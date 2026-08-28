"""Scenario configuration, DDGE, and rollout adapters for the default catalog."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from ewm.core import DDGEProblem
from ewm.scenarios.credit import (
    CreditConfig,
    CreditDDGEProblem,
    CreditRegime,
    cong_qualitative_reconstruction,
    generate_population,
)
from ewm.scenarios.credit import research_config as credit_research_config
from ewm.scenarios.forecasting import (
    ForecastingConfig,
    ForecastingProblem,
    simulate_series,
)
from ewm.scenarios.forecasting import research_config as forecasting_research_config
from ewm.scenarios.forecasting import smoke_config as forecasting_smoke_config
from ewm.scenarios.fx import FXSimulationConfig, run_fx_simulation
from ewm.scenarios.fx import research_config as fx_research_config
from ewm.scenarios.fx import smoke_config as fx_smoke_config
from ewm.scenarios.scalar import ScalarConfig, ScalarProblem
from ewm.scenarios.scalar import paper_config as scalar_paper_config

from .models import RolloutResult, ScenarioConfig


def with_overrides(config: ScenarioConfig, overrides: Mapping[str, Any]) -> ScenarioConfig:
    return replace(config, **dict(overrides)) if overrides else config


def forecasting_config(
    preset: str,
    seed: int,
    overrides: Mapping[str, Any],
) -> ScenarioConfig:
    config = forecasting_smoke_config() if preset == "smoke" else forecasting_research_config()
    return with_overrides(replace(config, seed=seed), overrides)


def fx_config(
    preset: str,
    _seed: int,
    overrides: Mapping[str, Any],
) -> ScenarioConfig:
    config = fx_smoke_config() if preset == "smoke" else fx_research_config()
    return with_overrides(config, overrides)


def credit_config(
    preset: str,
    seed: int,
    overrides: Mapping[str, Any],
) -> ScenarioConfig:
    config = (
        cong_qualitative_reconstruction(population_size=800)
        if preset == "smoke"
        else credit_research_config()
    )
    return with_overrides(replace(config, seed=seed), overrides)


def scalar_config(
    _preset: str,
    _seed: int,
    overrides: Mapping[str, Any],
) -> ScenarioConfig:
    return with_overrides(scalar_paper_config(), overrides)


def forecasting_ddge(
    config: ScenarioConfig,
    _regime: CreditRegime,
) -> DDGEProblem:
    if not isinstance(config, ForecastingConfig):
        raise TypeError("forecasting plugin requires ForecastingConfig")
    return ForecastingProblem(config)


def credit_ddge(config: ScenarioConfig, regime: CreditRegime) -> DDGEProblem:
    if not isinstance(config, CreditConfig):
        raise TypeError("credit plugin requires CreditConfig")
    return CreditDDGEProblem(config, generate_population(config), regime)


def scalar_ddge(
    config: ScenarioConfig,
    _regime: CreditRegime,
) -> DDGEProblem:
    if not isinstance(config, ScalarConfig):
        raise TypeError("scalar plugin requires ScalarConfig")
    return ScalarProblem(config)


def forecasting_rollout(
    config: ScenarioConfig,
    seed: int,
    periods: int | None,
    theta: float,
) -> RolloutResult:
    if not isinstance(config, ForecastingConfig):
        raise TypeError("forecasting plugin requires ForecastingConfig")
    rollout_config = replace(config, sample_size=periods) if periods is not None else config
    return simulate_series(theta, rollout_config, seed=seed)


def fx_rollout(
    config: ScenarioConfig,
    seed: int,
    periods: int | None,
    _theta: float,
) -> RolloutResult:
    if not isinstance(config, FXSimulationConfig):
        raise TypeError("FX plugin requires FXSimulationConfig")
    rollout_config = replace(config, periods=periods) if periods is not None else config
    return run_fx_simulation(rollout_config, seed=seed)
