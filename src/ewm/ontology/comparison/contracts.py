"""Immutable scientific preflight, alignment, and result contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

from ewm.core.domain.records import freeze_value

from ..graph.model import OntologyRef

ComparisonSide: TypeAlias = Literal["left", "right"]


@dataclass(frozen=True, slots=True)
class InterventionIdentity:
    """Intervention family shared by a comparison and its run-specific level."""

    family: str
    level: str


@dataclass(frozen=True, slots=True)
class PairingMetadata:
    """Exact pairing method and ordered random seeds."""

    method: str
    seeds: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class MultiplicityMetadata:
    """Prespecified multiplicity correction and ordered hypothesis family."""

    method: str
    alpha: float
    family: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RunComparisonMetadata:
    """Evidence-bearing identities required before two runs may be aligned."""

    run: OntologyRef
    ontology_schema: str
    world_identity: str
    protocol_identity: str
    software_identity: str
    intervention: InterventionIdentity
    pairing: PairingMetadata
    multiplicity: MultiplicityMetadata


@dataclass(frozen=True, slots=True)
class MeasurementComparisonMetadata:
    """Explicit semantic join key and measurement design identities."""

    measurement: OntologyRef
    comparison_key: str
    estimand_identity: str
    sample_identity: str
    estimator_identity: str
    paired_seeds: tuple[int, ...]
    hypothesis_id: str


@dataclass(frozen=True, slots=True)
class ComparisonIssue:
    """One deterministic preflight rejection or partial-alignment diagnostic."""

    code: str
    scope: Literal["run", "measurement"]
    message: str
    left: str | tuple[int, ...] | None
    right: str | tuple[int, ...] | None
    blocking: bool


@dataclass(frozen=True, slots=True)
class ComparisonPreflight:
    """Compatibility decision emitted before any aligned values."""

    compatible: bool
    issues: tuple[ComparisonIssue, ...]
    left: RunComparisonMetadata | None
    right: RunComparisonMetadata | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "issues", tuple(self.issues))


@dataclass(frozen=True, slots=True)
class AlignmentEntry:
    """One explicit semantic-key join selected by a deterministic plan."""

    comparison_key: str
    left_measurement: OntologyRef
    right_measurement: OntologyRef


@dataclass(frozen=True, slots=True)
class AlignmentPlan:
    """Deterministic accepted joins and all records withheld from alignment."""

    entries: tuple[AlignmentEntry, ...]
    unaligned_measurement_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "entries", tuple(self.entries))
        object.__setattr__(
            self,
            "unaligned_measurement_ids",
            tuple(self.unaligned_measurement_ids),
        )


@dataclass(frozen=True, slots=True)
class AlignedMeasurement:
    """Two compatible values with their full pairing and multiplicity design."""

    comparison_key: str
    estimand_identity: str
    sample_identity: str
    estimator_identity: str
    hypothesis_id: str
    unit: str
    left_measurement: OntologyRef
    right_measurement: OntologyRef
    left_name: str
    right_name: str
    left_value: Any
    right_value: Any
    left_intervention: InterventionIdentity
    right_intervention: InterventionIdentity
    pairing: PairingMetadata
    multiplicity: MultiplicityMetadata

    def __post_init__(self) -> None:
        object.__setattr__(self, "left_value", freeze_value(self.left_value))
        object.__setattr__(self, "right_value", freeze_value(self.right_value))


@dataclass(frozen=True, slots=True)
class UnalignedMeasurement:
    """One measurement withheld with an exact, machine-readable reason."""

    side: ComparisonSide
    measurement_id: str
    comparison_key: str | None
    reason_code: str
    reason: str


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """Preflight-first comparison output with no implicit alignment."""

    preflight: ComparisonPreflight
    plan: AlignmentPlan
    aligned: tuple[AlignedMeasurement, ...]
    unaligned: tuple[UnalignedMeasurement, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "aligned", tuple(self.aligned))
        object.__setattr__(self, "unaligned", tuple(self.unaligned))
