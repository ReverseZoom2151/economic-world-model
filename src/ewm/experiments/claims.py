"""Executable authorization boundaries for high-stakes model claims."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ClaimKind(StrEnum):
    """Public claim classes with distinct evidence requirements."""

    SYNTHETIC_CONFORMANCE = "synthetic_conformance"
    QUALITATIVE_RECONSTRUCTION = "qualitative_reconstruction"
    EXACT_REPLICATION = "exact_replication"
    EMPIRICALLY_CALIBRATED = "empirically_calibrated"
    POLICY_VALID = "policy_valid"
    DIGITAL_TWIN = "digital_twin"


@dataclass(frozen=True, slots=True)
class ClaimEvidence:
    """Evidence gates that cannot be inferred from a requested label."""

    exact_replication_identified: bool = False
    external_calibration_validated: bool = False
    policy_evaluation_validated: bool = False
    live_external_data_contract: bool = False
    repeated_out_of_sample_alignment: bool = False


@dataclass(frozen=True, slots=True)
class ClaimAuthorization:
    """Claims authorized by supplied evidence and their checked requirements."""

    authorized: tuple[ClaimKind, ...]
    checked_requirements: tuple[str, ...]


class UnsupportedClaimError(ValueError):
    """Raised when a requested model claim lacks its required evidence."""


def authorize_claims(
    requested: tuple[ClaimKind, ...],
    *,
    evidence: ClaimEvidence,
) -> ClaimAuthorization:
    """Authorize claims only from explicit evidence, never from their labels."""

    if len(requested) != len(set(requested)):
        raise ValueError("requested claims must be unique")
    missing: list[str] = []
    checked: list[str] = []
    for claim in requested:
        if claim in {
            ClaimKind.SYNTHETIC_CONFORMANCE,
            ClaimKind.QUALITATIVE_RECONSTRUCTION,
        }:
            checked.append(f"{claim.value}:scope_declaration")
        elif claim is ClaimKind.EXACT_REPLICATION:
            checked.append("exact_replication:identified_source_primitives")
            if not evidence.exact_replication_identified:
                missing.append("exact_replication requires identified source primitives")
        elif claim is ClaimKind.EMPIRICALLY_CALIBRATED:
            checked.append("empirically_calibrated:external_validation")
            if not evidence.external_calibration_validated:
                missing.append("empirically_calibrated requires external calibration validation")
        elif claim is ClaimKind.POLICY_VALID:
            checked.extend(
                (
                    "policy_valid:external_validation",
                    "policy_valid:policy_evaluation",
                )
            )
            if not evidence.external_calibration_validated:
                missing.append("policy_valid requires external calibration validation")
            if not evidence.policy_evaluation_validated:
                missing.append("policy_valid requires policy evaluation validation")
        elif claim is ClaimKind.DIGITAL_TWIN:
            checked.extend(
                (
                    "digital_twin:external_validation",
                    "digital_twin:live_data_contract",
                    "digital_twin:repeated_out_of_sample_alignment",
                )
            )
            if not evidence.external_calibration_validated:
                missing.append("digital_twin requires external calibration validation")
            if not evidence.live_external_data_contract:
                missing.append("digital_twin requires a live external data contract")
            if not evidence.repeated_out_of_sample_alignment:
                missing.append("digital_twin requires repeated out-of-sample alignment")
    if missing:
        raise UnsupportedClaimError("; ".join(missing))
    return ClaimAuthorization(
        authorized=tuple(requested),
        checked_requirements=tuple(checked),
    )
