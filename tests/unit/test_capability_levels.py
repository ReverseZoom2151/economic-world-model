from __future__ import annotations

from ewm.capabilities import (
    AxisEvidence,
    AxisStatus,
    CapabilityEvidence,
    CapabilityLevel,
    EvidenceKind,
    LevelRequirement,
    assess_capability,
)


def _evidence(
    requirement: LevelRequirement,
    *,
    kind: EvidenceKind,
    observations: int = 1,
    passed: bool = True,
) -> CapabilityEvidence:
    return CapabilityEvidence(
        requirement=requirement,
        passed=passed,
        kind=kind,
        provenance=f"evidence/{requirement.value}.json",
        observations=observations,
    )


def _through_l2() -> list[CapabilityEvidence]:
    synthetic = EvidenceKind.SYNTHETIC_TEST
    controlled = EvidenceKind.CONTROLLED_EXPERIMENT
    return [
        _evidence(LevelRequirement.AGENT_WORLD_EXECUTION, kind=synthetic),
        _evidence(LevelRequirement.ENDOGENOUS_ENVIRONMENT, kind=synthetic),
        _evidence(LevelRequirement.ECONOMIC_INVARIANTS, kind=synthetic),
        _evidence(LevelRequirement.ADAPTIVE_AGENT_STATE, kind=controlled),
        _evidence(LevelRequirement.LONGITUDINAL_PERSISTENCE, kind=controlled),
    ]


def _through_l3() -> list[CapabilityEvidence]:
    evidence = _through_l2()
    evidence.extend(
        [
            _evidence(
                LevelRequirement.LANGUAGE_MODEL_EXECUTION,
                kind=EvidenceKind.CONTROLLED_EXPERIMENT,
            ),
            _evidence(
                LevelRequirement.EXPLICIT_COGNITIVE_STATE,
                kind=EvidenceKind.SYNTHETIC_TEST,
            ),
            _evidence(
                LevelRequirement.MEMORY_AND_TOOLS,
                kind=EvidenceKind.SYNTHETIC_TEST,
            ),
            _evidence(
                LevelRequirement.COGNITIVE_BEHAVIOR_EVALUATION,
                kind=EvidenceKind.CONTROLLED_EXPERIMENT,
                observations=2,
            ),
        ]
    )
    return evidence


def _through_l4() -> list[CapabilityEvidence]:
    evidence = _through_l3()
    evidence.extend(
        [
            _evidence(
                LevelRequirement.CAPABILITY_PROPOSAL,
                kind=EvidenceKind.CONTROLLED_EXPERIMENT,
            ),
            _evidence(
                LevelRequirement.GATED_CAPABILITY_PROMOTION,
                kind=EvidenceKind.SYNTHETIC_TEST,
            ),
            _evidence(
                LevelRequirement.PERSISTENT_CAPABILITY_IMPROVEMENT,
                kind=EvidenceKind.CONTROLLED_EXPERIMENT,
                observations=2,
            ),
            _evidence(
                LevelRequirement.CAPABILITY_ROLLBACK,
                kind=EvidenceKind.SYNTHETIC_TEST,
            ),
        ]
    )
    return evidence


def _through_l5() -> list[CapabilityEvidence]:
    evidence = _through_l4()
    evidence.extend(
        [
            _evidence(
                LevelRequirement.ENDOGENOUS_INSTITUTION_PROPOSAL,
                kind=EvidenceKind.CONTROLLED_EXPERIMENT,
            ),
            _evidence(
                LevelRequirement.CONSTITUTIONAL_INSTITUTION_GATE,
                kind=EvidenceKind.SYNTHETIC_TEST,
            ),
            _evidence(
                LevelRequirement.ACCEPTED_INSTITUTION_CHANGE,
                kind=EvidenceKind.CONTROLLED_EXPERIMENT,
            ),
            _evidence(
                LevelRequirement.INSTITUTIONAL_OUTCOME_EVALUATION,
                kind=EvidenceKind.CONTROLLED_EXPERIMENT,
                observations=2,
            ),
        ]
    )
    return evidence


def test_fake_backend_and_interfaces_do_not_award_l3() -> None:
    evidence = _through_l2()
    evidence.extend(
        [
            _evidence(
                LevelRequirement.LANGUAGE_MODEL_EXECUTION,
                kind=EvidenceKind.SYNTHETIC_TEST,
            ),
            _evidence(
                LevelRequirement.EXPLICIT_COGNITIVE_STATE,
                kind=EvidenceKind.INTERFACE,
            ),
            _evidence(
                LevelRequirement.MEMORY_AND_TOOLS,
                kind=EvidenceKind.SYNTHETIC_TEST,
            ),
            _evidence(
                LevelRequirement.COGNITIVE_BEHAVIOR_EVALUATION,
                kind=EvidenceKind.SELF_REPORT,
                observations=100,
            ),
        ]
    )

    assessment = assess_capability(evidence)

    assert assessment.achieved_level is CapabilityLevel.L2
    assert LevelRequirement.LANGUAGE_MODEL_EXECUTION in assessment.missing_requirements
    assert LevelRequirement.COGNITIVE_BEHAVIOR_EVALUATION in assessment.missing_requirements
    assert any("insufficient evidence class" in warning for warning in assessment.warnings)


