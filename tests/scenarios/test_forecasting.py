from __future__ import annotations

import numpy as np
import pytest

from ewm.core import DDGEResult
from ewm.equilibrium import FixedPointConfig, solve_ddge
from ewm.scenarios.forecasting import (
    ForecastingConfig,
    ForecastingProblem,
    finite_sample_update,
    oracle_report,
    population_update,
)


def _config(feedback: float) -> ForecastingConfig:
    return ForecastingConfig(
        feedback=feedback,
        noise_std=0.35,
        burn_in=256,
        sample_size=4_096,
        chains=64,
        seed=123,
    )


def _solve(config: ForecastingConfig) -> DDGEResult:
    problem = ForecastingProblem(config)
    return solve_ddge(
        problem,
        (np.array([-1.5]), np.array([0.0]), np.array([1.5])),
        FixedPointConfig(tolerance=1e-9, max_iterations=500),
    )


def test_population_map_has_exact_origin_and_analytical_local_derivative() -> None:
    config = _config(feedback=1.8)

    assert population_update(0.0, config) == 0.0
    step = 1e-4
    derivative = (
        population_update(step, config) - population_update(-step, config)
    ) / (2.0 * step)

    assert derivative == pytest.approx(config.feedback, abs=1e-6)


def test_weak_feedback_has_one_stable_fixed_point() -> None:
    result = _solve(_config(feedback=0.8))

    assert len(result.fixed_points) == 1
    point = result.fixed_points[0]
    assert point.theta[0] == pytest.approx(0.0, abs=1e-7)
    assert point.stable is True
    assert point.spectral_radius == pytest.approx(0.8, abs=1e-5)


def test_strong_feedback_has_three_fixed_points_and_sign_selected_basins() -> None:
    result = _solve(_config(feedback=1.8))

    assert len(result.fixed_points) == 3
    ordered = sorted(result.fixed_points, key=lambda point: point.theta[0])
    assert ordered[0].theta[0] < -0.8
    assert ordered[1].theta[0] == 0.0
    assert ordered[2].theta[0] > 0.8
    assert ordered[0].stable is True
    assert ordered[1].stable is False
    assert ordered[2].stable is True

    basins = result.diagnostics["basin_initials"]
    by_sign = {
        int(np.sign(point.theta[0])): tuple(initials)
        for point, initials in zip(result.fixed_points, basins, strict=True)
    }
    assert by_sign[-1] == ((-1.5,),)
    assert by_sign[0] == ((0.0,),)
    assert by_sign[1] == ((1.5,),)


def test_finite_sample_retraining_ejects_exact_zero() -> None:
    config = ForecastingConfig(
        feedback=1.8,
        noise_std=0.35,
        burn_in=0,
        sample_size=128,
        chains=1,
        seed=2026,
    )

    next_theta = finite_sample_update(0.0, config)

    assert abs(next_theta) > 0.05


def test_oracle_independently_confirms_roots_and_stability() -> None:
    report = oracle_report(
        _config(feedback=1.8),
        search_bounds=(-1.5, 1.5),
        grid_size=41,
    )

    assert len(report.iteration_roots) == len(report.bracketing_roots) == 3
    assert np.allclose(report.iteration_roots, report.bracketing_roots, atol=2e-6)
    assert report.numerical_derivative_zero == pytest.approx(
        report.analytical_derivative_zero, abs=1e-6
    )
    assert report.stable == (True, False, True)
    assert all(-1.0 <= value <= 1.0 for value in report.first_autocorrelations)
