"""Explicit experiment registry and experiment-owned numerical execution."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, replace
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ewm.core import DDGEProblem, ExperimentResult
from ewm.equilibrium import FixedPointConfig, solve_ddge
from ewm.scenarios.credit import (
    CreditConfig,
    CreditDDGEProblem,
    CreditRegime,
    cong_qualitative_reconstruction,
    generate_population,
)
from ewm.scenarios.credit import (
    research_config as credit_research_config,
)
from ewm.scenarios.forecasting import (
    ForecastingConfig,
    ForecastingProblem,
    oracle_report,
    simulate_series,
)
from ewm.scenarios.forecasting import (
    research_config as forecasting_research_config,
)
from ewm.scenarios.forecasting import (
    smoke_config as forecasting_smoke_config,
)
from ewm.scenarios.fx import (
    FXSimulationConfig,
    FXSimulationResult,
    run_fx_simulation,
)
from ewm.scenarios.fx import (
    research_config as fx_research_config,
)
from ewm.scenarios.fx import (
    smoke_config as fx_smoke_config,
)
from ewm.scenarios.scalar import ScalarConfig, ScalarProblem
from ewm.scenarios.scalar import paper_config as scalar_paper_config

from .credit import credit_paper_target_report, run_credit_regimes
from .fx import replicated_fx_comparisons


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


ScenarioConfig = ForecastingConfig | FXSimulationConfig | CreditConfig | ScalarConfig
RolloutResult = NDArray[np.float64] | FXSimulationResult
ConfigFactory = Callable[[str, int, Mapping[str, Any]], ScenarioConfig]
DDGEFactory = Callable[[ScenarioConfig, CreditRegime], DDGEProblem]
RolloutFactory = Callable[
    [ScenarioConfig, int, int | None, float],
    RolloutResult,
]


@dataclass(frozen=True, slots=True)
class ScenarioPlugin:
    """One scenario's configuration, runtime capabilities, and experiments."""

    name: str
    description: str
    config_factory: ConfigFactory
    ddge_factory: DDGEFactory | None = None
    rollout_factory: RolloutFactory | None = None
    experiments: tuple[ExperimentSpec, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("scenario plugin name must not be empty")
        if not self.description:
            raise ValueError("scenario plugin description must not be empty")
        object.__setattr__(self, "experiments", tuple(self.experiments))

    def configure(
        self,
        preset: str,
        seed: int,
        overrides: Mapping[str, Any],
    ) -> ScenarioConfig:
        """Build one preset while retaining seed and override provenance."""

        if preset not in {"smoke", "research"}:
            raise ValueError("preset must be 'smoke' or 'research'")
        return self.config_factory(preset, seed, overrides)

    def make_ddge_problem(
        self,
        config: ScenarioConfig,
        regime: CreditRegime,
    ) -> DDGEProblem:
        """Build the scenario's DDGE problem or report the absent capability."""

        if self.ddge_factory is None:
            raise ValueError(f"scenario {self.name!r} does not define a DDGE problem")
        return self.ddge_factory(config, regime)

    def run_rollout(
        self,
        config: ScenarioConfig,
        seed: int,
        periods: int | None,
        theta: float,
    ) -> RolloutResult:
        """Run the scenario's temporal model or report the absent capability."""

        if self.rollout_factory is None:
            raise ValueError(f"scenario {self.name!r} does not define a temporal rollout")
        return self.rollout_factory(config, seed, periods, theta)


class ScenarioRegistry:
    """Immutable, validated catalog of scenarios and their owned experiments."""

    __slots__ = ("_experiments", "_scenarios")

    def __init__(self, plugins: tuple[ScenarioPlugin, ...]) -> None:
        owned_plugins = tuple(plugins)
        names = tuple(plugin.name for plugin in owned_plugins)
        if len(names) != len(set(names)):
            raise ValueError("scenario names must be unique")

        scenarios = dict(sorted((plugin.name, plugin) for plugin in owned_plugins))
        experiments: dict[str, ExperimentSpec] = {}
        for plugin in scenarios.values():
            for experiment in plugin.experiments:
                if experiment.scenario != plugin.name:
                    raise ValueError(
                        f"experiment {experiment.name!r} belongs to scenario "
                        f"{experiment.scenario!r}, not plugin {plugin.name!r}"
                    )
                if experiment.name in experiments:
                    raise ValueError("experiment names must be unique")
                experiments[experiment.name] = experiment

        self._scenarios: Mapping[str, ScenarioPlugin] = MappingProxyType(scenarios)
        self._experiments: Mapping[str, ExperimentSpec] = MappingProxyType(
            dict(sorted(experiments.items()))
        )

    @property
    def scenarios(self) -> Mapping[str, ScenarioPlugin]:
        return self._scenarios

    @property
    def experiments(self) -> Mapping[str, ExperimentSpec]:
        return self._experiments

    def scenario(self, name: str) -> ScenarioPlugin:
        """Resolve one scenario or raise an error listing stable choices."""

        try:
            return self._scenarios[name]
        except KeyError as error:
            choices = ", ".join(self._scenarios)
            raise ValueError(f"unknown scenario {name!r}; choose from: {choices}") from error

    def experiment(self, name: str) -> ExperimentSpec:
        """Resolve one experiment or raise an error listing stable choices."""

        try:
            return self._experiments[name]
        except KeyError as error:
            choices = ", ".join(self._experiments)
            raise ValueError(f"unknown experiment {name!r}; choose from: {choices}") from error


def _with_overrides(config: ScenarioConfig, overrides: Mapping[str, Any]) -> ScenarioConfig:
    return replace(config, **dict(overrides)) if overrides else config


def _forecasting_config(
    preset: str,
    seed: int,
    overrides: Mapping[str, Any],
) -> ScenarioConfig:
    config = forecasting_smoke_config() if preset == "smoke" else forecasting_research_config()
    return _with_overrides(replace(config, seed=seed), overrides)


def _fx_config(
    preset: str,
    _seed: int,
    overrides: Mapping[str, Any],
) -> ScenarioConfig:
    config = fx_smoke_config() if preset == "smoke" else fx_research_config()
    return _with_overrides(config, overrides)


def _credit_config(
    preset: str,
    seed: int,
    overrides: Mapping[str, Any],
) -> ScenarioConfig:
    config = (
        cong_qualitative_reconstruction(population_size=800)
        if preset == "smoke"
        else credit_research_config()
    )
    return _with_overrides(replace(config, seed=seed), overrides)


def _scalar_config(
    _preset: str,
    _seed: int,
    overrides: Mapping[str, Any],
) -> ScenarioConfig:
    return _with_overrides(scalar_paper_config(), overrides)


def _forecasting_ddge(
    config: ScenarioConfig,
    _regime: CreditRegime,
) -> DDGEProblem:
    if not isinstance(config, ForecastingConfig):
        raise TypeError("forecasting plugin requires ForecastingConfig")
    return ForecastingProblem(config)


def _credit_ddge(config: ScenarioConfig, regime: CreditRegime) -> DDGEProblem:
    if not isinstance(config, CreditConfig):
        raise TypeError("credit plugin requires CreditConfig")
    return CreditDDGEProblem(config, generate_population(config), regime)


def _scalar_ddge(
    config: ScenarioConfig,
    _regime: CreditRegime,
) -> DDGEProblem:
    if not isinstance(config, ScalarConfig):
        raise TypeError("scalar plugin requires ScalarConfig")
    return ScalarProblem(config)


def _forecasting_rollout(
    config: ScenarioConfig,
    seed: int,
    periods: int | None,
    theta: float,
) -> RolloutResult:
    if not isinstance(config, ForecastingConfig):
        raise TypeError("forecasting plugin requires ForecastingConfig")
    rollout_config = replace(config, sample_size=periods) if periods is not None else config
    return simulate_series(theta, rollout_config, seed=seed)


def _fx_rollout(
    config: ScenarioConfig,
    seed: int,
    periods: int | None,
    _theta: float,
) -> RolloutResult:
    if not isinstance(config, FXSimulationConfig):
        raise TypeError("FX plugin requires FXSimulationConfig")
    rollout_config = replace(config, periods=periods) if periods is not None else config
    return run_fx_simulation(rollout_config, seed=seed)


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


_CREDIT_EXPERIMENT = ExperimentSpec(
    "credit.regimes",
    "credit",
    "Compare no-AI, frozen, selective-DDGE, full-information-DDGE, and oracle credit regimes.",
    _credit,
)
_FORECASTING_EXPERIMENT = ExperimentSpec(
    "forecasting.ddge",
    "forecasting",
    "Find and independently verify the forecasting model's DDGE fixed points.",
    _forecasting,
)
_FX_ROLLOUT_EXPERIMENT = ExperimentSpec(
    "fx.rollout",
    "fx",
    "Run the adaptive heterogeneous FX economy and record clearing diagnostics.",
    _fx,
)
_FX_COMPARATIVE_STATICS_EXPERIMENT = ExperimentSpec(
    "fx.comparative_statics",
    "fx",
    "Estimate replicated common-random-number FX effects and uncertainty intervals.",
    _fx_comparative_statics,
)


SCENARIO_REGISTRY = ScenarioRegistry(
    (
        ScenarioPlugin(
            name="credit",
            description=(
                "AI-mediated credit with endogenous decision-flip adoption, selective labels, "
                "full-information retraining, and frozen and omniscient counterfactuals."
            ),
            config_factory=_credit_config,
            ddge_factory=_credit_ddge,
            experiments=(_CREDIT_EXPERIMENT,),
        ),
        ScenarioPlugin(
            name="forecasting",
            description=(
                "A self-fulfilling forecasting Data-Driven Generative Equilibrium with a "
                "pitchfork multiplicity threshold and independent numerical oracles."
            ),
            config_factory=_forecasting_config,
            ddge_factory=_forecasting_ddge,
            rollout_factory=_forecasting_rollout,
            experiments=(_FORECASTING_EXPERIMENT,),
        ),
        ScenarioPlugin(
            name="fx",
            description=(
                "A heterogeneous household, firm, and bank economy with uniform-price batch "
                "clearing, adaptive beliefs, balance feasibility, and conservation diagnostics."
            ),
            config_factory=_fx_config,
            rollout_factory=_fx_rollout,
            experiments=(
                _FX_COMPARATIVE_STATICS_EXPERIMENT,
                _FX_ROLLOUT_EXPERIMENT,
            ),
        ),
        ScenarioPlugin(
            name="scalar",
            description=(
                "Cong's closed-form scalar DDGE laboratory for displacement, multiplicity, "
                "amplification, instability, and damping."
            ),
            config_factory=_scalar_config,
            ddge_factory=_scalar_ddge,
        ),
    )
)
SCENARIO_DESCRIPTIONS: Mapping[str, str] = MappingProxyType(
    {name: plugin.description for name, plugin in SCENARIO_REGISTRY.scenarios.items()}
)
EXPERIMENTS: Mapping[str, ExperimentSpec] = SCENARIO_REGISTRY.experiments


def experiment_spec(name: str) -> ExperimentSpec:
    """Resolve one experiment or raise an error listing valid choices."""

    return SCENARIO_REGISTRY.experiment(name)
