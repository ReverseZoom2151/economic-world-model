"""Stable, deliberately small public facade for worlds and experiments."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ewm.core import DDGEProblem
from ewm.experiments import EXPERIMENTS, SCENARIO_DESCRIPTIONS
from ewm.experiments.runner import ExperimentRun, run_experiment
from ewm.scenarios.credit import (
    CreditConfig,
    CreditDDGEProblem,
    CreditRegime,
    generate_population,
    paper_like_config,
)
from ewm.scenarios.credit import (
    research_config as credit_research_config,
)
from ewm.scenarios.forecasting import (
    ForecastingConfig,
    ForecastingProblem,
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

ScenarioConfig = ForecastingConfig | FXSimulationConfig | CreditConfig | ScalarConfig
RolloutResult = NDArray[np.float64] | FXSimulationResult


@dataclass(frozen=True, slots=True)
class ScenarioHandle:
    """A configured scenario with explicit preset and seed provenance."""

    name: str
    preset: str
    seed: int
    config: ScenarioConfig

    def ddge_problem(
        self,
        *,
        regime: CreditRegime = CreditRegime.SELECTIVE,
    ) -> DDGEProblem:
        """Construct this scenario's declared behavior-data-learning problem."""

        if isinstance(self.config, ForecastingConfig):
            return ForecastingProblem(self.config)
        if isinstance(self.config, CreditConfig):
            return CreditDDGEProblem(
                self.config,
                generate_population(self.config),
                regime,
            )
        if isinstance(self.config, ScalarConfig):
            return ScalarProblem(self.config)
        raise ValueError(f"scenario {self.name!r} does not define a DDGE problem")


def _preset(name: str, preset: str, seed: int) -> ScenarioConfig:
    if preset not in ("smoke", "research"):
        raise ValueError("preset must be 'smoke' or 'research'")
    if name == "forecasting":
        forecasting_config = (
            forecasting_smoke_config()
            if preset == "smoke"
            else forecasting_research_config()
        )
        return replace(forecasting_config, seed=seed)
    if name == "fx":
        return fx_smoke_config() if preset == "smoke" else fx_research_config()
    if name == "credit":
        credit_config = (
            paper_like_config(population_size=800)
            if preset == "smoke"
            else credit_research_config()
        )
        return replace(credit_config, seed=seed)
    if name == "scalar":
        return scalar_paper_config()
    choices = ", ".join(sorted(SCENARIO_DESCRIPTIONS))
    raise ValueError(f"unknown scenario {name!r}; choose from: {choices}")


def make(
    name: str,
    *,
    preset: str = "smoke",
    seed: int = 42,
    **overrides: Any,
) -> ScenarioHandle:
    """Configure a named economic laboratory without running it."""

    config = _preset(name, preset, seed)
    if overrides:
        config = replace(config, **overrides)
    return ScenarioHandle(name=name, preset=preset, seed=seed, config=config)


def rollout(
    scenario: ScenarioHandle,
    *,
    periods: int | None = None,
    theta: float = 0.0,
) -> RolloutResult:
    """Simulate a configured temporal world while holding learned parameters fixed."""

    if periods is not None and periods < 1:
        raise ValueError("periods must be positive")
    if isinstance(scenario.config, ForecastingConfig):
        forecasting_config = (
            replace(scenario.config, sample_size=periods)
            if periods is not None
            else scenario.config
        )
        return simulate_series(theta, forecasting_config, seed=scenario.seed)
    if isinstance(scenario.config, FXSimulationConfig):
        fx_config = (
            replace(scenario.config, periods=periods)
            if periods is not None
            else scenario.config
        )
        return run_fx_simulation(fx_config, seed=scenario.seed)
    raise ValueError(f"scenario {scenario.name!r} does not define a temporal rollout")


def list_scenarios() -> tuple[str, ...]:
    """Return all registered economic laboratories."""

    return tuple(sorted(SCENARIO_DESCRIPTIONS))


def list_experiments() -> tuple[str, ...]:
    """Return all registered reproducible experiments."""

    return tuple(sorted(EXPERIMENTS))


def describe(name: str) -> str:
    """Describe a registered scenario or experiment."""

    if name in SCENARIO_DESCRIPTIONS:
        return SCENARIO_DESCRIPTIONS[name]
    if name in EXPERIMENTS:
        return EXPERIMENTS[name].description
    choices = ", ".join((*list_scenarios(), *list_experiments()))
    raise ValueError(f"unknown scenario or experiment {name!r}; choose from: {choices}")


__all__ = [
    "ExperimentRun",
    "RolloutResult",
    "ScenarioHandle",
    "describe",
    "list_experiments",
    "list_scenarios",
    "make",
    "rollout",
    "run_experiment",
]
