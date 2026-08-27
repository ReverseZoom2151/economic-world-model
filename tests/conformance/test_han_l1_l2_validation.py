from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from ewm.scenarios.fx.validation import (
    DEFAULT_HAN_L1_L2_PROTOCOL,
    HAN_L1_L2_PROTOCOL_SCHEMA,
    HAN_L1_L2_REPORT_SCHEMA,
    load_han_l1_l2_protocol,
    run_han_l1_l2_validation,
    validated_han_l1_l2_evidence,
    verify_han_l1_l2_report,
)

from ewm.capabilities import CapabilityLevel, LevelRequirement, assess_validated_capability
from ewm.core import verify_event_chain
from ewm.core.events import Event

pytestmark = pytest.mark.conformance

L1_L2_REQUIREMENTS = {
    LevelRequirement.AGENT_WORLD_EXECUTION,
    LevelRequirement.ENDOGENOUS_ENVIRONMENT,
    LevelRequirement.ECONOMIC_INVARIANTS,
    LevelRequirement.ADAPTIVE_AGENT_STATE,
    LevelRequirement.LONGITUDINAL_PERSISTENCE,
}


def _event(record: dict[str, object]) -> Event:
    payload = record["payload"]
    assert isinstance(payload, dict)
    return Event(
        sequence=int(record["sequence"]),
        kind=str(record["kind"]),
        payload=payload,
        schema_version=str(record["schema_version"]),
        state_version=(
            None if record["state_version"] is None else int(record["state_version"])
        ),
        previous_hash=str(record["previous_hash"]),
        event_hash=str(record["event_hash"]),
    )


def test_versioned_protocol_declares_synthetic_scope_metrics_and_sources() -> None:
    protocol = load_han_l1_l2_protocol()

    assert protocol.schema_version == HAN_L1_L2_PROTOCOL_SCHEMA
    assert protocol.report_schema == HAN_L1_L2_REPORT_SCHEMA
    assert protocol.classification == "synthetic_systems_conformance"
    assert protocol.excluded_claims == (
        "empirical_validation",
        "prospective_behavioral_study",
    )
    assert protocol.seeds == (17, 42)
    assert protocol.periods >= 2
    assert {item.requirement for item in protocol.requirements} == L1_L2_REQUIREMENTS
    assert all(item.criteria for item in protocol.requirements)
    assert all(item.minimum_observations >= 1 for item in protocol.requirements)
    assert len(protocol.protocol_sha256) == 64
    assert len(protocol.source_sha256) == 64
    assert DEFAULT_HAN_L1_L2_PROTOCOL.name.endswith("-v1.toml")


def test_compiled_fx_validation_produces_separate_observed_requirement_evidence() -> None:
    report = run_han_l1_l2_validation()

    assert report.schema_version == HAN_L1_L2_REPORT_SCHEMA
    assert report.classification == "synthetic_systems_conformance"
    assert report.seeds == (17, 42)
    assert len(report.report_sha256) == 64
    assert {item.requirement for item in report.requirements} == L1_L2_REQUIREMENTS
    assert all(item.passed for item in report.requirements)
    assert all(item.observations >= 1 for item in report.requirements)

    for run in report.runs:
        assert len(run.state_observations) >= 2
        assert tuple(event["kind"] for event in run.events) == (
            "reset",
            "run_agents",
            "step",
            "run_agents",
            "step",
            "run_agents",
            "step",
            "run_agents",
            "step",
            "run_agents",
            "step",
            "run_agents",
            "step",
        )
        events = tuple(_event(dict(item)) for item in run.events)
        assert verify_event_chain(events) == run.event_chain_hash
        assert all(len(str(item["event_hash"])) == 64 for item in run.events)
        steps = tuple(item for item in run.events if item["kind"] == "step")
        assert all("before_state_digest" in item["payload"] for item in steps)
        assert all("after_state_digest" in item["payload"] for item in steps)

    verify_han_l1_l2_report(report)


def test_each_requirement_gets_its_own_content_addressed_artifact() -> None:
    report = run_han_l1_l2_validation()
    evidence = validated_han_l1_l2_evidence(report)
    assessment = assess_validated_capability(evidence)

    assert len(evidence) == len(L1_L2_REQUIREMENTS)
    assert {item.assertion.requirement for item in evidence} == L1_L2_REQUIREMENTS
    assert len({item.artifact.payload_sha256 for item in evidence}) == len(evidence)
    assert all(item.artifact.status.value == "pass" for item in evidence)
    assert assessment.achieved_level is CapabilityLevel.L2
    assert L1_L2_REQUIREMENTS.issubset(set(assessment.satisfied_requirements))
    assert LevelRequirement.LANGUAGE_MODEL_EXECUTION in assessment.missing_requirements
    assert LevelRequirement.EXTERNAL_DATA_CONTRACT in assessment.missing_requirements


def test_counterexample_fails_only_its_requirement_and_cannot_award_l1(
    tmp_path: Path,
) -> None:
    original = DEFAULT_HAN_L1_L2_PROTOCOL.read_text(encoding="utf-8")
    counterexample = original.replace(
        'metric = "max_cash_residual"\noperator = "lte"\nvalue = 1e-10',
        'metric = "max_cash_residual"\noperator = "lte"\nvalue = -1.0',
        1,
    )
    assert counterexample != original
    path = tmp_path / DEFAULT_HAN_L1_L2_PROTOCOL.name
    path.write_text(counterexample, encoding="utf-8")

    report = run_han_l1_l2_validation(protocol_path=path)
    by_requirement = {item.requirement: item for item in report.requirements}
    evidence = validated_han_l1_l2_evidence(report, protocol_path=path)

    assert by_requirement[LevelRequirement.ECONOMIC_INVARIANTS].passed is False
    assert all(
        item.passed
        for requirement, item in by_requirement.items()
        if requirement is not LevelRequirement.ECONOMIC_INVARIANTS
    )
    assert assess_validated_capability(evidence).achieved_level is CapabilityLevel.L0


def test_report_tampering_is_rejected_before_artifacts_are_constructed() -> None:
    report = run_han_l1_l2_validation()
    tampered = replace(
        report,
        metrics={**report.metrics, "max_cash_residual": 1.0},
    )

    with pytest.raises(ValueError, match="report SHA-256"):
        verify_han_l1_l2_report(tampered)
    with pytest.raises(ValueError, match="report SHA-256"):
        validated_han_l1_l2_evidence(tampered)
