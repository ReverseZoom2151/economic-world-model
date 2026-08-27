"""Self-fulfilling forecasting and learning-generated multiplicity."""

from .model import (
    ForecastingConfig,
    ForecastingProblem,
    finite_sample_retraining_path,
    finite_sample_update,
    population_update,
    simulate_series,
    stationary_samples,
)
from .oracles import ForecastingOracleReport, oracle_report
from .presets import (
    paper_config,
    paper_finite_sample_config,
    research_config,
    smoke_config,
)
from .verification import (
    ForecastingReplicationReport,
    paper_population_roots,
    paper_replication_report,
    sample_first_autocorrelation,
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
