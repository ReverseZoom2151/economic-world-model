from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest

import ewm
from ewm._version import __version__
from ewm.core import ExperimentResult
from ewm.experiments.labs.production import solve_production_equilibrium
from ewm.experiments.runs.artifacts import write_artifacts
from ewm.experiments.runs.identity import build_run_identity, identity_sha256
from ewm.ontology.profiles import DEFAULT_PROFILES
from ewm.ontology.projection.compiler import ProjectionCompilation, compile_run_projection
from ewm.scenarios.production import package_authored_example
from ewm.scenarios.scalar import paper_config, scalar_verification_report


def _write_custom_run(
    root: Path,
    *,
    experiment: str,
    scenario: str,
    parameters: dict[str, object],
    metrics: dict[str, object],
    traces: dict[str, np.ndarray],
    events: tuple[dict[str, object], ...],
) -> Path:
    runtime = {"numpy": np.__version__, "python": "test"}
    source_fingerprint = "7" * 64
    identity = build_run_identity(
        experiment=experiment,
        package_version=__version__,
        parameters=parameters,
        preset="smoke",
        runtime_environment=runtime,
        scenario=scenario,
        seed=42,
        source_fingerprint=source_fingerprint,
    )
    return write_artifacts(
        output_root=root,
        run_hash=identity_sha256(identity)[:20],
        experiment=experiment,
        scenario=scenario,
        preset="smoke",
        seed=42,
        parameters=parameters,
        result=ExperimentResult(
            scenario=scenario,
            experiment=experiment,
            metrics=metrics,
            metadata={"preset": "smoke", "seed": 42},
        ),
        traces=traces,
        events=events,
        package_version=__version__,
        runtime_environment=runtime,
        source_fingerprint=source_fingerprint,
        identity=identity,
    )


@pytest.fixture(scope="session")
def scalar_projection(tmp_path_factory: pytest.TempPathFactory) -> ProjectionCompilation:
    config = paper_config()
    report = scalar_verification_report(config)
    parameters: dict[str, object] = {
        **asdict(config),
        "solver": "scipy.brentq_and_multistart_fixed_point_iteration",
        "tolerance": 1e-12,
        "max_iterations": 10_000,
        "stopping_rule": "residual_norm <= tolerance or max_iterations",
        "selector": "retain_all_distinct_roots",
    }
    events = tuple(
        {
            "kind": "fixed_point",
            "root": root,
            "derivative": derivative,
            "stable": stable,
            "residual": residual,
        }
        for root, derivative, stable, residual in zip(
            report.bracketing_roots,
            report.derivatives,
            report.stable,
            report.fixed_point_residuals,
            strict=True,
        )
    )
    run_dir = _write_custom_run(
        tmp_path_factory.mktemp("scalar-profile"),
        experiment="scalar.ddge",
        scenario="scalar",
        parameters=parameters,
        metrics={
            "root_count": len(report.bracketing_roots),
            "stable_root_count": sum(report.stable),
            "max_residual": max(report.fixed_point_residuals),
        },
        traces={
            "roots": np.asarray(report.bracketing_roots),
            "derivatives": np.asarray(report.derivatives),
            "residuals": np.asarray(report.fixed_point_residuals),
        },
        events=events,
    )
    return compile_run_projection(run_dir, adapters=DEFAULT_PROFILES)

@pytest.fixture(scope="session")
def forecasting_projection(tmp_path_factory: pytest.TempPathFactory) -> ProjectionCompilation:
    run = ewm.run_experiment(
        "forecasting.ddge",
        preset="smoke",
        seed=42,
        output_root=tmp_path_factory.mktemp("forecasting-profile"),
    )
    return compile_run_projection(run.run_dir, adapters=DEFAULT_PROFILES)


@pytest.fixture(scope="session")
def fx_projection(tmp_path_factory: pytest.TempPathFactory) -> ProjectionCompilation:
    run = ewm.run_experiment(
        "fx.rollout",
        preset="smoke",
        seed=42,
        output_root=tmp_path_factory.mktemp("fx-profile"),
    )
    return compile_run_projection(run.run_dir, adapters=DEFAULT_PROFILES)


@pytest.fixture(scope="session")
def credit_projection(tmp_path_factory: pytest.TempPathFactory) -> ProjectionCompilation:
    run = ewm.run_experiment(
        "credit.regimes",
        preset="smoke",
        seed=42,
        output_root=tmp_path_factory.mktemp("credit-profile"),
    )
    return compile_run_projection(run.run_dir, adapters=DEFAULT_PROFILES)


@pytest.fixture(scope="session")
def production_projection(tmp_path_factory: pytest.TempPathFactory) -> ProjectionCompilation:
    economy = package_authored_example()
    equilibrium = solve_production_equilibrium(
        economy,
        initial_rental_rate=0.08,
        initial_wage=1.0,
    )
    parameters: dict[str, object] = {
        "primitives": asdict(economy.primitives),
        "distribution": asdict(economy.distribution),
        "initial_rental_rate": 0.08,
        "initial_wage": 1.0,
        "solver": "scipy.optimize.root",
        "tolerance": 1e-8,
        "stopping_rule": "solver convergence and residual_norm <= tolerance",
    }
    equilibrium_record: dict[str, object] = {
        **asdict(equilibrium),
        "kind": "competitive_equilibrium",
    }
    run_dir = _write_custom_run(
        tmp_path_factory.mktemp("production-profile"),
        experiment="production.equilibrium",
        scenario="production",
        parameters=parameters,
        metrics={
            "rental_rate": equilibrium.rental_rate,
            "wage": equilibrium.wage,
            "residual_norm": equilibrium.residual_norm,
            "capital_clearing_residual": equilibrium.capital_clearing_residual,
            "labor_clearing_residual": equilibrium.labor_clearing_residual,
            "max_budget_residual": equilibrium.max_budget_residual,
            "max_household_foc_residual": equilibrium.max_household_foc_residual,
            "firm_capital_foc_residual": equilibrium.firm.capital_foc_residual,
            "firm_labor_foc_residual": equilibrium.firm.labor_foc_residual,
            "converged": equilibrium.converged,
        },
        traces={
            "market_residual": np.asarray(
                [
                    equilibrium.capital_clearing_residual,
                    equilibrium.labor_clearing_residual,
                ]
            ),
            "prices": np.asarray([equilibrium.rental_rate, equilibrium.wage]),
        },
        events=(equilibrium_record,),
    )
    return compile_run_projection(run_dir, adapters=DEFAULT_PROFILES)
