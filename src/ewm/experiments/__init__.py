"""Discoverable, reproducible experiment execution."""

from .claims import (
    ClaimAuthorization,
    ClaimEvidence,
    ClaimKind,
    UnsupportedClaimError,
    authorize_claims,
)
from .credit import (
    CreditOracleReport,
    CreditOrderingComparison,
    CreditPaperTargetReport,
    CreditTargetComparison,
    credit_oracle_report,
    credit_paper_target_report,
    run_credit_regimes,
)
from .evaluation import LAYER_METRICS, MetricEvidence, evaluate_layered
from .fx import replicated_fx_comparisons
from .production import solve_production_equilibrium
from .registry import EXPERIMENTS, SCENARIO_DESCRIPTIONS, experiment_spec
from .runner import ExperimentRun, run_experiment
from .statistics import PairedEstimate, paired_estimate

__all__ = [
    "EXPERIMENTS",
    "LAYER_METRICS",
    "SCENARIO_DESCRIPTIONS",
    "ClaimAuthorization",
    "ClaimEvidence",
    "ClaimKind",
    "CreditOracleReport",
    "CreditOrderingComparison",
    "CreditPaperTargetReport",
    "CreditTargetComparison",
    "ExperimentRun",
    "MetricEvidence",
    "PairedEstimate",
    "UnsupportedClaimError",
    "authorize_claims",
    "credit_oracle_report",
    "credit_paper_target_report",
    "evaluate_layered",
    "experiment_spec",
    "paired_estimate",
    "replicated_fx_comparisons",
    "run_credit_regimes",
    "run_experiment",
    "solve_production_equilibrium",
]
