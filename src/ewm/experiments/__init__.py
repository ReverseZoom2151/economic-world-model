"""Discoverable, reproducible experiment execution."""

from .credit import CreditOracleReport, credit_oracle_report, run_credit_regimes
from .registry import EXPERIMENTS, SCENARIO_DESCRIPTIONS, experiment_spec
from .runner import ExperimentRun, run_experiment
from .statistics import PairedEstimate, paired_estimate

__all__ = [
    "EXPERIMENTS",
    "SCENARIO_DESCRIPTIONS",
    "CreditOracleReport",
    "ExperimentRun",
    "PairedEstimate",
    "credit_oracle_report",
    "experiment_spec",
    "paired_estimate",
    "run_credit_regimes",
    "run_experiment",
]
