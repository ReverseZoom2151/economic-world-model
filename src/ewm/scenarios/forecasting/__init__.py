"""Self-fulfilling forecasting and learning-generated multiplicity."""

from ewm._internal.imports import register_module_aliases

from .economy.model import (
    ForecastingConfig,
    ForecastingProblem,
    finite_sample_retraining_path,
    finite_sample_update,
    population_update,
    simulate_series,
    stationary_samples,
)
from .economy.presets import (
    paper_config,
    paper_finite_sample_config,
    research_config,
    smoke_config,
)
from .validation.oracles import ForecastingOracleReport, oracle_report
from .validation.verification import (
    ForecastingReplicationReport,
    paper_population_roots,
    paper_replication_report,
    sample_first_autocorrelation,
)

register_module_aliases(
    __name__,
    {
        "model": "economy.model",
        "presets": "economy.presets",
        "oracles": "validation.oracles",
        "verification": "validation.verification",
    },
)

__all__ = [
    "ForecastingConfig",
    "ForecastingOracleReport",
    "ForecastingProblem",
    "ForecastingReplicationReport",
    "finite_sample_retraining_path",
    "finite_sample_update",
    "oracle_report",
    "paper_config",
    "paper_finite_sample_config",
    "paper_population_roots",
    "paper_replication_report",
    "population_update",
    "research_config",
    "sample_first_autocorrelation",
    "simulate_series",
    "smoke_config",
    "stationary_samples",
]
