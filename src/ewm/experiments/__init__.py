"""Discoverable, reproducible experiment execution."""

from .credit import (
    CreditOracleReport,
    CreditOrderingComparison,
    CreditPaperTargetReport,
    CreditTargetComparison,
    credit_oracle_report,
    credit_paper_target_report,
    run_credit_regimes,
)
from .fx import replicated_fx_comparisons
from .registry import EXPERIMENTS, SCENARIO_DESCRIPTIONS, experiment_spec
from .runner import ExperimentRun, run_experiment
from .statistics import PairedEstimate, paired_estimate

__all__ = [
    "EXPERIMENTS",
    "SCENARIO_DESCRIPTIONS",
    "CreditOracleReport",
    "CreditOrderingComparison",
    "CreditPaperTargetReport",
    "CreditTargetComparison",
    "ExperimentRun",
    "PairedEstimate",
    "credit_oracle_report",
    "credit_paper_target_report",
    "experiment_spec",
    "paired_estimate",
    "replicated_fx_comparisons",
    "run_credit_regimes",
    "run_experiment",
]
