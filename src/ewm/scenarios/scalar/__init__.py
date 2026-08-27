"""Exact implementation of Cong's Appendix A.8 and Laboratory II scalar model."""

from .model import (
    ScalarConfig,
    ScalarDisplacement,
    ScalarInnerSolution,
    ScalarLearner,
    ScalarProblem,
    inner_solution,
    linear_displacement,
    near_onset_expansion,
    outer_derivative,
    outer_update,
    paper_config,
    retraining_path,
)
from .verification import (
    ScalarVerificationReport,
    bracketed_fixed_points,
    scalar_verification_report,
)

__all__ = [
    "ScalarConfig",
    "ScalarDisplacement",
    "ScalarInnerSolution",
    "ScalarLearner",
    "ScalarProblem",
    "ScalarVerificationReport",
    "bracketed_fixed_points",
    "inner_solution",
    "linear_displacement",
    "near_onset_expansion",
    "outer_derivative",
    "outer_update",
    "paper_config",
    "retraining_path",
    "scalar_verification_report",
]
