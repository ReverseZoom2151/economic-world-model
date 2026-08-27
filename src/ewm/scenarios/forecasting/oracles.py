"""Independent numerical checks for the forecasting fixed points."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq

from ewm.equilibrium import FixedPointConfig, solve_ddge

from .model import (
    ForecastingConfig,
    ForecastingProblem,
    population_update,
    simulate_series,
)


@dataclass(frozen=True, slots=True)
class ForecastingOracleReport:
    """Agreement report from iteration, bracketing, derivatives, and simulation."""

    iteration_roots: tuple[float, ...]
    bracketing_roots: tuple[float, ...]
    analytical_derivative_zero: float
    numerical_derivative_zero: float
    derivatives: tuple[float, ...]
    stable: tuple[bool, ...]
    first_autocorrelations: tuple[float, ...]


def _deduplicate(values: list[float], tolerance: float = 1e-8) -> tuple[float, ...]:
    ordered = sorted(values)
    result: list[float] = []
    for value in ordered:
        if not result or abs(value - result[-1]) > tolerance:
            result.append(value)
    return tuple(result)


def _bracketing_roots(
    config: ForecastingConfig,
    bounds: tuple[float, float],
    grid_size: int,
) -> tuple[float, ...]:
    lower, upper = bounds
    grid = np.linspace(lower, upper, grid_size)

    def residual(theta: float) -> float:
        return population_update(theta, config) - theta

    values = tuple(residual(float(theta)) for theta in grid)
    candidates: list[float] = []
    for theta, value in zip(grid, values, strict=True):
        if abs(value) <= 1e-12:
            candidates.append(float(theta))
    for left, right, f_left, f_right in zip(
        grid[:-1], grid[1:], values[:-1], values[1:], strict=True
    ):
        if f_left * f_right < 0.0:
            candidates.append(brentq(residual, float(left), float(right), xtol=1e-12))
    return _deduplicate(candidates)


def _derivative(theta: float, config: ForecastingConfig, step: float = 1e-5) -> float:
    return (
        population_update(theta + step, config)
        - population_update(theta - step, config)
    ) / (2.0 * step)


def _first_autocorrelation(theta: float, config: ForecastingConfig) -> float:
    series = simulate_series(theta, config, seed=config.seed + 1)
    current = series[:-1]
    following = series[1:]
    if np.std(current) == 0.0 or np.std(following) == 0.0:
        return 0.0
    return float(np.corrcoef(current, following)[0, 1])


def oracle_report(
    config: ForecastingConfig,
    *,
    search_bounds: tuple[float, float] = (-1.5, 1.5),
    grid_size: int = 61,
) -> ForecastingOracleReport:
    """Cross-check DDGE iteration against bracketing and local analytical facts."""

    lower, upper = search_bounds
    if lower >= 0.0 or upper <= 0.0 or lower >= upper:
        raise ValueError("search_bounds must straddle zero")
    if grid_size < 3:
        raise ValueError("grid_size must be at least three")

    problem = ForecastingProblem(config)
    iterative = solve_ddge(
        problem,
        (np.array([lower]), np.array([0.0]), np.array([upper])),
        FixedPointConfig(tolerance=1e-10, max_iterations=1_000),
    )
    iteration_roots = tuple(
        sorted(float(point.theta[0]) for point in iterative.fixed_points)
    )
    bracketing_roots = _bracketing_roots(config, search_bounds, grid_size)
    derivatives = tuple(_derivative(root, config) for root in bracketing_roots)
    step = 1e-5
    derivative_zero = (
        population_update(step, config) - population_update(-step, config)
    ) / (2.0 * step)

    return ForecastingOracleReport(
        iteration_roots=iteration_roots,
        bracketing_roots=bracketing_roots,
        analytical_derivative_zero=config.feedback,
        numerical_derivative_zero=derivative_zero,
        derivatives=derivatives,
        stable=tuple(abs(value) < 1.0 for value in derivatives),
        first_autocorrelations=tuple(
            _first_autocorrelation(root, config) for root in bracketing_roots
        ),
    )
