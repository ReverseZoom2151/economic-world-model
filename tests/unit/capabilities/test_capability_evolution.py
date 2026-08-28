"""Evidence-bound unit contracts for capability evolution."""

from __future__ import annotations

import hashlib

import pytest

from ewm.capabilities import (
    CapabilityKind,
    CapabilityManifest,
    EvolutionProposal,
    EvolutionRegistry,
    GateEvidence,
    PromotionPolicy,
)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _manifest(version: int, label: str) -> CapabilityManifest:
    return CapabilityManifest(
        capability_id="dealer.inventory-strategy",
        kind=CapabilityKind.STRATEGY,
        version=version,
        content_hash=_digest(label),
        description=f"inventory strategy {label}",
        artifact_reference=f"artifacts/{label}.json",
        metadata={"author": "offline-test"},
    )


def _evidence(*, safety_passed: bool = True) -> tuple[GateEvidence, ...]:
    return (
        GateEvidence(
            gate="sandbox",
            passed=True,
            evaluator="deterministic-replay",
            score=0.92,
            threshold=0.80,
            evidence_reference="runs/sandbox.json",
        ),
        GateEvidence(
            gate="safety",
            passed=safety_passed,
            evaluator="constraint-audit",
            score=1.0 if safety_passed else 0.5,
            threshold=1.0,
            evidence_reference="runs/safety.json",
        ),
    )


def _proposal(
    version: int,
    label: str,
    *,
    parent_version: int | None,
    safety_passed: bool = True,
) -> EvolutionProposal:
    return EvolutionProposal(
        proposal_id=f"proposal-{label}",
        candidate=_manifest(version, label),
        parent_version=parent_version,
        evidence=_evidence(safety_passed=safety_passed),
    )


def test_failed_gate_leaves_active_capability_unchanged() -> None:
    registry = EvolutionRegistry(PromotionPolicy())
    accepted = registry.evaluate_and_promote(
        _proposal(1, "v1", parent_version=None)
    )
    before = registry.active("dealer.inventory-strategy")

    rejected = registry.evaluate_and_promote(
        _proposal(2, "unsafe-v2", parent_version=1, safety_passed=False)
    )

    assert accepted.promoted
    assert not rejected.promoted
    assert rejected.reasons == ("required gate 'safety' did not pass",)
    assert rejected.before == before
    assert rejected.after == before
    assert registry.active("dealer.inventory-strategy") == before
    assert registry.approved_versions("dealer.inventory-strategy") == (1,)


def test_promotion_requires_sequential_version_and_current_parent() -> None:
    registry = EvolutionRegistry(PromotionPolicy())
    registry.evaluate_and_promote(_proposal(1, "v1", parent_version=None))

    stale = registry.evaluate_and_promote(
        _proposal(3, "v3", parent_version=7)
    )
    promoted = registry.evaluate_and_promote(
        _proposal(2, "v2", parent_version=1)
    )

    assert not stale.promoted
    assert "candidate version must be 2" in stale.reasons
    assert "parent_version must identify active version 1" in stale.reasons
    assert promoted.promoted
    assert promoted.before == _manifest(1, "v1")
    assert promoted.after == _manifest(2, "v2")
    assert registry.approved_versions("dealer.inventory-strategy") == (1, 2)


def test_rollback_activates_only_an_approved_version() -> None:
    registry = EvolutionRegistry(PromotionPolicy())
    registry.evaluate_and_promote(_proposal(1, "v1", parent_version=None))
    registry.evaluate_and_promote(_proposal(2, "v2", parent_version=1))

    report = registry.rollback("dealer.inventory-strategy", target_version=1)

    assert report.before == _manifest(2, "v2")
    assert report.after == _manifest(1, "v1")
    assert registry.active("dealer.inventory-strategy") == _manifest(1, "v1")
    with pytest.raises(ValueError, match="not an approved version"):
        registry.rollback("dealer.inventory-strategy", target_version=9)


def test_approved_manifests_and_evidence_round_trip_without_executable_code() -> None:
    policy = PromotionPolicy()
    registry = EvolutionRegistry(policy)
    registry.evaluate_and_promote(_proposal(1, "v1", parent_version=None))
    registry.evaluate_and_promote(
        _proposal(2, "unsafe-v2", parent_version=1, safety_passed=False)
    )

    payload = registry.to_json()
    restored = EvolutionRegistry.from_json(payload, policy=policy)

    assert restored.active("dealer.inventory-strategy") == _manifest(1, "v1")
    assert restored.approved_versions("dealer.inventory-strategy") == (1,)
    assert restored.approval_evidence("dealer.inventory-strategy", 1) == _evidence()
    assert "unsafe-v2" not in payload
    assert "callable" not in payload
    assert restored.to_json() == payload


@pytest.mark.parametrize(
    "kind",
    [
        CapabilityKind.STRATEGY,
        CapabilityKind.SKILL,
        CapabilityKind.TOOL,
        CapabilityKind.MEMORY_ROUTINE,
        CapabilityKind.POLICY_ROUTINE,
    ],
)
def test_policy_accepts_each_declared_l4_capability_kind(kind: CapabilityKind) -> None:
    manifest = CapabilityManifest(
        capability_id=f"agent.{kind.value}",
        kind=kind,
        version=1,
        content_hash=_digest(kind.value),
        description=f"candidate {kind.value}",
    )
    proposal = EvolutionProposal(
        proposal_id=f"proposal-{kind.value}",
        candidate=manifest,
        parent_version=None,
        evidence=_evidence(),
    )

    report = EvolutionRegistry(PromotionPolicy()).evaluate_and_promote(proposal)

    assert report.promoted
    assert report.after == manifest


def test_manifest_rejects_non_sha256_content_identity() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        CapabilityManifest(
            capability_id="agent.strategy",
            kind=CapabilityKind.STRATEGY,
            version=1,
            content_hash="not-a-digest",
            description="invalid candidate",
        )
