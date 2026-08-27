"""Run prespecified synthetic stress tests without making empirical claims."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from itertools import product
from typing import Any

import numpy as np

import ewm
from ewm.equilibrium import FixedPointConfig
from ewm.experiments import paired_estimate, replicated_fx_comparisons, run_credit_regimes
from ewm.scenarios.credit import (
    CreditRegime,
    cong_qualitative_reconstruction,
    sensitivity_report,
)
from ewm.scenarios.forecasting import ForecastingProblem, oracle_report, smoke_config
from ewm.scenarios.fx import FXSimulationConfig, run_fx_simulation


def _forecasting_stress(*, quick: bool) -> dict[str, Any]:
    feedbacks = (0.8, 1.0, 1.2, 1.8) if quick else (0.6, 0.8, 1.0, 1.2, 1.8, 2.2)
    seeds = (42,) if quick else (11, 42, 303)
    cases: list[dict[str, Any]] = []

    for feedback, seed in product(feedbacks, seeds):
        config = replace(smoke_config(feedback=feedback), seed=seed)
        oracle = oracle_report(config)
        solved = ewm.solve_ddge(
            ForecastingProblem(config),
            (np.array([-1.25]), np.array([0.0]), np.array([1.25])),
            FixedPointConfig(tolerance=1e-8, max_iterations=500),
        )
        iterative_roots = tuple(sorted(float(point.theta[0]) for point in solved.fixed_points))
        root_gap = (
            max(
                abs(iterative - bracketed)
                for iterative, bracketed in zip(
                    iterative_roots,
                    oracle.bracketing_roots,
                    strict=True,
                )
            )
            if len(iterative_roots) == len(oracle.bracketing_roots)
            else None
        )
        cases.append(
            {
                "feedback": feedback,
                "seed": seed,
                "oracle_root_count": len(oracle.bracketing_roots),
                "iterative_root_count": len(iterative_roots),
                "stable_root_count": sum(oracle.stable),
                "derivative_error": abs(
                    oracle.numerical_derivative_zero - oracle.analytical_derivative_zero
                ),
                "root_gap": root_gap,
                "failed_initial_count": len(solved.diagnostics["failed_initials"]),
            }
        )

    derivative_check = all(case["derivative_error"] < 1e-6 for case in cases)
    declared_cases = tuple(case for case in cases if case["feedback"] not in (1.0, 2.2))
    phase_check = all(
        (case["oracle_root_count"] == 1 and case["stable_root_count"] == 1)
        if case["feedback"] < 1.0
        else (case["oracle_root_count"] == 3 and case["stable_root_count"] == 2)
        if case["feedback"] > 1.0
        else False
        for case in declared_cases
    )
    crosscheck = all(
        case["root_gap"] is not None and case["root_gap"] < 1e-5 for case in declared_cases
    )
    exploratory_warning_count = sum(
        case["failed_initial_count"] > 0
        or case["iterative_root_count"] != case["oracle_root_count"]
        for case in cases
        if case["feedback"] in (1.0, 2.2)
    )
    return {
        "case_count": len(cases),
        "cases": cases,
        "derivative_check": derivative_check,
        "declared_phase_check": phase_check,
        "declared_solver_oracle_crosscheck": crosscheck,
        "exploratory_warning_count": exploratory_warning_count,
    }


def _fx_stress(*, quick: bool) -> dict[str, Any]:
    depths = (5.0, 30.0) if quick else (5.0, 30.0, 150.0)
    spreads = (0.002,) if quick else (0.0005, 0.002, 0.02)
    trends = (0.0, 1.6) if quick else (0.0, 0.8, 1.6)
    seeds = (42,) if quick else (11, 42, 303)
    periods = 60 if quick else 120
    households = 8 if quick else 12
    cases: list[dict[str, Any]] = []

    for depth, spread, trend, seed in product(depths, spreads, trends, seeds):
        config = FXSimulationConfig(
            periods=periods,
            households=households,
            bank_depth=depth,
            bank_spread=spread,
            trend_weight=trend,
        )
        result = run_fx_simulation(config, seed=seed)
        cases.append(
            {
                "bank_depth": depth,
                "bank_spread": spread,
                "trend_weight": trend,
                "seed": seed,
                "minimum_price": min(result.prices),
                "max_cash_residual": result.max_cash_residual,
                "max_foreign_residual": result.max_foreign_residual,
                "rejected_orders": sum(result.rejected_orders),
            }
        )

    comparison_replications = 8 if quick else 50
    comparisons = replicated_fx_comparisons(
        FXSimulationConfig(periods=periods, households=households),
        seed=1_000,
        replications=comparison_replications,
    )
    comparison_report = {
        name: {metric: asdict(estimate) for metric, estimate in estimates.items()}
        for name, estimates in comparisons.items()
    }
    return {
        "case_count": len(cases),
        "cases": cases,
        "comparison_replications": comparison_replications,
        "comparisons": comparison_report,
        "accounting_check": all(
            case["max_cash_residual"] < 1e-8 and case["max_foreign_residual"] < 1e-8
            for case in cases
        ),
        "positive_price_check": all(case["minimum_price"] > 0.0 for case in cases),
    }


def _credit_stress(*, quick: bool) -> dict[str, Any]:
    seeds = (101, 102, 103) if quick else tuple(range(100, 110))
    population_size = 600 if quick else 1_200
    baseline_profit: list[float] = []
    frozen_profit: list[float] = []
    selective_profit: list[float] = []
    full_profit: list[float] = []
    cases: list[dict[str, Any]] = []
    finite_check = True
    observation_check = True

    for seed in seeds:
        config = replace(
            cong_qualitative_reconstruction(population_size=population_size),
            seed=seed,
        )
        regimes = run_credit_regimes(config)
        baseline = regimes[CreditRegime.NO_GENAI]
        frozen = regimes[CreditRegime.FROZEN]
        selective = regimes[CreditRegime.SELECTIVE]
        full = regimes[CreditRegime.FULL_INFORMATION]
        baseline_profit.append(baseline.profit_per_applicant)
        frozen_profit.append(frozen.profit_per_applicant)
        selective_profit.append(selective.profit_per_applicant)
        full_profit.append(full.profit_per_applicant)
        values = tuple(
            float(value)
            for regime in regimes.values()
            for key, value in asdict(regime).items()
            if key != "converged"
        )
        finite_check = finite_check and bool(np.isfinite(values).all())
        observation_check = observation_check and bool(
            np.isclose(selective.observed_rate, selective.approval_rate)
            and np.isclose(full.observed_rate, 1.0)
        )
        predicted_change = (
            frozen.predicted_profit_per_applicant - baseline.predicted_profit_per_applicant
        )
        realized_change = frozen.profit_per_applicant - baseline.profit_per_applicant
        cases.append(
            {
                "seed": seed,
                "frozen_predicted_change": predicted_change,
                "frozen_realized_change": realized_change,
                "frozen_sign_reversal": predicted_change * realized_change < 0.0,
                "selective_repair": (selective.profit_per_applicant >= frozen.profit_per_applicant),
                "full_information_repair": (
                    full.profit_per_applicant >= frozen.profit_per_applicant
                ),
                "selective_converged": selective.converged,
                "full_information_converged": full.converged,
                "selective_residual": selective.residual_norm,
                "full_information_residual": full.residual_norm,
            }
        )

    base = np.asarray(baseline_profit)
    paired_effects = {
        "frozen": asdict(paired_estimate(base, np.asarray(frozen_profit))),
        "selective_ddge": asdict(paired_estimate(base, np.asarray(selective_profit))),
        "full_information_ddge": asdict(paired_estimate(base, np.asarray(full_profit))),
    }
    sensitivity = sensitivity_report(
        replace(
            cong_qualitative_reconstruction(population_size=population_size),
            seed=seeds[0],
        ),
        polish_shifts=(0.0, 0.75, 1.5, 2.25, 3.0),
    )
    return {
        "replications": len(seeds),
        "population_size": population_size,
        "cases": cases,
        "paired_profit_effects": paired_effects,
        "frozen_sign_reversal_rate": sum(case["frozen_sign_reversal"] for case in cases)
        / len(cases),
        "selective_repair_rate": sum(case["selective_repair"] for case in cases) / len(cases),
        "full_information_repair_rate": sum(case["full_information_repair"] for case in cases)
        / len(cases),
        "selective_convergence_rate": sum(case["selective_converged"] for case in cases)
        / len(cases),
        "full_information_convergence_rate": sum(
            case["full_information_converged"] for case in cases
        )
        / len(cases),
        "sensitivity": [asdict(case) for case in sensitivity],
        "finite_metric_check": finite_check,
        "observation_check": observation_check,
    }


def build_report(*, quick: bool) -> dict[str, Any]:
    """Return the deterministic local stress report."""

    forecasting = _forecasting_stress(quick=quick)
    fx = _fx_stress(quick=quick)
    credit = _credit_stress(quick=quick)
    checks = {
        "forecasting_derivative": forecasting["derivative_check"],
        "forecasting_declared_phase_pattern": forecasting["declared_phase_check"],
        "forecasting_declared_solver_oracle": forecasting["declared_solver_oracle_crosscheck"],
        "fx_accounting": fx["accounting_check"],
        "fx_positive_prices": fx["positive_price_check"],
        "credit_finite_metrics": credit["finite_metric_check"],
        "credit_observation_semantics": credit["observation_check"],
    }
    return {
        "schema": "ewm.scientific-stress.v1",
        "mode": "quick" if quick else "full",
        "checks": checks,
        "forecasting": forecasting,
        "fx": fx,
        "credit": credit,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    report = build_report(quick=args.quick)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(report["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
