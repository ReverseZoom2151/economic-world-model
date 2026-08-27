"""Stationary-kernel quadrature oracle for the forecasting population OLS map."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import isfinite, pi, sqrt

import numpy as np
from scipy.optimize import brentq

FORECASTING_ORACLE_SCOPE = "population_stationary_kernel_ols_only"


@dataclass(frozen=True, slots=True)
class StationaryOLSResult:
    """One grid-kernel stationary-law calculation and its convergence residual."""

    update: float
    stationary_residual: float
    iterations: int
    scope: str = FORECASTING_ORACLE_SCOPE


def _validated_inputs(
    feedback: float,
    noise_std: float,
    grid_bound: float,
    grid_size: int,
    stationary_tolerance: float,
) -> tuple[float, float, float, int, float]:
    values = (feedback, noise_std, grid_bound, stationary_tolerance)
    if not all(isfinite(value) for value in values):
        raise ValueError("forecasting oracle parameters must be finite")
    if feedback < 0.0 or noise_std <= 0.0 or grid_bound <= 0.0:
        raise ValueError("feedback must be nonnegative and scales must be positive")
    if grid_size < 101 or grid_size % 2 == 0:
        raise ValueError("grid_size must be an odd integer of at least 101")
    if stationary_tolerance <= 0.0:
        raise ValueError("stationary_tolerance must be positive")
    return feedback, noise_std, grid_bound, grid_size, stationary_tolerance


@lru_cache(maxsize=128)
def _positive_stationary_kernel_ols_update(
    theta: float,
    feedback: float,
    noise_std: float,
    grid_bound: float,
    grid_size: int,
    stationary_tolerance: float,
) -> StationaryOLSResult:
    grid = np.linspace(-grid_bound, grid_bound, grid_size)
    conditional_mean = np.tanh(feedback * theta * grid)
    standardized = (grid[np.newaxis, :] - conditional_mean[:, np.newaxis]) / noise_std
    transition = np.exp(-0.5 * standardized * standardized) / (
        noise_std * sqrt(2.0 * pi)
    )
    transition /= transition.sum(axis=1, keepdims=True)

    distribution = np.full(grid_size, 1.0 / grid_size)
    residual = float("inf")
    maximum_iterations = 20_000
    for _iteration in range(1, maximum_iterations + 1):
        candidate = distribution @ transition
        residual = float(np.linalg.norm(candidate - distribution, ord=1))
        distribution = candidate
        if residual <= stationary_tolerance:
            break
    else:
        raise RuntimeError("stationary kernel power iteration did not converge")
    residual = float(
        np.linalg.norm(distribution @ transition - distribution, ord=1)
    )

    second_moment = float(distribution @ (grid * grid))
    if second_moment <= 0.0:
        raise RuntimeError("stationary grid has zero second moment")
    numerator = float(distribution @ (grid * conditional_mean))
    return StationaryOLSResult(
        update=numerator / second_moment,
        stationary_residual=residual,
        iterations=_iteration,
    )


def stationary_kernel_ols_update(
    theta: float,
    *,
    feedback: float,
    noise_std: float,
    grid_bound: float,
    grid_size: int,
    stationary_tolerance: float,
) -> StationaryOLSResult:
    """Compute the population OLS map from a discretized stationary Markov kernel."""

    parameters = _validated_inputs(
        feedback,
        noise_std,
        grid_bound,
        grid_size,
        stationary_tolerance,
    )
    if not isfinite(theta):
        raise ValueError("theta must be finite")
    if theta == 0.0:
        return StationaryOLSResult(update=0.0, stationary_residual=0.0, iterations=0)
    positive = _positive_stationary_kernel_ols_update(abs(theta), *parameters)
    return StationaryOLSResult(
        update=float(np.copysign(positive.update, theta)),
        stationary_residual=positive.stationary_residual,
        iterations=positive.iterations,
    )


def forecasting_population_roots(
    *,
    feedback: float,
    noise_std: float,
    grid_bound: float,
    grid_size: int,
    stationary_tolerance: float,
) -> tuple[float, ...]:
    """Bracket population fixed points; this makes no finite-sample path claim."""

    parameters = _validated_inputs(
        feedback,
        noise_std,
        grid_bound,
        grid_size,
        stationary_tolerance,
    )
    if feedback <= 1.0:
        return (0.0,)

    def residual(theta: float) -> float:
        return stationary_kernel_ols_update(
            theta,
            feedback=parameters[0],
            noise_std=parameters[1],
            grid_bound=parameters[2],
            grid_size=parameters[3],
            stationary_tolerance=parameters[4],
        ).update - theta

    positive = float(brentq(residual, 1e-5, 1.5, xtol=1e-10, rtol=1e-12))
    return (-positive, 0.0, positive)
