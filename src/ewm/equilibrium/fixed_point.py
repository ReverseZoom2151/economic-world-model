"""Transparent fixed-point iteration with multistart multiplicity discovery."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ewm.core import DDGEResult, FixedPoint

from .damping import damped_update
from .diagnostics import finite_difference_jacobian, spectral_radius

UpdateFunction = Callable[[NDArray[np.float64]], NDArray[np.floating]]


@dataclass(frozen=True, slots=True)
class FixedPointConfig:
    """Numerical tolerances for transparent fixed-point iteration."""

    tolerance: float = 1e-8
    max_iterations: int = 2_000
    damping: float = 1.0
    deduplication_tolerance: float = 1e-6
    jacobian_step: float = 1e-6

    def __post_init__(self) -> None:
        if self.tolerance <= 0.0:
            raise ValueError("tolerance must be positive")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be positive")
        if not 0.0 < self.damping <= 1.0:
            raise ValueError("damping must lie in (0, 1]")
        if self.deduplication_tolerance <= 0.0:
            raise ValueError("deduplication_tolerance must be positive")
        if self.jacobian_step <= 0.0:
            raise ValueError("jacobian_step must be positive")


def _vector(value: NDArray[np.floating]) -> NDArray[np.float64]:
    result = np.asarray(value, dtype=float)
    if result.ndim != 1:
        raise ValueError("fixed-point values must be one-dimensional arrays")
    if not np.all(np.isfinite(result)):
        raise ValueError("fixed-point values must be finite")
    return result


def iterate_fixed_point(
    update: UpdateFunction,
    initial_theta: NDArray[np.floating],
    config: FixedPointConfig | None = None,
) -> FixedPoint:
    """Iterate a possibly damped update from one initialization."""

    settings = config or FixedPointConfig()
    initial = _vector(initial_theta).copy()
    theta = initial.copy()
    history: list[float] = []
    converged = False
    iteration = 0

    for iteration in range(settings.max_iterations + 1):
        raw = _vector(update(theta))
        if raw.shape != theta.shape:
            raise ValueError("update changed fixed-point dimension")
        residual = float(np.linalg.norm(raw - theta))
        history.append(residual)
        if residual <= settings.tolerance:
            converged = True
            break
        if iteration == settings.max_iterations:
            break
        theta = damped_update(theta, raw, settings.damping)

    jacobian = finite_difference_jacobian(update, theta, settings.jacobian_step)
    radius = spectral_radius(jacobian)
    return FixedPoint(
        theta=theta,
        initial_theta=initial,
        residual_norm=history[-1],
        iterations=iteration,
        converged=converged,
        stable=radius < 1.0,
        spectral_radius=radius,
        residual_history=tuple(history),
    )


def solve_multistart(
    update: UpdateFunction,
    initializations: Iterable[NDArray[np.floating]],
    config: FixedPointConfig | None = None,
) -> DDGEResult:
    """Discover and deduplicate fixed points while retaining basin provenance."""

    settings = config or FixedPointConfig()
    distinct: list[FixedPoint] = []
    basins: list[list[tuple[float, ...]]] = []
    failed: list[tuple[float, ...]] = []

    for initialization in initializations:
        point = iterate_fixed_point(update, initialization, settings)
        initial_tuple = tuple(float(value) for value in point.initial_theta)
        if not point.converged:
            failed.append(initial_tuple)
            continue
        match = next(
            (
                index
                for index, existing in enumerate(distinct)
                if np.linalg.norm(existing.theta - point.theta)
                <= settings.deduplication_tolerance
            ),
            None,
        )
        if match is None:
            distinct.append(point)
            basins.append([initial_tuple])
        else:
            basins[match].append(initial_tuple)

    selected = 0 if len(distinct) == 1 else None
    diagnostics: dict[str, Any] = {
        "basin_initials": tuple(tuple(group) for group in basins),
        "failed_initials": tuple(failed),
        "attempted_count": len(distinct) + sum(len(group) - 1 for group in basins) + len(failed),
    }
    return DDGEResult(
        fixed_points=tuple(distinct),
        selected_index=selected,
        diagnostics=diagnostics,
    )

