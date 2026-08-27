"""Independent bracketing checks for Cong's scalar DDGE laboratory."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq

from ewm.equilibrium import FixedPointConfig, solve_ddge

from .model import (
    ScalarConfig,
    ScalarLearner,
    ScalarProblem,
    outer_derivative,
    outer_update,
)


def _deduplicate(values: list[float], tolerance: float = 1e-9) -> tuple[float, ...]:
    result: list[float] = []
    for value in sorted(values):
        if not result or abs(value - result[-1]) > tolerance:
            result.append(value)
    return tuple(result)


def bracketed_fixed_points(
    config: ScalarConfig,
    *,
    grid_size: int = 8_001,
) -> tuple[float, ...]:
    """Find every scalar root by sign bracketing on the learner's bounded range."""

    if config.learner is not ScalarLearner.TANH:
        raise ValueError("bracketing oracle requires the saturating learner")
    if grid_size < 101:
        raise ValueError("grid_size must be at least 101")
    bound = max(abs(config.learning_gain), 1e-6)
    grid = np.linspace(-bound, bound, grid_size)

    def residual(theta: float) -> float:
        return outer_update(theta, config) - theta

    values = tuple(residual(float(theta)) for theta in grid)
    candidates = [
        float(theta)
        for theta, value in zip(grid, values, strict=True)
        if abs(value) <= 1e-13
    ]
    for index in range(grid_size - 1):
        left = float(grid[index])
        right = float(grid[index + 1])
        f_left = values[index]
        f_right = values[index + 1]
        if f_left * f_right < 0.0:
            candidates.append(brentq(residual, left, right, xtol=1e-14))
    return _deduplicate(candidates)


@dataclass(frozen=True, slots=True)
class ScalarVerificationReport:
    """Closed-form facts checked by independent root-finding and iteration."""

    bracketing_roots: tuple[float, ...]
    iterative_roots: tuple[float, ...]
    derivatives: tuple[float, ...]
    stable: tuple[bool, ...]
    fixed_point_residuals: tuple[float, ...]


def scalar_verification_report(config: ScalarConfig) -> ScalarVerificationReport:
    """Cross-check the zero-intervention saturating DDGE set by two numerical routes."""

    if config.learner is not ScalarLearner.TANH or config.intervention != 0.0:
        raise ValueError("verification report requires a zero-intervention saturating model")
    bracketed = bracketed_fixed_points(config)
    bound = max(abs(config.learning_gain), 1.0)
    starts = tuple(np.array([value]) for value in (-bound, 0.0, bound))
    iterative = solve_ddge(
        ScalarProblem(config),
        starts,
        FixedPointConfig(
            tolerance=1e-12,
            max_iterations=10_000,
            deduplication_tolerance=1e-9,
        ),
    )
    iterative_roots = tuple(
        sorted(float(point.theta[0]) for point in iterative.fixed_points)
    )
    derivatives = tuple(outer_derivative(root, config) for root in bracketed)
    return ScalarVerificationReport(
        bracketing_roots=bracketed,
        iterative_roots=iterative_roots,
        derivatives=derivatives,
        stable=tuple(abs(value) < 1.0 for value in derivatives),
        fixed_point_residuals=tuple(
            abs(outer_update(root, config) - root) for root in bracketed
        ),
    )
