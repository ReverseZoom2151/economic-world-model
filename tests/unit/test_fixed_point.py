from __future__ import annotations

import numpy as np
from scipy.optimize import root

from ewm.equilibrium import (
    FixedPointConfig,
    damped_eigenvalue,
    damped_update,
    iterate_fixed_point,
    solve_equilibrium,
    solve_multistart,
)


class QuadraticEquilibrium:
    def residual(self, candidate: np.ndarray) -> np.ndarray:
        return np.array([candidate[0] ** 2 - 4.0])


def test_linear_fixed_point_converges_to_closed_form() -> None:
    def update(theta: np.ndarray) -> np.ndarray:
        return 0.4 * theta + 1.2

    result = iterate_fixed_point(update, np.array([0.0]), FixedPointConfig(tolerance=1e-11))

    assert result.converged
    assert np.allclose(result.theta, np.array([2.0]), atol=1e-9)
    assert result.residual_norm <= 1e-11
    assert result.stable is True
    assert np.isclose(result.spectral_radius, 0.4, atol=1e-5)


def test_damped_update_and_eigenvalue_are_explicit() -> None:
    theta = np.array([2.0])
    raw = np.array([6.0])

    assert np.array_equal(damped_update(theta, raw, 0.25), np.array([3.0]))
    assert damped_eigenvalue(1.6, 0.1) > 1.0
    assert damped_eigenvalue(1.6, 0.5) > 1.0
    assert abs(damped_eigenvalue(-1.6, 0.5)) < 1.0


def test_multistart_surfaces_three_tanh_fixed_points_and_basins() -> None:
    def update(theta: np.ndarray) -> np.ndarray:
        return np.tanh(1.8 * theta)
    initials = [np.array([value]) for value in (-2.0, -0.2, 0.0, 0.2, 2.0)]

    result = solve_multistart(
        update,
        initials,
        FixedPointConfig(tolerance=1e-11, deduplication_tolerance=1e-7),
    )

    roots = sorted(point.theta[0] for point in result.fixed_points)
    assert len(roots) == 3
    assert roots[0] < -0.9
    assert np.isclose(roots[1], 0.0, atol=1e-10)
    assert roots[2] > 0.9
    assert len(result.diagnostics["basin_initials"]) == 3
    middle = next(point for point in result.fixed_points if abs(point.theta[0]) < 1e-8)
    assert middle.stable is False


def test_inner_equilibrium_matches_independent_scipy_root() -> None:
    problem = QuadraticEquilibrium()
    result = solve_equilibrium(problem, np.array([1.0]))
    independent = root(problem.residual, np.array([1.0]))

    assert result.converged
    assert np.allclose(result.solution, independent.x)
    assert np.allclose(result.solution, np.array([2.0]), atol=1e-9)
