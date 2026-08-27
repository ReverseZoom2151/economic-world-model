from __future__ import annotations

import pytest

from ewm.capabilities import (
    CapabilityLevel,
    assess_capability,
    documented_prototype_evidence,
)
from ewm.experiments import (
    ClaimEvidence,
    ClaimKind,
    UnsupportedClaimError,
    authorize_claims,
)

pytestmark = pytest.mark.conformance


@pytest.mark.parametrize(
    "claim",
    [
        ClaimKind.EXACT_REPLICATION,
        ClaimKind.EMPIRICALLY_CALIBRATED,
        ClaimKind.POLICY_VALID,
        ClaimKind.DIGITAL_TWIN,
    ],
)
def test_unsupported_high_stakes_labels_are_rejected(claim: ClaimKind) -> None:
    with pytest.raises(UnsupportedClaimError):
        authorize_claims((claim,), evidence=ClaimEvidence())


def test_scope_labels_are_allowed_without_becoming_validity_claims() -> None:
    authorization = authorize_claims(
        (
            ClaimKind.SYNTHETIC_CONFORMANCE,
            ClaimKind.QUALITATIVE_RECONSTRUCTION,
        ),
        evidence=ClaimEvidence(),
    )

    assert authorization.authorized == (
        ClaimKind.SYNTHETIC_CONFORMANCE,
        ClaimKind.QUALITATIVE_RECONSTRUCTION,
    )


def test_digital_twin_requires_all_external_evidence_gates() -> None:
    incomplete = ClaimEvidence(
        external_calibration_validated=True,
        live_external_data_contract=True,
    )

    with pytest.raises(UnsupportedClaimError, match="repeated out-of-sample"):
        authorize_claims((ClaimKind.DIGITAL_TWIN,), evidence=incomplete)

    complete = ClaimEvidence(
        external_calibration_validated=True,
        live_external_data_contract=True,
        repeated_out_of_sample_alignment=True,
    )
    assert authorize_claims(
        (ClaimKind.DIGITAL_TWIN,), evidence=complete
    ).authorized == (ClaimKind.DIGITAL_TWIN,)


def test_documented_prototype_evidence_awards_l2_and_no_higher() -> None:
    assessment = assess_capability(documented_prototype_evidence())

    assert assessment.achieved_level is CapabilityLevel.L2
    assert any("fake-backend" in warning for warning in assessment.warnings)
    assert any("fixture" in warning for warning in assessment.warnings)
