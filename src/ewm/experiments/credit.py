"""Solver orchestration for the AI-mediated credit regime experiment."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType

import numpy as np

from ewm.equilibrium import FixedPointConfig, fixed_point_residual, iterate_fixed_point
from ewm.scenarios.credit import (
    CONG_LAB_I_PROVENANCE,
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
    """Prespecified reconstruction effects and fixed-point inconsistency diagnostics."""

    frozen_predicted_profit_change: float
    frozen_realized_profit_change: float
    frozen_realized_profit: float
    selective_realized_profit: float
    full_information_realized_profit: float
    one_step_residual: float
    selective_residual: float


@dataclass(frozen=True, slots=True)
class CreditTargetComparison:
    """A published magnitude beside this reconstruction's non-calibrated value."""

    identifier: str
    published_value: float
    reconstructed_value: float | None
    unit: str

    @property
    def measured(self) -> bool:
        return self.reconstructed_value is not None

    @property
    def difference(self) -> float | None:
        if self.reconstructed_value is None:
            return None
        return self.reconstructed_value - self.published_value


@dataclass(frozen=True, slots=True)
class CreditOrderingComparison:
    """Whether one source-stated qualitative ordering appears in this reconstruction."""

    identifier: str
    matches: bool | None
    limitation: str = ""


@dataclass(frozen=True, slots=True)
class CreditPaperTargetReport:
    """Auditable comparison that never treats nonidentified magnitudes as targets."""

    targets: tuple[CreditTargetComparison, ...]
    orderings: tuple[CreditOrderingComparison, ...]
    one_step_residual: float
    terminal_residual_floor: float
    sampling_noise_floor: float | None
    sampling_noise_floor_limitation: str
    exact_replication_claimed: bool = False


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


def credit_paper_target_report(
    config: CreditConfig,
    *,
    regimes: Mapping[CreditRegime, CreditMetrics] | None = None,
) -> CreditPaperTargetReport:
    """Compare source magnitudes and orderings without asserting numerical replication."""

    results = run_credit_regimes(config) if regimes is None else regimes
    baseline = results[CreditRegime.NO_GENAI]
    frozen = results[CreditRegime.FROZEN]
    selective = results[CreditRegime.SELECTIVE]
    full = results[CreditRegime.FULL_INFORMATION]
    omniscient = results[CreditRegime.OMNISCIENT]

    population = generate_population(config)
    initial = fit_initial_model(config)
    problem = CreditDDGEProblem(config, population, CreditRegime.SELECTIVE)
    one_step_residual = fixed_point_residual(problem.update, initial.to_vector())
    no_polish_population = generate_population(replace(config, polish_shift=0.0))
    no_polish_omniscient = evaluate_omniscient(no_polish_population, config)

    reconstructed: dict[str, float | None] = {
        "baseline_profit_per_applicant": baseline.profit_per_applicant,
        "baseline_auc": baseline.auc,
        "structured_only_auc": None,
        "frozen_predicted_profit_change": (
            frozen.predicted_profit_per_applicant
            - baseline.predicted_profit_per_applicant
        ),
        "frozen_realized_profit_change": (
            frozen.profit_per_applicant - baseline.profit_per_applicant
        ),
        "selective_ddge_profit_change": (
            selective.profit_per_applicant - baseline.profit_per_applicant
        ),
        "frozen_adoption_rate": frozen.adoption_rate,
        "selective_ddge_adoption_rate": selective.adoption_rate,
        "baseline_false_positive_rate": baseline.false_positive_rate,
        "frozen_false_positive_rate": frozen.false_positive_rate,
        "selective_ddge_false_positive_rate": selective.false_positive_rate,
        "full_information_profit_change": (
            full.profit_per_applicant - baseline.profit_per_applicant
        ),
        "one_step_residual": one_step_residual,
        "residual_to_sampling_noise_ratio": None,
        "local_retraining_modulus": None,
        "damped_map_modulus": None,
    }
    targets = tuple(
        CreditTargetComparison(
            identifier=target.identifier,
            published_value=target.value,
            reconstructed_value=reconstructed[target.identifier],
            unit=target.unit,
        )
        for target in CONG_LAB_I_PROVENANCE.published_targets
    )
    frozen_loss = frozen.profit_per_applicant - baseline.profit_per_applicant
    selective_loss = selective.profit_per_applicant - baseline.profit_per_applicant
    orderings = (
        CreditOrderingComparison("endogenous_adoption", frozen.adoption_rate > 0.0),
        CreditOrderingComparison(
            "selective_outcome_observation",
            bool(np.isclose(selective.observed_rate, selective.approval_rate)),
        ),
        CreditOrderingComparison(
            "frozen_predicted_realized_sign_reversal",
            frozen.predicted_profit_per_applicant
            - baseline.predicted_profit_per_applicant
            > 0.0
            > frozen_loss,
        ),
        CreditOrderingComparison(
            "selective_ddge_partial_repair",
            frozen_loss < selective_loss < 0.0,
        ),
        CreditOrderingComparison(
            "full_information_underperforms_selective",
            full.profit_per_applicant < selective.profit_per_applicant,
        ),
        CreditOrderingComparison(
            "omniscient_intervention_invariance",
            omniscient.adoption_rate == 0.0
            and bool(
                np.isclose(
                    omniscient.profit_per_applicant,
                    no_polish_omniscient.profit_per_applicant,
                )
            ),
        ),
        CreditOrderingComparison(
            "adoption_falls_after_selective_retraining",
            selective.adoption_rate < frozen.adoption_rate,
        ),
        CreditOrderingComparison(
            "text_informativeness_declines",
            None,
            "Incremental text-only AUC is not yet measured by this reconstruction.",
        ),
        CreditOrderingComparison(
            "false_positive_rate_partially_recovers",
            baseline.false_positive_rate
            < selective.false_positive_rate
            < frozen.false_positive_rate,
        ),
    )
    return CreditPaperTargetReport(
        targets=targets,
        orderings=orderings,
        one_step_residual=one_step_residual,
        terminal_residual_floor=selective.residual_floor,
        sampling_noise_floor=None,
        sampling_noise_floor_limitation=(
            "Cong's sampling noise floor is not estimated because its cohort process and "
            "estimator are not specified; terminal_residual_floor is only a recent-iterate minimum."
        ),
    )
