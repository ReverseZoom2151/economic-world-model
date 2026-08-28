"""Immutable model types for scenario and experiment discovery."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ewm.core import DDGEProblem, ExperimentResult
from ewm.scenarios.credit import CreditConfig, CreditRegime
from ewm.scenarios.forecasting import ForecastingConfig
from ewm.scenarios.fx import FXSimulationConfig, FXSimulationResult
from ewm.scenarios.scalar import ScalarConfig


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


# These types were first published from ewm.experiments.registry. Keep their stable module identity
# for repr, pickle, and downstream introspection while the implementation lives in the catalog.
for _public_type in (ExperimentPayload, ExperimentSpec, ScenarioPlugin, ScenarioRegistry):
    _public_type.__module__ = "ewm.experiments.registry"
