"""Scientific preflight and explicit alignment for economic-run comparisons."""

from .contracts import (
    AlignedMeasurement,
    AlignmentEntry,
    AlignmentPlan,
    ComparisonIssue,
    ComparisonPreflight,
    ComparisonResult,
    InterventionIdentity,
    MeasurementComparisonMetadata,
    MultiplicityMetadata,
    PairingMetadata,
    RunComparisonMetadata,
    UnalignedMeasurement,
)
from .service import compare_projections

__all__ = [
    "AlignedMeasurement",
    "AlignmentEntry",
    "AlignmentPlan",
    "ComparisonIssue",
    "ComparisonPreflight",
    "ComparisonResult",
    "InterventionIdentity",
    "MeasurementComparisonMetadata",
    "MultiplicityMetadata",
    "PairingMetadata",
    "RunComparisonMetadata",
    "UnalignedMeasurement",
    "compare_projections",
]
