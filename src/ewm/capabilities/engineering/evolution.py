"""Evidence-gated, artifact-neutral persistent capability evolution."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from typing import Any, cast

from ewm.core.records import freeze_value

EVOLUTION_SCHEMA_VERSION = "ewm.capability-registry.v1"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class CapabilityKind(StrEnum):
    """Persistent agent capability classes identified in Han et al. L4."""

    STRATEGY = "strategy"
    SKILL = "skill"
    TOOL = "tool"
    MEMORY_ROUTINE = "memory_routine"
    POLICY_ROUTINE = "policy_routine"


@dataclass(frozen=True, slots=True)
class CapabilityManifest:
    """Identity and provenance for an artifact without embedding executable code."""

    capability_id: str
    kind: CapabilityKind
    version: int
    content_hash: str
    description: str
    artifact_reference: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.capability_id:
            raise ValueError("capability_id must not be empty")
        if self.version < 1:
            raise ValueError("capability version must be positive")
        if _SHA256_PATTERN.fullmatch(self.content_hash) is None:
            raise ValueError("content_hash must be a lowercase SHA-256 digest")
        if not self.description:
            raise ValueError("capability description must not be empty")
        if self.artifact_reference == "":
            raise ValueError("artifact_reference must not be empty")
        if any(not key for key in self.metadata):
            raise ValueError("capability metadata keys must not be empty")
        object.__setattr__(self, "metadata", freeze_value(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class GateEvidence:
    """One externally produced evaluation or safety-gate result."""

    gate: str
    passed: bool
    evaluator: str
    evidence_reference: str
    score: float | None = None
    threshold: float | None = None

    def __post_init__(self) -> None:
        if not self.gate or not self.evaluator or not self.evidence_reference:
            raise ValueError("gate, evaluator, and evidence_reference must not be empty")
        if (self.score is None) != (self.threshold is None):
            raise ValueError("score and threshold must either both be set or both be absent")
        if self.score is not None and self.threshold is not None:
            if not isfinite(self.score) or not isfinite(self.threshold):
                raise ValueError("gate score and threshold must be finite")
            if self.passed != (self.score >= self.threshold):
                raise ValueError("gate outcome must agree with score and threshold")


@dataclass(frozen=True, slots=True)
class EvolutionProposal:
    """A candidate manifest, its active parent, and declared evaluation evidence."""

    proposal_id: str
    candidate: CapabilityManifest
    parent_version: int | None
    evidence: tuple[GateEvidence, ...]

    def __post_init__(self) -> None:
        if not self.proposal_id:
            raise ValueError("proposal_id must not be empty")
        if self.parent_version is not None and self.parent_version < 1:
            raise ValueError("parent_version must be positive when present")
        object.__setattr__(self, "evidence", tuple(self.evidence))


@dataclass(frozen=True, slots=True)
class PromotionPolicy:
    """Allow-listed capability classes and mandatory promotion gates."""

    required_gates: tuple[str, ...] = ("sandbox", "safety")
    allowed_kinds: tuple[CapabilityKind, ...] = (
        CapabilityKind.STRATEGY,
        CapabilityKind.SKILL,
        CapabilityKind.TOOL,
        CapabilityKind.MEMORY_ROUTINE,
        CapabilityKind.POLICY_ROUTINE,
    )

    def __post_init__(self) -> None:
        if not self.required_gates or any(not gate for gate in self.required_gates):
            raise ValueError("required_gates must contain nonempty names")
        if len(self.required_gates) != len(set(self.required_gates)):
            raise ValueError("required_gates must be unique")
        if not {"sandbox", "safety"}.issubset(self.required_gates):
            raise ValueError("promotion requires sandbox and safety gates")
        if not self.allowed_kinds:
            raise ValueError("allowed_kinds must not be empty")
        if len(self.allowed_kinds) != len(set(self.allowed_kinds)):
            raise ValueError("allowed_kinds must be unique")
        object.__setattr__(self, "required_gates", tuple(self.required_gates))
        object.__setattr__(self, "allowed_kinds", tuple(self.allowed_kinds))


@dataclass(frozen=True, slots=True)
class PromotionReport:
    """Atomic outcome of evaluating one capability proposal."""

    proposal_id: str
    promoted: bool
    reasons: tuple[str, ...]
    before: CapabilityManifest | None
    after: CapabilityManifest | None


@dataclass(frozen=True, slots=True)
class RollbackReport:
    """Activation change between two already approved manifests."""

    capability_id: str
    before: CapabilityManifest
    after: CapabilityManifest


@dataclass(frozen=True, slots=True)
class _Approval:
    proposal_id: str
    manifest: CapabilityManifest
    evidence: tuple[GateEvidence, ...]


class EvolutionRegistry:
    """Promote, persist, and roll back manifests while never executing artifacts."""

    def __init__(self, policy: PromotionPolicy) -> None:
        self._policy = policy
        self._approved: dict[str, list[_Approval]] = {}
        self._active_versions: dict[str, int] = {}
        self._approved_proposal_ids: set[str] = set()

    @property
    def policy(self) -> PromotionPolicy:
        return self._policy

    def active(self, capability_id: str) -> CapabilityManifest | None:
        """Return the active manifest, if the capability has an approved version."""

        active_version = self._active_versions.get(capability_id)
        if active_version is None:
            return None
        return self._approval(capability_id, active_version).manifest

    def approved_versions(self, capability_id: str) -> tuple[int, ...]:
        """Return all approved versions in promotion order."""

        return tuple(
            approval.manifest.version
            for approval in self._approved.get(capability_id, ())
        )

    def approval_evidence(
        self,
        capability_id: str,
        version: int,
    ) -> tuple[GateEvidence, ...]:
        """Return the immutable gate evidence used to approve a version."""

        return self._approval(capability_id, version).evidence

    def evaluate_and_promote(self, proposal: EvolutionProposal) -> PromotionReport:
        """Validate every gate before atomically changing the active manifest."""

        candidate = proposal.candidate
        before = self.active(candidate.capability_id)
        approvals = self._approved.get(candidate.capability_id, ())
        expected_version = max(
            (approval.manifest.version for approval in approvals),
            default=0,
        ) + 1
        reasons: list[str] = []
        if proposal.proposal_id in self._approved_proposal_ids:
            reasons.append("proposal_id has already been approved")
        if candidate.version != expected_version:
            reasons.append(f"candidate version must be {expected_version}")
        expected_parent = before.version if before is not None else None
        if proposal.parent_version != expected_parent:
            if expected_parent is None:
                reasons.append("parent_version must be absent for an initial capability")
            else:
                reasons.append(
                    f"parent_version must identify active version {expected_parent}"
                )
        if before is not None and candidate.kind != before.kind:
            reasons.append("candidate kind must match the active capability kind")
        if candidate.kind not in self._policy.allowed_kinds:
            reasons.append(f"capability kind {candidate.kind.value!r} is not allowed")

        evidence_by_gate: dict[str, GateEvidence] = {}
        for item in proposal.evidence:
            if item.gate in evidence_by_gate:
                reasons.append(f"gate {item.gate!r} has duplicate evidence")
            else:
                evidence_by_gate[item.gate] = item
        for gate in self._policy.required_gates:
            evidence = evidence_by_gate.get(gate)
            if evidence is None:
                reasons.append(f"required gate {gate!r} has no evidence")
            elif not evidence.passed:
                reasons.append(f"required gate {gate!r} did not pass")

        if reasons:
            return PromotionReport(
                proposal_id=proposal.proposal_id,
                promoted=False,
                reasons=tuple(reasons),
                before=before,
                after=before,
            )

        approval = _Approval(
            proposal_id=proposal.proposal_id,
            manifest=candidate,
            evidence=proposal.evidence,
        )
        self._approved.setdefault(candidate.capability_id, []).append(approval)
        self._active_versions[candidate.capability_id] = candidate.version
        self._approved_proposal_ids.add(proposal.proposal_id)
        return PromotionReport(
            proposal_id=proposal.proposal_id,
            promoted=True,
            reasons=(),
            before=before,
            after=candidate,
        )

    def rollback(self, capability_id: str, *, target_version: int) -> RollbackReport:
        """Activate a previously approved manifest without deleting audit history."""

        before = self.active(capability_id)
        if before is None:
            raise ValueError(f"capability {capability_id!r} has no active version")
        try:
            after = self._approval(capability_id, target_version).manifest
        except KeyError as error:
            raise ValueError(
                f"version {target_version} is not an approved version of {capability_id!r}"
            ) from error
        self._active_versions[capability_id] = target_version
        return RollbackReport(capability_id=capability_id, before=before, after=after)

    def to_json(self) -> str:
        """Serialize approved manifests, their evidence, and active pointers only."""

        capabilities: list[dict[str, Any]] = []
        for capability_id in sorted(self._approved):
            approved = [
                {
                    "proposal_id": approval.proposal_id,
                    "manifest": _manifest_to_data(approval.manifest),
                    "evidence": [
                        _evidence_to_data(evidence) for evidence in approval.evidence
                    ],
                }
                for approval in self._approved[capability_id]
            ]
            capabilities.append(
                {
                    "capability_id": capability_id,
                    "active_version": self._active_versions[capability_id],
                    "approved": approved,
                }
            )
        data = {
            "schema_version": EVOLUTION_SCHEMA_VERSION,
            "capabilities": capabilities,
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(
        cls,
        payload: str,
        *,
        policy: PromotionPolicy,
    ) -> EvolutionRegistry:
        """Restore a registry while revalidating all serialized records."""

        data = cast(dict[str, Any], json.loads(payload))
        if data.get("schema_version") != EVOLUTION_SCHEMA_VERSION:
            raise ValueError("unsupported capability registry schema")
        registry = cls(policy)
        capabilities = cast(list[dict[str, Any]], data.get("capabilities"))
        for capability in capabilities:
            capability_id = cast(str, capability["capability_id"])
            approved = cast(list[dict[str, Any]], capability["approved"])
            for record in approved:
                manifest = _manifest_from_data(
                    cast(dict[str, Any], record["manifest"])
                )
                if manifest.capability_id != capability_id:
                    raise ValueError("serialized capability_id does not match manifest")
                evidence = tuple(
                    _evidence_from_data(item)
                    for item in cast(list[dict[str, Any]], record["evidence"])
                )
                proposal_id = cast(str, record["proposal_id"])
                if not proposal_id or proposal_id in registry._approved_proposal_ids:
                    raise ValueError("serialized proposal_id must be nonempty and unique")
                registry._approved.setdefault(capability_id, []).append(
                    _Approval(proposal_id, manifest, evidence)
                )
                registry._approved_proposal_ids.add(proposal_id)
            versions = registry.approved_versions(capability_id)
            if versions != tuple(range(1, len(versions) + 1)):
                raise ValueError("serialized approved versions must be sequential")
            active_version = cast(int, capability["active_version"])
            if active_version not in versions:
                raise ValueError("serialized active version must be approved")
            registry._active_versions[capability_id] = active_version
        return registry

    def _approval(self, capability_id: str, version: int) -> _Approval:
        for approval in self._approved.get(capability_id, ()):
            if approval.manifest.version == version:
                return approval
        raise KeyError((capability_id, version))


def _manifest_to_data(manifest: CapabilityManifest) -> dict[str, Any]:
    return {
        "capability_id": manifest.capability_id,
        "kind": manifest.kind.value,
        "version": manifest.version,
        "content_hash": manifest.content_hash,
        "description": manifest.description,
        "artifact_reference": manifest.artifact_reference,
        "metadata": dict(manifest.metadata),
    }


def _manifest_from_data(data: dict[str, Any]) -> CapabilityManifest:
    return CapabilityManifest(
        capability_id=cast(str, data["capability_id"]),
        kind=CapabilityKind(cast(str, data["kind"])),
        version=cast(int, data["version"]),
        content_hash=cast(str, data["content_hash"]),
        description=cast(str, data["description"]),
        artifact_reference=cast(str | None, data["artifact_reference"]),
        metadata=cast(dict[str, str], data["metadata"]),
    )


def _evidence_to_data(evidence: GateEvidence) -> dict[str, Any]:
    return {
        "gate": evidence.gate,
        "passed": evidence.passed,
        "evaluator": evidence.evaluator,
        "evidence_reference": evidence.evidence_reference,
        "score": evidence.score,
        "threshold": evidence.threshold,
    }


def _evidence_from_data(data: dict[str, Any]) -> GateEvidence:
    return GateEvidence(
        gate=cast(str, data["gate"]),
        passed=cast(bool, data["passed"]),
        evaluator=cast(str, data["evaluator"]),
        evidence_reference=cast(str, data["evidence_reference"]),
        score=cast(float | None, data["score"]),
        threshold=cast(float | None, data["threshold"]),
    )
