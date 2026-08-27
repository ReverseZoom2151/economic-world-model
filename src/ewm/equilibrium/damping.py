"""Damped fixed-point updates and their local eigenvalues."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def damped_update(
    theta: NDArray[np.floating],
    raw_update: NDArray[np.floating],
    damping: float,
) -> NDArray[np.float64]:
    """Return ``(1-eta) theta + eta F(theta)``."""

    if not 0.0 < damping <= 1.0:
        raise ValueError("damping must lie in (0, 1]")
    current = np.asarray(theta, dtype=float)
    candidate = np.asarray(raw_update, dtype=float)
    if current.shape != candidate.shape:
        raise ValueError("theta and raw_update must have equal shape")
    return np.asarray((1.0 - damping) * current + damping * candidate, dtype=float)


def damped_eigenvalue(eigenvalue: complex, damping: float) -> complex:
    """Map an eigenvalue of ``F`` to that of the damped update."""

    if not 0.0 < damping <= 1.0:
        raise ValueError("damping must lie in (0, 1]")
    return 1.0 + damping * (eigenvalue - 1.0)

