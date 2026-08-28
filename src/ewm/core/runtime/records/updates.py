"""Layer-neutral runtime state-update primitives."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray


def convex_update(
    current: NDArray[np.floating[Any]],
    proposal: NDArray[np.floating[Any]],
    weight: float,
) -> NDArray[np.float64]:
    """Blend current and proposed values as ``(1-weight) current + weight proposal``."""

    if not np.isfinite(weight) or not 0.0 < weight <= 1.0:
        raise ValueError("weight must lie in (0, 1]")
    current_array = np.asarray(current, dtype=float)
    proposal_array = np.asarray(proposal, dtype=float)
    if current_array.shape != proposal_array.shape:
        raise ValueError("current and proposal must have equal shape")
    if not np.all(np.isfinite(current_array)) or not np.all(
        np.isfinite(proposal_array)
    ):
        raise ValueError("current and proposal must be finite")
    return np.asarray(
        (1.0 - weight) * current_array + weight * proposal_array,
        dtype=float,
    )
