"""Counterfactual and sensitivity reports for the credit laboratory."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from ewm.equilibrium import fixed_point_residual

from .learner import adoption_mask, fit_initial_model
from .model import CreditDDGEProblem, CreditRegime, run_credit_regimes
from .population import assemble_features, generate_population
from .presets import CreditConfig


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


@dataclass(frozen=True, slots=True)
class CreditSensitivityCase:
    """One frozen-model intervention point retained without result filtering."""

    polish_shift: float
    adoption_rate: float
    predicted_profit_change: float
    realized_profit_change: float
    frozen_sign_reversal: bool


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


def sensitivity_report(
    config: CreditConfig,
    *,
    polish_shifts: tuple[float, ...],
) -> tuple[CreditSensitivityCase, ...]:
    """Retain frozen-counterfactual outcomes across a prespecified polish grid."""

    cases: list[CreditSensitivityCase] = []
    for shift in polish_shifts:
        candidate = replace(config, polish_shift=shift)
        population = generate_population(candidate)
        model = fit_initial_model(candidate)
        no_adoption = np.zeros(population.size, dtype=bool)
        adoption = adoption_mask(population, model, candidate)
        baseline_features = assemble_features(population, no_adoption)
        frozen_features = assemble_features(population, adoption)
        baseline_probability = model.predict_probability(baseline_features)
        frozen_probability = model.predict_probability(frozen_features)
        baseline_approval = model.approve(baseline_features, candidate)
        frozen_approval = model.approve(frozen_features, candidate)
        payoff = np.where(
            population.potential_repayment,
            candidate.repayment_gain,
            -candidate.default_loss,
        )
        baseline_expected = (
            baseline_probability * candidate.repayment_gain
            - (1.0 - baseline_probability) * candidate.default_loss
        )
        frozen_expected = (
            frozen_probability * candidate.repayment_gain
            - (1.0 - frozen_probability) * candidate.default_loss
        )
        predicted_change = float(
            np.mean(frozen_approval * frozen_expected)
            - np.mean(baseline_approval * baseline_expected)
        )
        realized_change = float(
            np.mean(frozen_approval * payoff) - np.mean(baseline_approval * payoff)
        )
        cases.append(
            CreditSensitivityCase(
                polish_shift=shift,
                adoption_rate=float(np.mean(adoption)),
                predicted_profit_change=predicted_change,
                realized_profit_change=realized_change,
                frozen_sign_reversal=predicted_change * realized_change < 0.0,
            )
        )
    return tuple(cases)
