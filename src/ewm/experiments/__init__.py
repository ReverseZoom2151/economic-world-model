"""Discoverable, reproducible experiment execution."""

from .claims import (
    ClaimAuthorization,
    ClaimEvidence,
    ClaimKind,
    UnsupportedClaimError,
    ValidatedClaimEvidence,
    authorize_claims,
    authorize_validated_claims,
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
from .registry import (
    EXPERIMENTS,
    SCENARIO_DESCRIPTIONS,
    SCENARIO_REGISTRY,
    RolloutResult,
    ScenarioConfig,
    ScenarioPlugin,
    ScenarioRegistry,
    experiment_spec,
)
from .replay import RunReplayError, verify_and_replay_run
from .runner import ExperimentRun, run_experiment
from .statistics import (
    BinomialEstimate,
    HolmCorrection,
    PairedEstimate,
    RobustPairedEstimate,
    holm_correction,
    paired_estimate,
    robust_paired_estimate,
    wilson_interval,
)
from .verification import ArtifactVerificationError, VerificationReport, verify_run

__all__ = [
    "EXPERIMENTS",
    "LAYER_METRICS",
    "SCENARIO_DESCRIPTIONS",
    "SCENARIO_REGISTRY",
    "ArtifactVerificationError",
    "BinomialEstimate",
    "ClaimAuthorization",
    "ClaimEvidence",
    "ClaimKind",
    "CreditOracleReport",
    "CreditOrderingComparison",
    "CreditPaperTargetReport",
    "CreditTargetComparison",
    "ExperimentRun",
    "HolmCorrection",
    "MetricEvidence",
    "PairedEstimate",
    "RobustPairedEstimate",
    "RolloutResult",
    "RunReplayError",
    "ScenarioConfig",
    "ScenarioPlugin",
    "ScenarioRegistry",
    "UnsupportedClaimError",
    "ValidatedClaimEvidence",
    "VerificationReport",
    "authorize_claims",
    "authorize_validated_claims",
    "credit_oracle_report",
    "credit_paper_target_report",
    "evaluate_layered",
    "experiment_spec",
    "holm_correction",
    "paired_estimate",
    "replicated_fx_comparisons",
    "robust_paired_estimate",
    "run_credit_regimes",
    "run_experiment",
    "solve_production_equilibrium",
    "verify_and_replay_run",
    "verify_run",
    "wilson_interval",
]
