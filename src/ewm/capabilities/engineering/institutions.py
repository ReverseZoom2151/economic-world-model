"""Governed, versioned institutional evolution with constitutional checks."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from ewm.core.protocols import InstitutionChangeProposal
from ewm.core.records import freeze_value

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class InstitutionKind(StrEnum):
    """Institution classes that may change at Han et al. L5."""

    RULE = "rule"
    MECHANISM = "mechanism"
    CONTRACT = "contract"
    POLICY = "policy"
    INFORMATION = "information"
    GOVERNANCE = "governance"
    CONSTRAINT = "constraint"


@dataclass(frozen=True, slots=True)
class InstitutionManifest:
    """Content-addressed declaration of one institutional version."""

    institution_id: str
    kind: InstitutionKind
    version: int
    content_hash: str
    description: str
    artifact_reference: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.institution_id:
            raise ValueError("institution_id must not be empty")
        if self.version < 1:
            raise ValueError("institution version must be positive")
        if _SHA256_PATTERN.fullmatch(self.content_hash) is None:
            raise ValueError("content_hash must be a lowercase SHA-256 digest")
        if not self.description:
            raise ValueError("institution description must not be empty")
        if self.artifact_reference == "":
            raise ValueError("artifact_reference must not be empty")
        if any(not key for key in self.metadata):
            raise ValueError("institution metadata keys must not be empty")
        object.__setattr__(self, "metadata", freeze_value(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class InstitutionProposal:
    """Change proposed by an agent or a diagnostic under a named authority."""

    proposal_id: str
    proposer_id: str
    proposer_type: str
    authority: str
    parent_version: int | None
    candidate: InstitutionManifest

    def __post_init__(self) -> None:
        if not self.proposal_id or not self.proposer_id or not self.authority:
            raise ValueError("proposal, proposer, and authority identifiers must not be empty")
        if self.proposer_type not in {"agent", "diagnostic"}:
            raise ValueError("proposer_type must be 'agent' or 'diagnostic'")
        if self.parent_version is not None and self.parent_version < 1:
            raise ValueError("parent_version must be positive when present")


@dataclass(frozen=True, slots=True)
class InstitutionCheck:
    """Trusted validator evidence for one constitutional condition."""

    check: str
    passed: bool
    evaluator: str
    evidence_reference: str
    detail: str | None = None

    def __post_init__(self) -> None:
        if not self.check or not self.evaluator or not self.evidence_reference:
            raise ValueError("check, evaluator, and evidence_reference must not be empty")
        if self.detail == "":
            raise ValueError("check detail must not be empty")


@dataclass(frozen=True, slots=True)
class InstitutionPolicy:
    """Constitutional checks and authorities for each mutable institution class."""

    authorities: Mapping[InstitutionKind, tuple[str, ...]]
    required_checks: tuple[str, ...] = (
        "allow_list",
        "feasibility",
        "accounting",
        "safety",
        "acceptance",
    )

    def __post_init__(self) -> None:
        normalized: dict[InstitutionKind, tuple[str, ...]] = {}
        for raw_kind, raw_authorities in self.authorities.items():
            kind = InstitutionKind(raw_kind)
            authorities = tuple(raw_authorities)
            if not authorities or any(not authority for authority in authorities):
                raise ValueError(f"authorities for {kind.value!r} must not be empty")
            if len(authorities) != len(set(authorities)):
                raise ValueError(f"authorities for {kind.value!r} must be unique")
            normalized[kind] = authorities
        if not normalized:
            raise ValueError("institution policy must allow at least one kind")
        if len(self.required_checks) != len(set(self.required_checks)) or any(
            not check for check in self.required_checks
        ):
            raise ValueError("required_checks must be nonempty and unique")
        mandatory = {"allow_list", "feasibility", "accounting", "safety", "acceptance"}
        if not mandatory.issubset(self.required_checks):
            raise ValueError("institution policy omits a mandatory constitutional check")
        object.__setattr__(self, "authorities", freeze_value(normalized))
        object.__setattr__(self, "required_checks", tuple(self.required_checks))


@dataclass(frozen=True, slots=True)
class InstitutionSnapshot:
    """Immutable institutional regime state."""

    regime_version: int
    active: Mapping[str, InstitutionManifest]

    def __post_init__(self) -> None:
        if self.regime_version < 0:
            raise ValueError("regime_version must be non-negative")
        object.__setattr__(self, "active", freeze_value(dict(self.active)))


@dataclass(frozen=True, slots=True)
class InstitutionTransitionReport:
    """Auditable outcome of a proposed promotion or rollback."""

    proposal_id: str
    institution_id: str
    accepted: bool
    reasons: tuple[str, ...]
    checks: tuple[InstitutionCheck, ...]
    before_regime_version: int
    after_regime_version: int
    before_institution_version: int | None
    after_institution_version: int | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "reasons", tuple(self.reasons))
        object.__setattr__(self, "checks", tuple(self.checks))


InstitutionValidator = Callable[
    [InstitutionProposal, InstitutionSnapshot],
    InstitutionCheck,
]


class GovernedInstitutions:
    """Apply institutional changes only after authority and validator checks pass."""

    def __init__(
        self,
        *,
        policy: InstitutionPolicy,
        validators: Mapping[str, InstitutionValidator],
    ) -> None:
        if set(validators) != set(policy.required_checks):
            raise ValueError("validator registry must exactly match required checks")
        self._policy = policy
        self._validators = dict(validators)
        self._approved: dict[str, list[InstitutionManifest]] = {}
        self._active: dict[str, InstitutionManifest] = {}
        self._approved_proposal_ids: set[str] = set()
        self._version = 0

    @property
    def version(self) -> int:
        return self._version

    @property
    def snapshot(self) -> InstitutionSnapshot:
        return InstitutionSnapshot(regime_version=self._version, active=self._active)

    def active(self, institution_id: str) -> InstitutionManifest | None:
        return self._active.get(institution_id)

    def approved_versions(self, institution_id: str) -> tuple[int, ...]:
        return tuple(
            manifest.version for manifest in self._approved.get(institution_id, ())
        )

    def evolve(
        self,
        proposal: InstitutionChangeProposal,
    ) -> InstitutionTransitionReport:
        """Evaluate trusted checks, then promote the complete change atomically."""

        if not isinstance(proposal, InstitutionProposal):
            raise TypeError("governed institutions require an InstitutionProposal")
        candidate = proposal.candidate
        before = self._active.get(candidate.institution_id)
        before_version = before.version if before is not None else None
        prior = self._approved.get(candidate.institution_id, ())
        expected_version = max((item.version for item in prior), default=0) + 1
        reasons: list[str] = []
        if proposal.proposal_id in self._approved_proposal_ids:
            reasons.append("proposal_id has already been approved")
        if candidate.kind not in self._policy.authorities:
            reasons.append(f"institution kind {candidate.kind.value!r} is not allow-listed")
        else:
            allowed_authorities = self._policy.authorities[candidate.kind]
            if proposal.authority not in allowed_authorities:
                reasons.append(
                    f"authority {proposal.authority!r} cannot change institution kind "
                    f"{candidate.kind.value!r}"
                )
        if candidate.version != expected_version:
            reasons.append(f"candidate version must be {expected_version}")
        if proposal.parent_version != before_version:
            if before_version is None:
                reasons.append("parent_version must be absent for an initial institution")
            else:
                reasons.append(
                    f"parent_version must identify active version {before_version}"
                )
        if before is not None and candidate.kind != before.kind:
            reasons.append("candidate kind must match the active institution kind")

        checks: tuple[InstitutionCheck, ...] = ()
        if not reasons:
            snapshot = self.snapshot
            evaluated: list[InstitutionCheck] = []
            for name in self._policy.required_checks:
                result = self._validators[name](proposal, snapshot)
                if result.check != name:
                    raise ValueError(
                        f"validator {name!r} returned check {result.check!r}"
                    )
                evaluated.append(result)
                if not result.passed:
                    reasons.append(f"required check {name!r} did not pass")
            checks = tuple(evaluated)

        if reasons:
            return InstitutionTransitionReport(
                proposal_id=proposal.proposal_id,
                institution_id=candidate.institution_id,
                accepted=False,
                reasons=tuple(reasons),
                checks=checks,
                before_regime_version=self._version,
                after_regime_version=self._version,
                before_institution_version=before_version,
                after_institution_version=before_version,
            )

        before_regime_version = self._version
        self._approved.setdefault(candidate.institution_id, []).append(candidate)
        self._active[candidate.institution_id] = candidate
        self._approved_proposal_ids.add(proposal.proposal_id)
        self._version += 1
        return InstitutionTransitionReport(
            proposal_id=proposal.proposal_id,
            institution_id=candidate.institution_id,
            accepted=True,
            reasons=(),
            checks=checks,
            before_regime_version=before_regime_version,
            after_regime_version=self._version,
            before_institution_version=before_version,
            after_institution_version=candidate.version,
        )

    def rollback(
        self,
        institution_id: str,
        *,
        target_version: int,
        authority: str,
    ) -> InstitutionTransitionReport:
        """Activate a prior approved version under the same authority boundary."""

        before = self._active.get(institution_id)
        if before is None:
            raise ValueError(f"institution {institution_id!r} has no active version")
        if authority not in self._policy.authorities[before.kind]:
            raise PermissionError(
                f"authority {authority!r} cannot roll back {before.kind.value!r}"
            )
        target = next(
            (
                manifest
                for manifest in self._approved.get(institution_id, ())
                if manifest.version == target_version
            ),
            None,
        )
        if target is None:
            raise ValueError(
                f"version {target_version} is not an approved version of {institution_id!r}"
            )
        before_regime_version = self._version
        self._active[institution_id] = target
        self._version += 1
        return InstitutionTransitionReport(
            proposal_id=f"rollback:{institution_id}:{target_version}",
            institution_id=institution_id,
            accepted=True,
            reasons=(),
            checks=(),
            before_regime_version=before_regime_version,
            after_regime_version=self._version,
            before_institution_version=before.version,
            after_institution_version=target.version,
        )
