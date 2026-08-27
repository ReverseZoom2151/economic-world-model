from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from ewm.capabilities import (
    LEVEL_REQUIREMENTS,
    CapabilityEvidence,
    CapabilityLevel,
    EvidenceKind,
    LevelRequirement,
    ValidatedCapabilityEvidence,
    assess_validated_capability,
    requirement_gate,
)
from ewm.capabilities.readiness import (
    DEFAULT_HAN_L3_L6_PROTOCOL,
    HAN_L3_L6_PROTOCOL_SCHEMA,
    HAN_L3_L6_REPORT_SCHEMA,
    ReadinessClassification,
    han_l3_l6_artifacts,
    load_han_l3_l6_protocol,
    run_han_l3_l6_readiness,
    verify_han_l3_l6_report,
)
from ewm.core import content_digest
from ewm.scenarios.fx.validation import run_han_l1_l2_validation
from scripts.run_conformance import validated_han_l1_l2_evidence

pytestmark = pytest.mark.conformance

HIGHER_LEVELS = (
    CapabilityLevel.L3,
    CapabilityLevel.L4,
    CapabilityLevel.L5,
    CapabilityLevel.L6,
)
HIGHER_REQUIREMENTS = {
    requirement for level in HIGHER_LEVELS for requirement in LEVEL_REQUIREMENTS[level]
}


def test_readiness_protocol_is_versioned_strict_and_derived_from_official_gates() -> None:
    protocol = load_han_l3_l6_protocol()

    assert protocol.schema_version == HAN_L3_L6_PROTOCOL_SCHEMA
    assert protocol.report_schema == HAN_L3_L6_REPORT_SCHEMA
    assert protocol.protocol_version == 1
    assert protocol.protocol_filename == DEFAULT_HAN_L3_L6_PROTOCOL.name
    assert protocol.classification == "evidence_readiness_only"
    assert {item.requirement for item in protocol.requirements} == HIGHER_REQUIREMENTS
    assert len(protocol.protocol_sha256) == 64
    assert len(protocol.source_sha256) == 64
    for declaration in protocol.requirements:
        gate = requirement_gate(declaration.requirement)
        assert declaration.level in HIGHER_LEVELS
        assert declaration.requirement in LEVEL_REQUIREMENTS[declaration.level]
        assert gate.minimum_kind in {
            EvidenceKind.SYNTHETIC_TEST,
            EvidenceKind.CONTROLLED_EXPERIMENT,
            EvidenceKind.EXTERNAL_VALIDATION,
        }
        assert gate.minimum_observations >= 1


def test_deterministic_substrates_emit_one_blocked_result_and_artifact_per_requirement() -> None:
    report = run_han_l3_l6_readiness()
    artifacts = han_l3_l6_artifacts(report)

    assert report.schema_version == HAN_L3_L6_REPORT_SCHEMA
    assert report.classification == "evidence_readiness_only"
    assert {item.requirement for item in report.results} == HIGHER_REQUIREMENTS
    assert len(report.results) == len(artifacts) == 16
    assert all(item.blocked for item in report.results)
    assert all(item.officially_awarded is False for item in report.results)
    assert all(item.blocker for item in report.results)
    assert all(artifact.subject.startswith("readiness:") for artifact in artifacts)
    assert len({artifact.payload_sha256 for artifact in artifacts}) == 16
    assert len(report.report_sha256) == 64
    verify_han_l3_l6_report(report)


