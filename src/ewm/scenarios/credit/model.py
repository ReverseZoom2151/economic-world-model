"""Endogenous adoption, observation, retraining, and credit regimes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray
from sklearn.metrics import roc_auc_score

from ewm.equilibrium import FixedPointConfig, fixed_point_residual, iterate_fixed_point

from .learner import (
    CreditModel,
    adoption_mask,
    fit_credit_model,
    fit_initial_model,
    omniscient_approvals,
)
from .population import CreditPopulation, assemble_features, generate_population
from .presets import CreditConfig


class CreditRegime(StrEnum):
    """Observation and adaptation regimes used by the credit laboratory."""

    NO_GENAI = "no_genai"
    FROZEN = "frozen"
    SELECTIVE = "selective_ddge"
    FULL_INFORMATION = "full_information_ddge"
    OMNISCIENT = "omniscient_oracle"


@dataclass(frozen=True, slots=True)
class CreditMetrics:
    """Economic, predictive, and fixed-point measurements for one regime."""

    profit_per_applicant: float
    predicted_profit_per_applicant: float
    approval_rate: float
    adoption_rate: float
    observed_rate: float
    auc: float
    false_positive_rate: float
    false_negative_rate: float
    residual_norm: float
    residual_floor: float
    coefficient_distance: float
    iterations: int = 0
    converged: bool = True


@dataclass(frozen=True, slots=True)
class CreditDDGEProblem:
    """Behavior-data-learning update for selective or full-information labels."""

    config: CreditConfig
    population: CreditPopulation
    regime: CreditRegime
    _historical_features: NDArray[np.float64] = field(
        init=False, repr=False, compare=False
    )
    _historical_repayment: NDArray[np.bool_] = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.regime not in (
            CreditRegime.SELECTIVE,
            CreditRegime.FULL_INFORMATION,
        ):
            raise ValueError("a credit DDGE problem requires a retraining regime")
        historical = generate_population(self.config, seed=self.config.seed + 10_000)
        historical_features = assemble_features(
            historical, np.zeros(historical.size, dtype=bool)
        )
        object.__setattr__(self, "_historical_features", historical_features)
        object.__setattr__(
            self, "_historical_repayment", historical.potential_repayment
        )

    @property
    def dimension(self) -> int:
        return self.config.feature_count + 1

    def induced_state(
        self, theta: NDArray[np.floating[Any]]
    ) -> tuple[CreditModel, NDArray[np.bool_], NDArray[np.float64], NDArray[np.bool_]]:
        model = CreditModel.from_vector(theta)
        if model.coefficients.size != self.config.feature_count:
            raise ValueError("credit theta has the wrong dimension")
        adopted = adoption_mask(self.population, model, self.config)
        features = assemble_features(self.population, adopted)
        approvals = model.approve(features, self.config)
        return model, adopted, features, approvals

    def training_mask(
        self, theta: NDArray[np.floating[Any]]
    ) -> NDArray[np.bool_]:
        """Return the endogenous label-observation mask under a candidate model."""

        _, _, _, approvals = self.induced_state(theta)
        if self.regime is CreditRegime.SELECTIVE:
            return approvals
        return np.ones(self.population.size, dtype=bool)

    def update(
        self, theta: NDArray[np.floating[Any]]
    ) -> NDArray[np.floating[Any]]:
        """Generate adoption and labels, refit, then apply declared retraining damping."""

        candidate = np.asarray(theta, dtype=float)
        _, _, features, _ = self.induced_state(candidate)
        observed = self.training_mask(candidate)
        if observed.sum() < 2:
            return candidate.copy()
        training_features = np.vstack((self._historical_features, features[observed]))
        training_repayment = np.concatenate(
            (self._historical_repayment, self.population.potential_repayment[observed])
        )
        fitted = fit_credit_model(
            training_features,
            training_repayment,
            ridge=self.config.ridge,
        ).to_vector()
        damping = self.config.retraining_damping
        return (1.0 - damping) * candidate + damping * fitted


def _classification_rates(
    approvals: NDArray[np.bool_], repayment: NDArray[np.bool_]
) -> tuple[float, float]:
    negative = ~repayment
    positive = repayment
    false_positive = float(np.mean(approvals[negative])) if negative.any() else 0.0
    false_negative = float(np.mean(~approvals[positive])) if positive.any() else 0.0
    return false_positive, false_negative


def _realized_profit(
    approvals: NDArray[np.bool_],
    repayment: NDArray[np.bool_],
    config: CreditConfig,
) -> float:
    payoff = np.where(repayment, config.repayment_gain, -config.default_loss)
    return float(np.mean(approvals * payoff))


def _predicted_profit(
    approvals: NDArray[np.bool_],
    probabilities: NDArray[np.float64],
    config: CreditConfig,
) -> float:
    expected = (
        probabilities * config.repayment_gain
        - (1.0 - probabilities) * config.default_loss
    )
    return float(np.mean(approvals * expected))


def _metrics(
    *,
    population: CreditPopulation,
    approvals: NDArray[np.bool_],
    adoption: NDArray[np.bool_],
    observed: NDArray[np.bool_],
    probabilities: NDArray[np.float64],
    config: CreditConfig,
    residual_norm: float = 0.0,
    residual_floor: float = 0.0,
    coefficient_distance: float = 0.0,
    iterations: int = 0,
    converged: bool = True,
) -> CreditMetrics:
    false_positive, false_negative = _classification_rates(
        approvals, population.potential_repayment
    )
    auc = (
        float(roc_auc_score(population.potential_repayment, probabilities))
        if np.unique(population.potential_repayment).size == 2
        else 0.5
    )
    return CreditMetrics(
        profit_per_applicant=_realized_profit(
            approvals, population.potential_repayment, config
        ),
        predicted_profit_per_applicant=_predicted_profit(
            approvals, probabilities, config
        ),
        approval_rate=float(np.mean(approvals)),
        adoption_rate=float(np.mean(adoption)),
        observed_rate=float(np.mean(observed)),
        auc=auc,
        false_positive_rate=false_positive,
        false_negative_rate=false_negative,
        residual_norm=residual_norm,
        residual_floor=residual_floor,
        coefficient_distance=coefficient_distance,
        iterations=iterations,
        converged=converged,
    )


def _evaluate_model(
    population: CreditPopulation,
    model: CreditModel,
    config: CreditConfig,
    *,
    adoption: NDArray[np.bool_],
    observed: NDArray[np.bool_] | None = None,
    residual_norm: float = 0.0,
    residual_floor: float = 0.0,
    initial_model: CreditModel | None = None,
    iterations: int = 0,
    converged: bool = True,
) -> CreditMetrics:
    features = assemble_features(population, adoption)
    probabilities = model.predict_probability(features)
    approvals = probabilities >= config.approval_threshold
    observed_mask = approvals if observed is None else observed
    distance = (
        float(np.linalg.norm(model.to_vector() - initial_model.to_vector()))
        if initial_model is not None
        else 0.0
    )
    return _metrics(
        population=population,
        approvals=approvals,
        adoption=adoption,
        observed=observed_mask,
        probabilities=probabilities,
        config=config,
        residual_norm=residual_norm,
        residual_floor=residual_floor,
        coefficient_distance=distance,
        iterations=iterations,
        converged=converged,
    )


def _solve_adaptive_regime(
    problem: CreditDDGEProblem,
    initial_model: CreditModel,
) -> tuple[CreditModel, float, float, int, bool]:
    point = iterate_fixed_point(
        problem.update,
        initial_model.to_vector(),
        FixedPointConfig(
            tolerance=problem.config.ddge_tolerance,
            max_iterations=problem.config.ddge_max_iterations,
            estimate_stability=False,
        ),
    )
    model = CreditModel.from_vector(point.theta)
    residual = fixed_point_residual(problem.update, point.theta)
    tail = point.residual_history[-min(20, len(point.residual_history)) :]
    residual_floor = min(tail, default=residual)
    return model, residual, residual_floor, point.iterations, point.converged


def run_credit_regimes(config: CreditConfig) -> Mapping[CreditRegime, CreditMetrics]:
    """Evaluate baseline, frozen, two DDGEs, and the omniscient oracle."""

    population = generate_population(config)
    initial_model = fit_initial_model(config)
    no_adoption = np.zeros(population.size, dtype=bool)
    baseline = _evaluate_model(
        population,
        initial_model,
        config,
        adoption=no_adoption,
    )

    frozen_adoption = adoption_mask(population, initial_model, config)
    frozen = _evaluate_model(
        population,
        initial_model,
        config,
        adoption=frozen_adoption,
    )

    selective_problem = CreditDDGEProblem(
        config, population, CreditRegime.SELECTIVE
    )
    (
        selective_model,
        selective_residual,
        selective_floor,
        selective_iterations,
        selective_converged,
    ) = _solve_adaptive_regime(selective_problem, initial_model)
    selective_adoption = adoption_mask(population, selective_model, config)
    selective = _evaluate_model(
        population,
        selective_model,
        config,
        adoption=selective_adoption,
        residual_norm=selective_residual,
        residual_floor=selective_floor,
        initial_model=initial_model,
        iterations=selective_iterations,
        converged=selective_converged,
    )

    full_problem = CreditDDGEProblem(
        config, population, CreditRegime.FULL_INFORMATION
    )
    (
        full_model,
        full_residual,
        full_floor,
        full_iterations,
        full_converged,
    ) = _solve_adaptive_regime(full_problem, initial_model)
    full_adoption = adoption_mask(population, full_model, config)
    full = _evaluate_model(
        population,
        full_model,
        config,
        adoption=full_adoption,
        observed=np.ones(population.size, dtype=bool),
        residual_norm=full_residual,
        residual_floor=full_floor,
        initial_model=initial_model,
        iterations=full_iterations,
        converged=full_converged,
    )

    oracle_approval = omniscient_approvals(population, config)
    oracle_probability = population.repayment_probability
    oracle = _metrics(
        population=population,
        approvals=oracle_approval,
        adoption=no_adoption,
        observed=np.ones(population.size, dtype=bool),
        probabilities=oracle_probability,
        config=config,
    )
    return MappingProxyType(
        {
            CreditRegime.NO_GENAI: baseline,
            CreditRegime.FROZEN: frozen,
            CreditRegime.SELECTIVE: selective,
            CreditRegime.FULL_INFORMATION: full,
            CreditRegime.OMNISCIENT: oracle,
        }
    )
