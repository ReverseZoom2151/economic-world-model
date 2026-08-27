"""Damped fixed-point updates and their local eigenvalues."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from ewm.core import convex_update


@dataclass(frozen=True, slots=True)
class DampingStabilityCertificate:
    """Appendix A.10 local damping test for all Jacobian eigenvalues."""

    eigenvalues: tuple[complex, ...]
    stabilizable: bool
    full_step_stable: bool
    maximum_damping: float | None
    suggested_damping: float | None


def damped_update(
    theta: NDArray[np.floating],
    raw_update: NDArray[np.floating],
    damping: float,
) -> NDArray[np.float64]:
    """Return ``(1-eta) theta + eta F(theta)``."""

    return convex_update(theta, raw_update, damping)


def damped_eigenvalue(eigenvalue: complex, damping: float) -> complex:
    """Map an eigenvalue of ``F`` to that of the damped update."""

    if not 0.0 < damping <= 1.0:
        raise ValueError("damping must lie in (0, 1]")
    return 1.0 + damping * (eigenvalue - 1.0)


def damping_stability_certificate(
    jacobian: NDArray[np.floating],
) -> DampingStabilityCertificate:
    """Determine whether some positive damping restores local convergence.

    `maximum_damping` is the supremum over admissible damping levels in ``(0, 1]``. When
    `full_step_stable` is false, strict stability requires a damping level below that supremum.
    """

    matrix = np.asarray(jacobian, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("jacobian must be square")
    if matrix.shape[0] == 0 or not np.all(np.isfinite(matrix)):
        raise ValueError("jacobian must be nonempty and finite")
    values = tuple(complex(value) for value in np.linalg.eigvals(matrix))
    full_step_stable = max(abs(value) for value in values) < 1.0
    if any(value.real >= 1.0 for value in values):
        return DampingStabilityCertificate(
            eigenvalues=values,
            stabilizable=False,
            full_step_stable=full_step_stable,
            maximum_damping=None,
            suggested_damping=None,
        )

    thresholds = tuple(
        -2.0 * (value.real - 1.0) / abs(value - 1.0) ** 2 for value in values
    )
    maximum = min(1.0, min(thresholds))
    suggested = 1.0 if full_step_stable else 0.5 * maximum
    return DampingStabilityCertificate(
        eigenvalues=values,
        stabilizable=True,
        full_step_stable=full_step_stable,
        maximum_damping=maximum,
        suggested_damping=suggested,
    )
