"""Residual, Jacobian, contraction, and stability diagnostics."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

UpdateFunction = Callable[[NDArray[np.float64]], NDArray[np.floating]]


def _vector(value: NDArray[np.floating]) -> NDArray[np.float64]:
    result = np.asarray(value, dtype=float)
    if result.ndim != 1:
        raise ValueError("fixed-point values must be one-dimensional arrays")
    if not np.all(np.isfinite(result)):
        raise ValueError("fixed-point values must be finite")
    return result


def fixed_point_residual(update: UpdateFunction, theta: NDArray[np.floating]) -> float:
    """Compute the Euclidean residual ``||F(theta)-theta||``."""

    current = _vector(theta)
    candidate = _vector(update(current))
    if candidate.shape != current.shape:
        raise ValueError("update changed fixed-point dimension")
    return float(np.linalg.norm(candidate - current))


def finite_difference_jacobian(
    update: UpdateFunction,
    theta: NDArray[np.floating],
    step: float = 1e-6,
) -> NDArray[np.float64]:
    """Estimate ``DF(theta)`` using a central finite difference."""

    if step <= 0.0:
        raise ValueError("step must be positive")
    center = _vector(theta)
    dimension = center.size
    jacobian = np.empty((dimension, dimension), dtype=float)
    for column in range(dimension):
        delta = np.zeros(dimension, dtype=float)
        delta[column] = step
        upper = _vector(update(center + delta))
        lower = _vector(update(center - delta))
        if upper.shape != center.shape or lower.shape != center.shape:
            raise ValueError("update changed fixed-point dimension")
        jacobian[:, column] = (upper - lower) / (2.0 * step)
    return jacobian


def local_modulus(jacobian: NDArray[np.floating]) -> float:
    """Return the Euclidean operator norm used for a local contraction check."""

    matrix = np.asarray(jacobian, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("jacobian must be square")
    return float(np.linalg.norm(matrix, ord=2))


def spectral_radius(jacobian: NDArray[np.floating]) -> float:
    """Return the largest absolute Jacobian eigenvalue."""

    matrix = np.asarray(jacobian, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("jacobian must be square")
    return float(np.max(np.abs(np.linalg.eigvals(matrix))))


def posteriori_distance_bound(contraction: float, step_norm: float) -> float:
    """Bound remaining distance from one observed contraction step."""

    if not 0.0 <= contraction < 1.0:
        raise ValueError("contraction must lie in [0, 1)")
    if step_norm < 0.0:
        raise ValueError("step_norm must be non-negative")
    return contraction / (1.0 - contraction) * step_norm