def test_local_observations_are_truthfully_classified_below_required_evidence() -> None:
    report = run_han_l3_l6_readiness()
    results = {item.requirement: item for item in report.results}

    assert report.metrics["cognition_fixture_backend_call_count"] == 2
    assert report.metrics["cognition_belief_state_observation_count"] == 2
    assert report.metrics["cognition_memory_and_tool_observation_count"] == 2
    assert report.metrics["evolution_promoted_version_count"] == 2
    assert report.metrics["evolution_persisted_version_count"] == 2
    assert report.metrics["evolution_rollback_count"] == 1
    assert report.metrics["institution_constitutional_check_count"] == 10
    assert report.metrics["institution_accepted_fixture_change_count"] == 2
    assert report.metrics["institution_outcome_observation_count"] == 0
    assert report.metrics["alignment_external_fixture_count"] == 1
    assert report.metrics["alignment_fixture_observation_count"] == 1
    assert report.metrics["alignment_fixture_correction_count"] == 1

    assert (
        results[LevelRequirement.LANGUAGE_MODEL_EXECUTION].classification
        is ReadinessClassification.FIXTURE_ONLY
    )
    assert (
        results[LevelRequirement.COGNITIVE_BEHAVIOR_EVALUATION].classification
        is ReadinessClassification.FIXTURE_ONLY
    )
    assert (
        results[LevelRequirement.EXPLICIT_COGNITIVE_STATE].classification
        is ReadinessClassification.SYNTHETIC_SUBSTRATE
    )
    assert (
        results[LevelRequirement.MEMORY_AND_TOOLS].classification
        is ReadinessClassification.SYNTHETIC_SUBSTRATE
    )
    assert (
        results[LevelRequirement.PERSISTENT_CAPABILITY_IMPROVEMENT].classification
        is ReadinessClassification.FIXTURE_ONLY
    )
    assert (
        results[LevelRequirement.ENDOGENOUS_INSTITUTION_PROPOSAL].classification
        is ReadinessClassification.FIXTURE_ONLY
    )
    assert (
        results[LevelRequirement.INSTITUTIONAL_OUTCOME_EVALUATION].classification
        is ReadinessClassification.NOT_OBSERVED
    )
    assert all(
        results[requirement].classification is ReadinessClassification.FIXTURE_ONLY
        for requirement in LEVEL_REQUIREMENTS[CapabilityLevel.L6]
    )


def test_fake_and_fixture_readiness_artifacts_cannot_cross_capability_boundary() -> None:
    report = run_han_l3_l6_readiness()
    artifacts = han_l3_l6_artifacts(report)
    by_subject = {artifact.subject: artifact for artifact in artifacts}

    for result in report.results:
        gate = requirement_gate(result.requirement)
        with pytest.raises(ValueError, match="capability artifact subject"):
            ValidatedCapabilityEvidence(
                assertion=CapabilityEvidence(
                    requirement=result.requirement,
                    passed=True,
                    kind=gate.minimum_kind,
                    provenance=by_subject[f"readiness:{result.requirement.value}"].provenance,
                    observations=max(result.observations, gate.minimum_observations),
                ),
                artifact=by_subject[f"readiness:{result.requirement.value}"],
            )

    official_l2 = validated_han_l1_l2_evidence(run_han_l1_l2_validation())
    assessment = assess_validated_capability(official_l2)
    assert assessment.achieved_level is CapabilityLevel.L2
    assert HIGHER_REQUIREMENTS.issubset(set(assessment.missing_requirements))


def test_single_alignment_fixture_cannot_meet_repeated_or_external_l6_gates() -> None:
    report = run_han_l3_l6_readiness()
    results = {item.requirement: item for item in report.results}

    for requirement in LEVEL_REQUIREMENTS[CapabilityLevel.L6]:
        result = results[requirement]
        assert result.classification is ReadinessClassification.FIXTURE_ONLY
        assert result.blocked
        assert result.officially_awarded is False
        assert result.required_evidence_kind is EvidenceKind.EXTERNAL_VALIDATION
    assert results[LevelRequirement.REPEATED_OUT_OF_SAMPLE_ALIGNMENT].observations == 1
    assert results[LevelRequirement.REPEATED_OUT_OF_SAMPLE_ALIGNMENT].required_observations == 2


