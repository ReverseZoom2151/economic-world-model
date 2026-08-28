"""Unit contracts for restricted theorem certificates."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pytest

from ewm.equilibrium import (
    ObligationStatus,
    affine_polyhedral_certificate,
    fragility_upper_bound,
    local_linear_certificate,
    transition_robustness_bounds,
)


def _unit_box(dimension: int) -> tuple[np.ndarray, np.ndarray]:
    identity = np.eye(dimension)
    return np.vstack((identity, -identity)), np.ones(2 * dimension)


def test_affine_polyhedral_certificate_has_provenance_and_solver_residuals() -> None:
    constraints, bounds = _unit_box(2)
    certificate = affine_polyhedral_certificate(
        matrix=np.array([[0.4, 0.1], [0.0, 0.25]]),
        offset=np.array([0.1, -0.2]),
        constraint_matrix=constraints,
        constraint_bounds=bounds,
        map_provenance="unit-test:declared-affine-map",
        domain_provenance="unit-test:declared-unit-box",
    )

    assert certificate.restricted_existence_certified
    assert certificate.restricted_uniqueness_certified
    assert certificate.fixed_point_residual <= certificate.tolerance
    assert certificate.maximum_linear_program_residual <= certificate.tolerance
    assert certificate.maximum_domain_violation <= certificate.tolerance
    assert certificate.maximum_self_map_violation <= certificate.tolerance
    assert np.allclose(
        certificate.matrix @ certificate.fixed_point + certificate.offset,
        certificate.fixed_point,
    )
    assert certificate.obligation("restricted:affine_map").provenance == (
        "unit-test:declared-affine-map"
    )
    assert certificate.obligation("restricted:nonempty_compact_polyhedron").provenance == (
        "unit-test:declared-unit-box; scipy.optimize.linprog(method='highs')"
    )
    assert certificate.obligation(
        "restricted:linear_program_residuals"
    ).status is ObligationStatus.VERIFIED
    assert not certificate.fixed_point.flags.writeable


def test_general_assumption_and_kakutani_obligations_remain_blocked() -> None:
    constraints, bounds = _unit_box(1)
    certificate = affine_polyhedral_certificate(
        matrix=np.array([[0.5]]),
        offset=np.array([0.0]),
        constraint_matrix=constraints,
        constraint_bounds=bounds,
        map_provenance="unit-test:scalar-map",
        domain_provenance="unit-test:interval",
    )

    assert certificate.obligation(
        "general:assumption_3_2_correspondence"
    ).status is ObligationStatus.BLOCKED
    assert certificate.obligation(
        "general:kakutani_existence"
    ).status is ObligationStatus.BLOCKED
    assert certificate.restricted_existence_certified


def test_failed_self_map_does_not_create_an_existence_certificate() -> None:
    constraints, bounds = _unit_box(1)
    certificate = affine_polyhedral_certificate(
        matrix=np.array([[0.5]]),
        offset=np.array([1.0]),
        constraint_matrix=constraints,
        constraint_bounds=bounds,
        map_provenance="unit-test:translated-map",
        domain_provenance="unit-test:interval",
    )

    assert not certificate.restricted_existence_certified
    assert not certificate.restricted_uniqueness_certified
    assert certificate.maximum_self_map_violation == pytest.approx(0.5)
    assert certificate.maximum_domain_violation == pytest.approx(1.0)
    assert certificate.fixed_point_residual <= certificate.tolerance
    assert certificate.obligation(
        "restricted:self_map"
    ).status is ObligationStatus.FAILED


def test_identity_self_map_certifies_existence_but_not_uniqueness() -> None:
    constraints, bounds = _unit_box(1)
    certificate = affine_polyhedral_certificate(
        matrix=np.array([[1.0]]),
        offset=np.array([0.0]),
        constraint_matrix=constraints,
        constraint_bounds=bounds,
        map_provenance="unit-test:identity",
        domain_provenance="unit-test:interval",
    )

    assert certificate.restricted_existence_certified
    assert not certificate.restricted_uniqueness_certified
    assert certificate.obligation(
        "restricted:euclidean_contraction"
    ).status is ObligationStatus.FAILED


def test_singular_value_non_contraction_is_distinct_from_spectral_stability() -> None:
    diagnostics = local_linear_certificate(np.array([[0.0, 2.0], [0.0, 0.0]]))

    assert diagnostics.maximum_singular_value == pytest.approx(2.0)
    assert diagnostics.spectral_radius == pytest.approx(0.0)
    assert diagnostics.singular_value_non_contraction
    assert not diagnostics.euclidean_contraction
    assert diagnostics.spectrally_stable


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (
            lambda: affine_polyhedral_certificate(
                matrix=np.array([[0.5]]),
                offset=np.array([0.0]),
                constraint_matrix=np.array([[-1.0]]),
                constraint_bounds=np.array([0.0]),
                map_provenance="unit-test:map",
                domain_provenance="unit-test:unbounded-halfline",
            ),
            "bounded",
        ),
        (
            lambda: affine_polyhedral_certificate(
                matrix=np.array([[0.5]]),
                offset=np.array([0.0]),
                constraint_matrix=np.array([[1.0], [-1.0]]),
                constraint_bounds=np.array([0.0, -1.0]),
                map_provenance="unit-test:map",
                domain_provenance="unit-test:empty-domain",
            ),
            "nonempty",
        ),
        (
            lambda: affine_polyhedral_certificate(
                matrix=np.array([[0.5]]),
                offset=np.array([0.0]),
                constraint_matrix=np.array([[1.0], [-1.0]]),
                constraint_bounds=np.array([1.0, 1.0]),
                map_provenance="",
                domain_provenance="unit-test:interval",
            ),
            "map_provenance",
        ),
        (
            lambda: transition_robustness_bounds(1.01, 0.5, 1.0),
            r"\[0, 1\]",
        ),
        (
            lambda: fragility_upper_bound(0.1, 1.01),
            r"\[0, 1\]",
        ),
    ],
)
def test_restricted_certificates_reject_unproved_or_invalid_domains(
    call: Callable[[], object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        call()
