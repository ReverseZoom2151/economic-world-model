"""Solver orchestration for the AI-mediated credit regime experiment."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from ewm.equilibrium import FixedPointConfig, fixed_point_residual, iterate_fixed_point
from ewm.scenarios.credit import (
    CreditConfig,
    CreditDDGEProblem,
    CreditMetrics,
    CreditModel,
    CreditRegime,
    adoption_mask,
    evaluate_credit_model,
    evaluate_omniscient,
    fit_initial_model,
    generate_population,
)


@dataclass(frozen=True, slots=True)
class CreditOracleReport:
    """Prespecified paper-like effects and fixed-point inconsistency diagnostics."""

    frozen_predicted_profit_change: float
    frozen_realized_profit_change: float
    frozen_realized_profit: float
    selective_realized_profit: float
    full_information_realized_profit: float
    one_step_residual: float
    selective_residual: float


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
    baseline = evaluate_credit_model(
        population,
        initial_model,
        config,
        adoption=no_adoption,
    )

    frozen_adoption = adoption_mask(population, initial_model, config)
    frozen = evaluate_credit_model(
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
    selective = evaluate_credit_model(
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
    full = evaluate_credit_model(
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
    return MappingProxyType(
        {
            CreditRegime.NO_GENAI: baseline,
            CreditRegime.FROZEN: frozen,
            CreditRegime.SELECTIVE: selective,
            CreditRegime.FULL_INFORMATION: full,
            CreditRegime.OMNISCIENT: evaluate_omniscient(population, config),
        }
    )


def credit_oracle_report(config: CreditConfig) -> CreditOracleReport:
    """Compare frozen expectations with realized and endogenous-model outcomes."""

    regimes = run_credit_regimes(config)
    baseline = regimes[CreditRegime.NO_GENAI]
    frozen = regimes[CreditRegime.FROZEN]
    selective = regimes[CreditRegime.SELECTIVE]
    full = regimes[CreditRegime.FULL_INFORMATION]
    population = generate_population(config)
    initial = fit_initial_model(config)
    problem = CreditDDGEProblem(config, population, CreditRegime.SELECTIVE)
    one_step_residual = fixed_point_residual(problem.update, initial.to_vector())
    return CreditOracleReport(
        frozen_predicted_profit_change=(
            frozen.predicted_profit_per_applicant
            - baseline.predicted_profit_per_applicant
        ),
        frozen_realized_profit_change=(
            frozen.profit_per_applicant - baseline.profit_per_applicant
        ),
        frozen_realized_profit=frozen.profit_per_applicant,
        selective_realized_profit=selective.profit_per_applicant,
        full_information_realized_profit=full.profit_per_applicant,
        one_step_residual=one_step_residual,
        selective_residual=selective.residual_norm,
    )