def test_ladder_is_cumulative_even_when_higher_level_artifacts_exist() -> None:
    evidence = _through_l2()
    evidence.extend(
        [
            _evidence(
                LevelRequirement.GATED_CAPABILITY_PROMOTION,
                kind=EvidenceKind.SYNTHETIC_TEST,
            ),
            _evidence(
                LevelRequirement.CAPABILITY_ROLLBACK,
                kind=EvidenceKind.SYNTHETIC_TEST,
            ),
        ]
    )

    assessment = assess_capability(evidence)

    assert assessment.achieved_level is CapabilityLevel.L2
    assert LevelRequirement.GATED_CAPABILITY_PROMOTION in assessment.satisfied_requirements
    assert LevelRequirement.LANGUAGE_MODEL_EXECUTION in assessment.missing_requirements


def test_controlled_language_model_and_behavior_evidence_award_l3_only() -> None:
    assessment = assess_capability(_through_l3())

    assert assessment.achieved_level is CapabilityLevel.L3
    assert assessment.evidence_provenance[
        LevelRequirement.COGNITIVE_BEHAVIOR_EVALUATION
    ] == ("evidence/cognitive_behavior_evaluation.json",)


def test_single_external_correction_does_not_award_l6() -> None:
    evidence = _through_l5()
    evidence.extend(
        [
            _evidence(
                LevelRequirement.EXTERNAL_DATA_CONTRACT,
                kind=EvidenceKind.EXTERNAL_VALIDATION,
            ),
            _evidence(
                LevelRequirement.REPEATED_OUT_OF_SAMPLE_ALIGNMENT,
                kind=EvidenceKind.EXTERNAL_VALIDATION,
                observations=1,
            ),
            _evidence(
                LevelRequirement.DRIFT_MONITORING,
                kind=EvidenceKind.EXTERNAL_VALIDATION,
                observations=1,
            ),
            _evidence(
                LevelRequirement.CORRECTION_PERFORMANCE,
                kind=EvidenceKind.EXTERNAL_VALIDATION,
                observations=1,
            ),
        ]
    )

    assessment = assess_capability(evidence)

    assert assessment.achieved_level is CapabilityLevel.L5
    assert LevelRequirement.REPEATED_OUT_OF_SAMPLE_ALIGNMENT in (
        assessment.missing_requirements
    )
    assert any("requires at least 2 observations" in item for item in assessment.warnings)


def test_repeated_external_evidence_can_award_l6() -> None:
    evidence = _through_l5()
    evidence.extend(
        [
            _evidence(
                LevelRequirement.EXTERNAL_DATA_CONTRACT,
                kind=EvidenceKind.EXTERNAL_VALIDATION,
            ),
            _evidence(
                LevelRequirement.REPEATED_OUT_OF_SAMPLE_ALIGNMENT,
                kind=EvidenceKind.EXTERNAL_VALIDATION,
                observations=3,
            ),
            _evidence(
                LevelRequirement.DRIFT_MONITORING,
                kind=EvidenceKind.EXTERNAL_VALIDATION,
                observations=3,
            ),
            _evidence(
                LevelRequirement.CORRECTION_PERFORMANCE,
                kind=EvidenceKind.EXTERNAL_VALIDATION,
                observations=3,
            ),
        ]
    )

    assert assess_capability(evidence).achieved_level is CapabilityLevel.L6


def test_ddge_and_empirical_validity_are_reported_on_separate_axes() -> None:
    assessment = assess_capability(
        [],
        ddge_evidence=[
            AxisEvidence(
                passed=True,
                kind=EvidenceKind.SYNTHETIC_TEST,
                provenance="certificates/ddge.json",
            )
        ],
        empirical_evidence=[
            AxisEvidence(
                passed=False,
                kind=EvidenceKind.EXTERNAL_VALIDATION,
                provenance="holdout/failed.json",
            )
        ],
    )

    assert assessment.achieved_level is CapabilityLevel.L0
    assert assessment.ddge_consistency.status is AxisStatus.SUPPORTED
    assert assessment.empirical_validity.status is AxisStatus.FAILED
    assert assessment.ddge_consistency.provenance == ("certificates/ddge.json",)


def test_self_report_cannot_support_either_validation_axis() -> None:
    self_report = AxisEvidence(
        passed=True,
        kind=EvidenceKind.SELF_REPORT,
        provenance="claims/model-card.md",
    )

    assessment = assess_capability(
        [],
        ddge_evidence=[self_report],
        empirical_evidence=[self_report],
    )

    assert assessment.ddge_consistency.status is AxisStatus.NOT_ASSESSED
    assert assessment.empirical_validity.status is AxisStatus.NOT_ASSESSED
