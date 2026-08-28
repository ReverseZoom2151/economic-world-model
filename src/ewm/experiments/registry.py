"""Explicit experiment registry and experiment-owned numerical execution."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, replace
from typing import Any

import numpy as np

from ewm.core import Event, ExperimentResult
from ewm.equilibrium import FixedPointConfig, solve_ddge
from ewm.scenarios.credit import CreditRegime, cong_qualitative_reconstruction
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
from ewm.scenarios.fx import run_fx_world
from ewm.scenarios.fx import (
    smoke_config as fx_smoke_config,
)

from .catalog.defaults import build_default_catalog
from .catalog.models import (
    ConfigFactory,
    DDGEFactory,
    Executor,
    ExperimentPayload,
    ExperimentSpec,
    RolloutFactory,
    RolloutResult,
    ScenarioConfig,
    ScenarioPlugin,
    ScenarioRegistry,
)
from .labs.credit import credit_paper_target_report, run_credit_regimes
from .labs.fx import replicated_fx_comparisons

__all__ = [
    "EXPERIMENTS",
    "SCENARIO_DESCRIPTIONS",
    "SCENARIO_REGISTRY",
    "ConfigFactory",
    "DDGEFactory",
    "Executor",
    "ExperimentPayload",
    "ExperimentSpec",
    "RolloutFactory",
    "RolloutResult",
    "ScenarioConfig",
    "ScenarioPlugin",
    "ScenarioRegistry",
    "experiment_spec",
]


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
    iteration_roots = tuple(sorted(float(point.theta[0]) for point in iterative.fixed_points))
    root_gap = (
        max(
            abs(iterative - bracketed)
            for iterative, bracketed in zip(iteration_roots, report.bracketing_roots, strict=True)
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
        events=tuple({"kind": "fixed_point", **record} for record in records),
    )


def _fx(preset: str, seed: int) -> ExperimentPayload:
    if preset == "smoke":
        config = fx_smoke_config()
    elif preset == "research":
        config = fx_research_config()
    else:
        raise ValueError("preset must be 'smoke' or 'research'")
    world_run = run_fx_world(config, seed=seed)
    simulation = world_run.result
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
        events=tuple(_event_record(event) for event in world_run.events),
    )


def _event_record(event: Event) -> Mapping[str, Any]:
    return {
        "event_hash": event.event_hash,
        "kind": event.kind,
        "payload": event.payload,
        "previous_hash": event.previous_hash,
        "schema_version": event.schema_version,
        "sequence": event.sequence,
        "state_version": event.state_version,
    }


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
        events=tuple({"kind": "paired_comparison", **record} for record in records),
    )


def _credit(preset: str, seed: int) -> ExperimentPayload:
    if preset == "smoke":
        config = cong_qualitative_reconstruction(population_size=800)
        configuration_name = "cong_qualitative_reconstruction"
    elif preset == "research":
        config = credit_research_config()
        configuration_name = "package_research_scale"
    else:
        raise ValueError("preset must be 'smoke' or 'research'")
    config = replace(config, seed=seed)
    regimes = run_credit_regimes(config)
    paper_report = credit_paper_target_report(config, regimes=regimes)
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
        "iterations",
        "converged",
    )
    metrics = {
        f"{regime.value}.{name}": getattr(values, name)
        for regime, values in regimes.items()
        for name in metric_names
    }
    records = tuple(
        {"regime": regime.value, **asdict(values)} for regime, values in regimes.items()
    )
    ordered_regimes = tuple(CreditRegime)
    return ExperimentPayload(
        result=ExperimentResult(
            scenario="credit",
            experiment="credit.regimes",
            metrics=metrics,
            records=records,
            metadata={
                "preset": preset,
                "seed": seed,
                "configuration": configuration_name,
                "source_id": "cong-2026",
                "claim_type": "qualitative-reconstruction",
                "exact_replication": False,
                "residual_floor_semantics": (
                    "minimum recent deterministic iterate residual; not the paper's "
                    "sampling noise floor"
                ),
                "published_target_differences": {
                    comparison.identifier: comparison.difference
                    for comparison in paper_report.targets
                },
                "qualitative_orderings": {
                    comparison.identifier: comparison.matches
                    for comparison in paper_report.orderings
                },
                "sampling_noise_floor": paper_report.sampling_noise_floor,
                "sampling_noise_floor_limitation": (paper_report.sampling_noise_floor_limitation),
            },
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


_DEFAULT_CATALOG = build_default_catalog(
    credit_executor=_credit,
    forecasting_executor=_forecasting,
    fx_comparative_statics_executor=_fx_comparative_statics,
    fx_rollout_executor=_fx,
)
SCENARIO_REGISTRY = _DEFAULT_CATALOG.registry
SCENARIO_DESCRIPTIONS: Mapping[str, str] = _DEFAULT_CATALOG.scenario_descriptions
EXPERIMENTS: Mapping[str, ExperimentSpec] = _DEFAULT_CATALOG.experiments


def experiment_spec(name: str) -> ExperimentSpec:
    """Resolve one experiment or raise an error listing valid choices."""

    return SCENARIO_REGISTRY.experiment(name)
