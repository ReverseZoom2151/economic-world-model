"""Direct expansion witness computed without the package's singular-value routine."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class DirectionExpansion:
    """A unit right direction and its directly measured expansion."""

    right_direction: NDArray[np.float64]
    input_norm: float
    output_norm: float
    expansion_ratio: float
    method: str


def right_singular_direction_expansion(
    matrix: NDArray[np.floating],
) -> DirectionExpansion:
    """Use an eigenvector of ``A.T @ A`` and measure ``||Av|| / ||v||`` directly."""

    candidate = np.asarray(matrix, dtype=float)
    if candidate.ndim != 2 or 0 in candidate.shape:
        raise ValueError("matrix must be a nonempty two-dimensional array")
    if not np.all(np.isfinite(candidate)):
        raise ValueError("matrix must be finite")
    eigenvalues, eigenvectors = np.linalg.eigh(candidate.T @ candidate)
    direction = np.asarray(eigenvectors[:, int(np.argmax(eigenvalues))], dtype=float)
    direction.setflags(write=False)
    input_norm = float(np.linalg.norm(direction))
    output_norm = float(np.linalg.norm(candidate @ direction))
    return DirectionExpansion(
        right_direction=direction,
        input_norm=input_norm,
        output_norm=output_norm,
        expansion_ratio=output_norm / input_norm,
        method="eigenvector_of_transpose_times_matrix_then_direct_norm",
    )
