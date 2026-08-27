"""Self-fulfilling forecasting and learning-generated multiplicity."""

from .model import (
    ForecastingConfig,
    ForecastingProblem,
    finite_sample_update,
    population_update,
    simulate_series,
    stationary_samples,
)
from .oracles import ForecastingOracleReport, oracle_report
from .presets import research_config, smoke_config

__all__ = [
    "ForecastingConfig",
    "ForecastingOracleReport",
    "ForecastingProblem",
    "finite_sample_update",
    "oracle_report",
    "population_update",
    "research_config",
    "simulate_series",
    "smoke_config",
    "stationary_samples",
]