def test_self_resealed_observation_tampering_is_rejected_by_deterministic_rerun() -> None:
    report = run_han_l3_l6_readiness()
    first = report.results[0]
    tampered = replace(
        report,
        results=(replace(first, observed_value=first.observed_value + 1.0), *report.results[1:]),
        report_sha256="",
    )
    resealed = replace(
        tampered,
        report_sha256=content_digest(tampered.as_dict(include_report_hash=False)),
    )

    with pytest.raises(ValueError, match="deterministic substrate observations"):
        verify_han_l3_l6_report(resealed)


def test_source_identity_tampering_is_rejected_even_when_report_is_resealed() -> None:
    report = run_han_l3_l6_readiness()
    tampered = replace(report, source_sha256="0" * 64, report_sha256="")
    resealed = replace(
        tampered,
        report_sha256=content_digest(tampered.as_dict(include_report_hash=False)),
    )

    with pytest.raises(ValueError, match="source SHA-256"):
        verify_han_l3_l6_report(resealed)


@pytest.mark.parametrize(
    "mutation",
    (
        lambda text: text.replace("seed = 73", "seed = 73\nunknown = true", 1),
        lambda text: text.replace('classification = "evidence_readiness_only"\n', "", 1),
        lambda text: text.replace(
            'probe = "cognition"',
            'probe = "cognition"\nunknown = true',
            1,
        ),
        lambda text: text.replace('level = "L3"\n', "", 1),
        lambda text: text.replace('operator = "eq"', 'operator = "eq"\nunknown = true', 1),
        lambda text: text.replace("value = 2\n", "", 1),
    ),
)
def test_protocol_rejects_unknown_or_missing_keys_at_every_level(
    mutation: Callable[[str], str],
    tmp_path: Path,
) -> None:
    original = DEFAULT_HAN_L3_L6_PROTOCOL.read_text(encoding="utf-8")
    changed = mutation(original)
    assert changed != original
    path = tmp_path / DEFAULT_HAN_L3_L6_PROTOCOL.name
    path.write_text(changed, encoding="utf-8")

    with pytest.raises(ValueError, match="keys do not match"):
        load_han_l3_l6_protocol(path)


def test_protocol_drift_from_levels_policy_or_evidence_class_is_rejected(
    tmp_path: Path,
) -> None:
    original = DEFAULT_HAN_L3_L6_PROTOCOL.read_text(encoding="utf-8")
    wrong_level = original.replace(
        'requirement = "language_model_execution"\nlevel = "L3"',
        'requirement = "language_model_execution"\nlevel = "L4"',
        1,
    )
    path = tmp_path / DEFAULT_HAN_L3_L6_PROTOCOL.name
    path.write_text(wrong_level, encoding="utf-8")

    with pytest.raises(ValueError, match="levels policy"):
        load_han_l3_l6_protocol(path)

    fake_controlled = original.replace(
        'classification = "fixture_only"',
        'classification = "controlled_validation"',
        1,
    )
    path.write_text(fake_controlled, encoding="utf-8")
    with pytest.raises(ValueError, match="local readiness classification"):
        load_han_l3_l6_protocol(path)


def test_impossible_local_criterion_is_reported_and_never_awarded(tmp_path: Path) -> None:
    original = DEFAULT_HAN_L3_L6_PROTOCOL.read_text(encoding="utf-8")
    counterexample = original.replace(
        'metric = "cognition_fixture_backend_call_count"\noperator = "eq"\nvalue = 2',
        'metric = "cognition_fixture_backend_call_count"\noperator = "eq"\nvalue = 999',
        1,
    )
    assert counterexample != original
    path = tmp_path / DEFAULT_HAN_L3_L6_PROTOCOL.name
    path.write_text(counterexample, encoding="utf-8")

    report = run_han_l3_l6_readiness(protocol_path=path)
    result = next(
        item
        for item in report.results
        if item.requirement is LevelRequirement.LANGUAGE_MODEL_EXECUTION
    )
    artifact = next(
        item
        for item in han_l3_l6_artifacts(report, protocol_path=path)
        if item.subject == "readiness:language_model_execution"
    )

    assert result.local_criterion_passed is False
    assert result.officially_awarded is False
    assert artifact.status.value == "fail"
