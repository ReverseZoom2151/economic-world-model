"""Explicit experiment registry and experiment-owned numerical execution."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, replace
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ewm.core import ExperimentResult
from ewm.equilibrium import FixedPointConfig, solve_ddge
from ewm.scenarios.credit import (
    CreditRegime,
    paper_like_config,
)
from ewm.scenarios.credit import (
    research_config as credit_research_config,
)
from ewm.scenarios.forecasting import (
    ForecastingProblem,
    oracle_report,
)
from ewm.scenarios.forecasting import (
    research_config as forecasting_research_config,
)
from ewm.scenarios.forecasting import (
    smoke_config as forecasting_smoke_config,
)
from ewm.scenarios.fx import (
    research_config as fx_research_config,
)
from ewm.scenarios.fx import (
    run_fx_simulation,
)
from ewm.scenarios.fx import (
    smoke_config as fx_smoke_config,
)

from .credit import run_credit_regimes
from .fx import replicated_fx_comparisons

SCENARIO_DESCRIPTIONS: Mapping[str, str] = {
    "credit": (
        "AI-mediated credit with endogenous decision-flip adoption, selective labels, "
        "full-information retraining, and frozen and omniscient counterfactuals."
    ),
    "forecasting": (
        "A self-fulfilling forecasting Data-Driven Generative Equilibrium with a pitchfork "
        "multiplicity threshold and independent numerical oracles."
    ),
    "fx": (
        "A heterogeneous household, firm, and bank economy with uniform-price batch clearing, "
        "adaptive beliefs, balance feasibility, and conservation diagnostics."
    ),
}


@dataclass(frozen=True, slots=True)
class ExperimentPayload:
    """Scenario-produced values before the shared runner writes artifacts."""

    result: ExperimentResult
    parameters: Mapping[str, Any]
    traces: Mapping[str, NDArray[Any]]
    events: tuple[Mapping[str, Any], ...]


Executor = Callable[[str, int], ExperimentPayload]


@dataclass(frozen=True, slots=True)
class ExperimentSpec:
    """One discoverable experiment and its deterministic executor."""

    name: str
    scenario: str
    description: str
    execute: Executor


def _forecasting(preset: str, seed: int) -> ExperimentPayload:
    if preset == "smoke":
        config = forecasting_smoke_config()
    elif preset == "research":
        config = forecasting_research_config()
    else:
        raise ValueError("preset must be 'smoke' or 'research'")
    config = replace(config, seed=seed)
    report = oracle_report(config)
    iterative = solve_ddge(
        ForecastingProblem(config),
        (np.array([-1.5]), np.array([0.0]), np.array([1.5])),
        FixedPointConfig(tolerance=1e-10, max_iterations=1_000),
    )
    iteration_roots = tuple(
        sorted(float(point.theta[0]) for point in iterative.fixed_points)
    )
    root_gap = (
        max(
            abs(iterative - bracketed)
            for iterative, bracketed in zip(
                iteration_roots, report.bracketing_roots, strict=True
            )
        )
        if iteration_roots
        else 0.0
    )
    metrics = {
        "analytical_derivative_zero": report.analytical_derivative_zero,
        "derivative_error": abs(
            report.numerical_derivative_zero - report.analytical_derivative_zero
        ),
        "max_root_gap": root_gap,
        "root_count": len(iteration_roots),
        "stable_root_count": sum(report.stable),
    }
    records = tuple(
        {
            "root": root,
            "derivative": derivative,
            "stable": stable,
            "first_autocorrelation": autocorrelation,
        }
        for root, derivative, stable, autocorrelation in zip(
            report.bracketing_roots,
            report.derivatives,
            report.stable,
            report.first_autocorrelations,
            strict=True,
        )
    )
    return ExperimentPayload(
        result=ExperimentResult(
            scenario="forecasting",
            experiment="forecasting.ddge",
            metrics=metrics,
            records=records,
            metadata={"preset": preset, "seed": seed},
        ),
        parameters=asdict(config),
        traces={
            "roots": np.asarray(report.bracketing_roots),
            "derivatives": np.asarray(report.derivatives),
            "first_autocorrelations": np.asarray(report.first_autocorrelations),
        },
        events=tuple(
            {"kind": "fixed_point", **record} for record in records
        ),
    )


def _fx(preset: str, seed: int) -> ExperimentPayload:
    if preset == "smoke":
        config = fx_smoke_config()
    elif preset == "research":
        config = fx_research_config()
    else:
        raise ValueError("preset must be 'smoke' or 'research'")
    simulation = run_fx_simulation(config, seed=seed)
    metrics = {
        **simulation.metrics,
        "max_cash_residual": simulation.max_cash_residual,
        "max_foreign_residual": simulation.max_foreign_residual,
    }
    records = tuple(
        {
            "period": period,
            "price": simulation.prices[period],
            "volume": simulation.volumes[period - 1],
            "rejected_orders": simulation.rejected_orders[period - 1],
        }
        for period in range(1, len(simulation.prices))
    )
    return ExperimentPayload(
        result=ExperimentResult(
            scenario="fx",
            experiment="fx.rollout",
            metrics=metrics,
            records=records,
            metadata={"preset": preset, "seed": seed},
        ),
        parameters=asdict(config),
        traces={
            "prices": np.asarray(simulation.prices),
            "volumes": np.asarray(simulation.volumes),
            "rejected_orders": np.asarray(simulation.rejected_orders),
        },
        events=tuple({"kind": "clearing", **record} for record in records),
    )


def _fx_comparative_statics(preset: str, seed: int) -> ExperimentPayload:
    if preset == "smoke":
        config = fx_smoke_config()
        replications = 8
    elif preset == "research":
        config = fx_research_config()
        replications = 50
    else:
        raise ValueError("preset must be 'smoke' or 'research'")
    reports = replicated_fx_comparisons(
        config,
        seed=seed,
        replications=replications,
    )
    records = tuple(
        {
            "comparison": comparison,
            "metric": metric,
            **asdict(estimate),
        }
        for comparison, estimates in reports.items()
        for metric, estimate in estimates.items()
    )
    metrics = {
        f"{record['comparison']}.{record['metric']}.{field}": record[field]
        for record in records
        for field in (
            "mean_difference",
            "standard_error",
            "interval_low",
            "interval_high",
            "sample_size",
        )
    }
    return ExperimentPayload(
        result=ExperimentResult(
            scenario="fx",
            experiment="fx.comparative_statics",
            metrics=metrics,
            records=records,
            metadata={"preset": preset, "seed": seed},
        ),
        parameters={**asdict(config), "replications": replications},
        traces={
            field: np.asarray([record[field] for record in records])
            for field in (
                "mean_difference",
                "standard_error",
                "interval_low",
                "interval_high",
            )
        },
        events=tuple(
            {"kind": "paired_comparison", **record} for record in records
        ),
    )


def _credit(preset: str, seed: int) -> ExperimentPayload:
    if preset == "smoke":
        config = paper_like_config(population_size=800)
    elif preset == "research":
        config = credit_research_config()
    else:
        raise ValueError("preset must be 'smoke' or 'research'")
    config = replace(config, seed=seed)
    regimes = run_credit_regimes(config)
    metric_names = (
        "profit_per_applicant",
        "predicted_profit_per_applicant",
        "approval_rate",
        "adoption_rate",
        "observed_rate",
        "auc",
        "false_positive_rate",
        "false_negative_rate",
        "residual_norm",
        "residual_floor",
        "coefficient_distance",
    )
    metrics = {
        f"{regime.value}.{name}": getattr(values, name)
        for regime, values in regimes.items()
        for name in metric_names
    }
    records = tuple(
        {"regime": regime.value, **asdict(values)}
        for regime, values in regimes.items()
    )
    ordered_regimes = tuple(CreditRegime)
    return ExperimentPayload(
        result=ExperimentResult(
            scenario="credit",
            experiment="credit.regimes",
            metrics=metrics,
            records=records,
            metadata={"preset": preset, "seed": seed},
        ),
        parameters=asdict(config),
        traces={
            "profit_per_applicant": np.asarray(
                [regimes[regime].profit_per_applicant for regime in ordered_regimes]
            ),
            "approval_rate": np.asarray(
                [regimes[regime].approval_rate for regime in ordered_regimes]
            ),
            "adoption_rate": np.asarray(
                [regimes[regime].adoption_rate for regime in ordered_regimes]
            ),
            "residual_norm": np.asarray(
                [regimes[regime].residual_norm for regime in ordered_regimes]
            ),
        },
        events=tuple({"kind": "regime", **record} for record in records),
    )


EXPERIMENTS: Mapping[str, ExperimentSpec] = {
    "credit.regimes": ExperimentSpec(
        "credit.regimes",
        "credit",
        "Compare no-AI, frozen, selective-DDGE, full-information-DDGE, and oracle credit regimes.",
        _credit,
    ),
    "forecasting.ddge": ExperimentSpec(
        "forecasting.ddge",
        "forecasting",
        "Find and independently verify the forecasting model's DDGE fixed points.",
        _forecasting,
    ),
    "fx.rollout": ExperimentSpec(
        "fx.rollout",
        "fx",
        "Run the adaptive heterogeneous FX economy and record clearing diagnostics.",
        _fx,
    ),
    "fx.comparative_statics": ExperimentSpec(
        "fx.comparative_statics",
        "fx",
        "Estimate replicated common-random-number FX effects and uncertainty intervals.",
        _fx_comparative_statics,
    ),
}


def experiment_spec(name: str) -> ExperimentSpec:
    """Resolve one experiment or raise an error listing valid choices."""

    try:
        return EXPERIMENTS[name]
    except KeyError as error:
        choices = ", ".join(EXPERIMENTS)
        raise ValueError(f"unknown experiment {name!r}; choose from: {choices}") from error
