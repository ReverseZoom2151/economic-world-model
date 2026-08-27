"""Discoverable, reproducible experiment execution."""

from .registry import EXPERIMENTS, SCENARIO_DESCRIPTIONS, experiment_spec
from .runner import ExperimentRun, run_experiment
from .statistics import PairedEstimate, paired_estimate

__all__ = [
    "EXPERIMENTS",
    "SCENARIO_DESCRIPTIONS",
    "ExperimentRun",
    "PairedEstimate",
    "experiment_spec",
    "paired_estimate",
    "run_experiment",
]
