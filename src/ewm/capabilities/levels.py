"""Machine-checkable evidence gates for Han et al.'s cumulative EWM ladder."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from types import MappingProxyType

from ewm.core.evidence import EvidenceStatus, ValidatedEvidenceArtifact


class CapabilityLevel(IntEnum):
    """Cumulative EWM capability level, including L0 for insufficient evidence."""

    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4
    L5 = 5
    L6 = 6


class EvidenceKind(StrEnum):
    """Increasing evidence strength; labels alone have no gate value."""

    SELF_REPORT = "self_report"
    INTERFACE = "interface"
    SYNTHETIC_TEST = "synthetic_test"
    CONTROLLED_EXPERIMENT = "controlled_experiment"
    EXTERNAL_VALIDATION = "external_validation"


class LevelRequirement(StrEnum):
    """Observable prerequisites used by the cumulative capability assessment."""

    AGENT_WORLD_EXECUTION = "agent_world_execution"
    ENDOGENOUS_ENVIRONMENT = "endogenous_environment"
    ECONOMIC_INVARIANTS = "economic_invariants"
    ADAPTIVE_AGENT_STATE = "adaptive_agent_state"
    LONGITUDINAL_PERSISTENCE = "longitudinal_persistence"
    LANGUAGE_MODEL_EXECUTION = "language_model_execution"
    EXPLICIT_COGNITIVE_STATE = "explicit_cognitive_state"
    MEMORY_AND_TOOLS = "memory_and_tools"
    COGNITIVE_BEHAVIOR_EVALUATION = "cognitive_behavior_evaluation"
    CAPABILITY_PROPOSAL = "capability_proposal"
    GATED_CAPABILITY_PROMOTION = "gated_capability_promotion"
    PERSISTENT_CAPABILITY_IMPROVEMENT = "persistent_capability_improvement"
    CAPABILITY_ROLLBACK = "capability_rollback"
    ENDOGENOUS_INSTITUTION_PROPOSAL = "endogenous_institution_proposal"
    CONSTITUTIONAL_INSTITUTION_GATE = "constitutional_institution_gate"
    ACCEPTED_INSTITUTION_CHANGE = "accepted_institution_change"
    INSTITUTIONAL_OUTCOME_EVALUATION = "institutional_outcome_evaluation"
    EXTERNAL_DATA_CONTRACT = "external_data_contract"
    REPEATED_OUT_OF_SAMPLE_ALIGNMENT = "repeated_out_of_sample_alignment"
    DRIFT_MONITORING = "drift_monitoring"
    CORRECTION_PERFORMANCE = "correction_performance"


class AxisStatus(StrEnum):
    """Support status for an assessment axis independent of capability level."""

    NOT_ASSESSED = "not_assessed"
    SUPPORTED = "supported"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class CapabilityEvidence:
    """One caller-asserted observation about a level requirement."""

    requirement: LevelRequirement
    passed: bool
    kind: EvidenceKind
    provenance: str
    observations: int = 1

    def __post_init__(self) -> None:
        if not self.provenance:
            raise ValueError("capability evidence provenance must not be empty")
        if self.observations < 1:
            raise ValueError("capability evidence observations must be positive")


@dataclass(frozen=True, slots=True)
class AxisEvidence:
    """Evidence for DDGE consistency or empirical validity, never for level inference."""

    passed: bool
    kind: EvidenceKind
    provenance: str

    def __post_init__(self) -> None:
        if not self.provenance:
            raise ValueError("axis evidence provenance must not be empty")


@dataclass(frozen=True, slots=True)
class ValidatedCapabilityEvidence:
    """A capability assertion bound to an observed validation artifact."""

    assertion: CapabilityEvidence
    artifact: ValidatedEvidenceArtifact

    def __post_init__(self) -> None:
        expected_subject = f"capability:{self.assertion.requirement.value}"
        if self.artifact.subject != expected_subject:
            raise ValueError(
                f"capability artifact subject must be {expected_subject!r}; "
                f"got {self.artifact.subject!r}"
            )


@dataclass(frozen=True, slots=True)
class AxisAssessment:
    """Independent result for one model-quality axis."""

    status: AxisStatus
    provenance: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapabilityAssessment:
    """Cumulative level result, requirement gaps, provenance, and separate validity axes."""

    achieved_level: CapabilityLevel
    satisfied_requirements: tuple[LevelRequirement, ...]
    missing_requirements: tuple[LevelRequirement, ...]
    evidence_provenance: Mapping[LevelRequirement, tuple[str, ...]]
    warnings: tuple[str, ...]
    ddge_consistency: AxisAssessment
    empirical_validity: AxisAssessment

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evidence_provenance",
            MappingProxyType(dict(self.evidence_provenance)),
        )


@dataclass(frozen=True, slots=True)
class _RequirementGate:
    minimum_kind: EvidenceKind
    minimum_observations: int = 1


_EVIDENCE_RANK = {
    EvidenceKind.SELF_REPORT: 0,
    EvidenceKind.INTERFACE: 1,
    EvidenceKind.SYNTHETIC_TEST: 2,
    EvidenceKind.CONTROLLED_EXPERIMENT: 3,
    EvidenceKind.EXTERNAL_VALIDATION: 4,
}

LEVEL_REQUIREMENTS: Mapping[CapabilityLevel, tuple[LevelRequirement, ...]] = MappingProxyType(
    {
        CapabilityLevel.L1: (
            LevelRequirement.AGENT_WORLD_EXECUTION,
            LevelRequirement.ENDOGENOUS_ENVIRONMENT,
            LevelRequirement.ECONOMIC_INVARIANTS,
        ),
        CapabilityLevel.L2: (
            LevelRequirement.ADAPTIVE_AGENT_STATE,
            LevelRequirement.LONGITUDINAL_PERSISTENCE,
        ),
        CapabilityLevel.L3: (
            LevelRequirement.LANGUAGE_MODEL_EXECUTION,
            LevelRequirement.EXPLICIT_COGNITIVE_STATE,
            LevelRequirement.MEMORY_AND_TOOLS,
            LevelRequirement.COGNITIVE_BEHAVIOR_EVALUATION,
        ),
        CapabilityLevel.L4: (
            LevelRequirement.CAPABILITY_PROPOSAL,
            LevelRequirement.GATED_CAPABILITY_PROMOTION,
            LevelRequirement.PERSISTENT_CAPABILITY_IMPROVEMENT,
            LevelRequirement.CAPABILITY_ROLLBACK,
        ),
        CapabilityLevel.L5: (
            LevelRequirement.ENDOGENOUS_INSTITUTION_PROPOSAL,
            LevelRequirement.CONSTITUTIONAL_INSTITUTION_GATE,
            LevelRequirement.ACCEPTED_INSTITUTION_CHANGE,
            LevelRequirement.INSTITUTIONAL_OUTCOME_EVALUATION,
        ),
        CapabilityLevel.L6: (
            LevelRequirement.EXTERNAL_DATA_CONTRACT,
            LevelRequirement.REPEATED_OUT_OF_SAMPLE_ALIGNMENT,
            LevelRequirement.DRIFT_MONITORING,
            LevelRequirement.CORRECTION_PERFORMANCE,
        ),
    }
)

_GATES: Mapping[LevelRequirement, _RequirementGate] = MappingProxyType(
    {
        LevelRequirement.AGENT_WORLD_EXECUTION: _RequirementGate(
            EvidenceKind.SYNTHETIC_TEST
        ),
        LevelRequirement.ENDOGENOUS_ENVIRONMENT: _RequirementGate(
            EvidenceKind.SYNTHETIC_TEST
        ),
        LevelRequirement.ECONOMIC_INVARIANTS: _RequirementGate(
            EvidenceKind.SYNTHETIC_TEST
        ),
        LevelRequirement.ADAPTIVE_AGENT_STATE: _RequirementGate(
            EvidenceKind.CONTROLLED_EXPERIMENT
        ),
        LevelRequirement.LONGITUDINAL_PERSISTENCE: _RequirementGate(
            EvidenceKind.CONTROLLED_EXPERIMENT
        ),
        LevelRequirement.LANGUAGE_MODEL_EXECUTION: _RequirementGate(
            EvidenceKind.CONTROLLED_EXPERIMENT
        ),
        LevelRequirement.EXPLICIT_COGNITIVE_STATE: _RequirementGate(
            EvidenceKind.SYNTHETIC_TEST
        ),
        LevelRequirement.MEMORY_AND_TOOLS: _RequirementGate(
            EvidenceKind.SYNTHETIC_TEST
        ),
        LevelRequirement.COGNITIVE_BEHAVIOR_EVALUATION: _RequirementGate(
            EvidenceKind.CONTROLLED_EXPERIMENT,
            minimum_observations=2,
        ),
        LevelRequirement.CAPABILITY_PROPOSAL: _RequirementGate(
            EvidenceKind.CONTROLLED_EXPERIMENT
        ),
        LevelRequirement.GATED_CAPABILITY_PROMOTION: _RequirementGate(
            EvidenceKind.SYNTHETIC_TEST
        ),
        LevelRequirement.PERSISTENT_CAPABILITY_IMPROVEMENT: _RequirementGate(
            EvidenceKind.CONTROLLED_EXPERIMENT,
            minimum_observations=2,
        ),
        LevelRequirement.CAPABILITY_ROLLBACK: _RequirementGate(
            EvidenceKind.SYNTHETIC_TEST
        ),
        LevelRequirement.ENDOGENOUS_INSTITUTION_PROPOSAL: _RequirementGate(
            EvidenceKind.CONTROLLED_EXPERIMENT
        ),
        LevelRequirement.CONSTITUTIONAL_INSTITUTION_GATE: _RequirementGate(
            EvidenceKind.SYNTHETIC_TEST
        ),
        LevelRequirement.ACCEPTED_INSTITUTION_CHANGE: _RequirementGate(
            EvidenceKind.CONTROLLED_EXPERIMENT
        ),
        LevelRequirement.INSTITUTIONAL_OUTCOME_EVALUATION: _RequirementGate(
            EvidenceKind.CONTROLLED_EXPERIMENT,
            minimum_observations=2,
        ),
        LevelRequirement.EXTERNAL_DATA_CONTRACT: _RequirementGate(
            EvidenceKind.EXTERNAL_VALIDATION
        ),
        LevelRequirement.REPEATED_OUT_OF_SAMPLE_ALIGNMENT: _RequirementGate(
            EvidenceKind.EXTERNAL_VALIDATION,
            minimum_observations=2,
        ),
        LevelRequirement.DRIFT_MONITORING: _RequirementGate(
            EvidenceKind.EXTERNAL_VALIDATION,
            minimum_observations=2,
        ),
        LevelRequirement.CORRECTION_PERFORMANCE: _RequirementGate(
            EvidenceKind.EXTERNAL_VALIDATION,
            minimum_observations=2,
        ),
    }
)


def assess_capability(
    evidence: Iterable[CapabilityEvidence],
    *,
    ddge_evidence: Iterable[AxisEvidence] = (),
    empirical_evidence: Iterable[AxisEvidence] = (),
) -> CapabilityAssessment:
    """Assess the cumulative ladder without inferring validity from interfaces or labels."""

    by_requirement: dict[LevelRequirement, list[CapabilityEvidence]] = {
        requirement: [] for requirement in LevelRequirement
    }
    for item in evidence:
        by_requirement[item.requirement].append(item)

    satisfied: list[LevelRequirement] = []
    missing: list[LevelRequirement] = []
    provenance: dict[LevelRequirement, tuple[str, ...]] = {}
    warnings: list[str] = []
    for requirement in LevelRequirement:
        gate = _GATES[requirement]
        qualifying: list[CapabilityEvidence] = []
        for item in by_requirement[requirement]:
            if not item.passed:
                warnings.append(
                    f"{requirement.value}: failed evidence at {item.provenance}"
                )
                continue
            if _EVIDENCE_RANK[item.kind] < _EVIDENCE_RANK[gate.minimum_kind]:
                warnings.append(
                    f"{requirement.value}: insufficient evidence class "
                    f"{item.kind.value} at {item.provenance}; "
                    f"requires {gate.minimum_kind.value}"
                )
                continue
            if item.observations < gate.minimum_observations:
                warnings.append(
                    f"{requirement.value}: requires at least "
                    f"{gate.minimum_observations} observations; got {item.observations}"
                )
                continue
            qualifying.append(item)
        if qualifying:
            satisfied.append(requirement)
            provenance[requirement] = tuple(
                sorted({item.provenance for item in qualifying})
            )
        else:
            missing.append(requirement)

    satisfied_set = set(satisfied)
    cumulative: set[LevelRequirement] = set()
    achieved = CapabilityLevel.L0
    for level in (
        CapabilityLevel.L1,
        CapabilityLevel.L2,
        CapabilityLevel.L3,
        CapabilityLevel.L4,
        CapabilityLevel.L5,
        CapabilityLevel.L6,
    ):
        cumulative.update(LEVEL_REQUIREMENTS[level])
        if cumulative.issubset(satisfied_set):
            achieved = level
        else:
            break

    ddge = _assess_axis(
        ddge_evidence,
        minimum_kind=EvidenceKind.SYNTHETIC_TEST,
        label="DDGE consistency",
    )
    empirical = _assess_axis(
        empirical_evidence,
        minimum_kind=EvidenceKind.EXTERNAL_VALIDATION,
        label="empirical validity",
    )
    warnings.extend(ddge.warnings)
    warnings.extend(empirical.warnings)
    return CapabilityAssessment(
        achieved_level=achieved,
        satisfied_requirements=tuple(satisfied),
        missing_requirements=tuple(missing),
        evidence_provenance=provenance,
        warnings=tuple(warnings),
        ddge_consistency=ddge,
        empirical_validity=empirical,
    )


def assess_validated_capability(
    evidence: Iterable[ValidatedCapabilityEvidence | CapabilityEvidence],
) -> CapabilityAssessment:
    """Assess official capability only from passing validation artifacts."""

    validated: list[CapabilityEvidence] = []
    for item in evidence:
        if not isinstance(item, ValidatedCapabilityEvidence):
            raise TypeError(
                "official assessment requires validated capability evidence; "
                "caller assertions are insufficient"
            )
        assertion = item.assertion
        validated.append(
            CapabilityEvidence(
                requirement=assertion.requirement,
                passed=(
                    assertion.passed and item.artifact.status is EvidenceStatus.PASS
                ),
                kind=assertion.kind,
                provenance=assertion.provenance,
                observations=min(assertion.observations, item.artifact.observations),
            )
        )
    return assess_capability(validated)


def documented_prototype_evidence() -> tuple[CapabilityEvidence, ...]:
    """Return the repository's conservative, provenance-bearing capability evidence."""

    return (
        CapabilityEvidence(
            LevelRequirement.AGENT_WORLD_EXECUTION,
            True,
            EvidenceKind.SYNTHETIC_TEST,
            "tests/scenarios/test_fx.py",
        ),
        CapabilityEvidence(
            LevelRequirement.ENDOGENOUS_ENVIRONMENT,
            True,
            EvidenceKind.SYNTHETIC_TEST,
            "tests/scenarios/test_fx.py",
        ),
        CapabilityEvidence(
            LevelRequirement.ECONOMIC_INVARIANTS,
            True,
            EvidenceKind.SYNTHETIC_TEST,
            "tests/properties/test_fx_accounting.py",
        ),
        CapabilityEvidence(
            LevelRequirement.ADAPTIVE_AGENT_STATE,
            True,
            EvidenceKind.CONTROLLED_EXPERIMENT,
            "tests/scenarios/test_fx.py",
        ),
        CapabilityEvidence(
            LevelRequirement.LONGITUDINAL_PERSISTENCE,
            True,
            EvidenceKind.CONTROLLED_EXPERIMENT,
            "tests/scenarios/test_fx.py",
        ),
        CapabilityEvidence(
            LevelRequirement.LANGUAGE_MODEL_EXECUTION,
            True,
            EvidenceKind.SYNTHETIC_TEST,
            "tests/unit/test_cognition.py:fake-backend",
        ),
        CapabilityEvidence(
            LevelRequirement.EXPLICIT_COGNITIVE_STATE,
            True,
            EvidenceKind.SYNTHETIC_TEST,
            "tests/unit/test_cognition.py",
        ),
        CapabilityEvidence(
            LevelRequirement.MEMORY_AND_TOOLS,
            True,
            EvidenceKind.SYNTHETIC_TEST,
            "tests/unit/test_cognition.py",
        ),
        CapabilityEvidence(
            LevelRequirement.GATED_CAPABILITY_PROMOTION,
            True,
            EvidenceKind.SYNTHETIC_TEST,
            "tests/unit/test_capability_evolution.py",
        ),
        CapabilityEvidence(
            LevelRequirement.CAPABILITY_ROLLBACK,
            True,
            EvidenceKind.SYNTHETIC_TEST,
            "tests/unit/test_capability_evolution.py",
        ),
        CapabilityEvidence(
            LevelRequirement.CONSTITUTIONAL_INSTITUTION_GATE,
            True,
            EvidenceKind.SYNTHETIC_TEST,
            "tests/unit/test_institutions.py",
        ),
        CapabilityEvidence(
            LevelRequirement.ACCEPTED_INSTITUTION_CHANGE,
            True,
            EvidenceKind.SYNTHETIC_TEST,
            "tests/unit/test_institutions.py",
        ),
        CapabilityEvidence(
            LevelRequirement.EXTERNAL_DATA_CONTRACT,
            True,
            EvidenceKind.SYNTHETIC_TEST,
            "examples/offline_alignment.py:fixture-only",
        ),
        CapabilityEvidence(
            LevelRequirement.REPEATED_OUT_OF_SAMPLE_ALIGNMENT,
            True,
            EvidenceKind.SYNTHETIC_TEST,
            "tests/unit/test_alignment.py:single-fixture",
        ),
    )


def _assess_axis(
    evidence: Iterable[AxisEvidence],
    *,
    minimum_kind: EvidenceKind,
    label: str,
) -> AxisAssessment:
    qualified: list[AxisEvidence] = []
    warnings: list[str] = []
    for item in evidence:
        if _EVIDENCE_RANK[item.kind] < _EVIDENCE_RANK[minimum_kind]:
            warnings.append(
                f"{label}: ignored {item.kind.value} evidence at {item.provenance}"
            )
        else:
            qualified.append(item)
    if not qualified:
        status = AxisStatus.NOT_ASSESSED
    elif any(not item.passed for item in qualified):
        status = AxisStatus.FAILED
    else:
        status = AxisStatus.SUPPORTED
    return AxisAssessment(
        status=status,
        provenance=tuple(sorted({item.provenance for item in qualified})),
        warnings=tuple(warnings),
    )
