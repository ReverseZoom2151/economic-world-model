from __future__ import annotations

from itertools import pairwise

import numpy as np
import pytest

import ewm
from ewm.equilibrium import FixedPointConfig, posteriori_distance_bound, solve_ddge
from ewm.scenarios.scalar import (
    ScalarConfig,
    ScalarLearner,
    ScalarProblem,
    bracketed_fixed_points,
    inner_solution,
    linear_displacement,
    near_onset_expansion,
    outer_derivative,
    outer_update,
    retraining_path,
    scalar_verification_report,
)


def _config(
    *,
    phi: float,
    learning_gain: float,
    intervention: float = 0.0,
    learner: ScalarLearner = ScalarLearner.TANH,
) -> ScalarConfig:
    return ScalarConfig(
        kappa=phi,
        gamma=1.0,
        learning_gain=learning_gain,
        intervention=intervention,
        learner=learner,
    )


def test_equation_a1_inner_solution_and_composite_gain_are_exact() -> None:
    config = _config(phi=0.4, learning_gain=0.4, intervention=0.05)

    solution = inner_solution(theta=0.2, config=config)

    assert np.isclose(solution.behavior, (0.2 + 0.05) / (1.0 - 0.4))
    assert np.isclose(solution.response, solution.behavior)
    assert np.isclose(solution.sensitivity, 1.0 / (1.0 - 0.4))
    assert np.isclose(config.composite_gain, 0.4 / (1.0 - 0.4))
    assert np.isclose(
        solution.behavior,
        config.kappa * solution.response + 0.2 + config.intervention,
    )


def test_linear_intervention_displacement_matches_closed_form_and_solver() -> None:
    config = _config(
        phi=0.4,
        learning_gain=0.4,
        intervention=0.05,
        learner=ScalarLearner.LINEAR,
    )

    closed_form = linear_displacement(config)
    result = solve_ddge(
        ScalarProblem(config),
        (np.array([-0.5]), np.array([0.0]), np.array([0.5])),
        FixedPointConfig(tolerance=1e-13, max_iterations=1_000),
    )

    assert len(result.fixed_points) == 1
    assert closed_form.fixed_point == pytest.approx(
        config.learning_gain
        * config.intervention
        / (1.0 - config.inner_feedback - config.learning_gain)
    )
    assert closed_form.residual == pytest.approx(
        config.composite_gain * config.intervention
    )
    assert closed_form.displacement == pytest.approx(
        closed_form.residual / (1.0 - config.composite_gain)
    )
    assert result.fixed_points[0].theta[0] == pytest.approx(
        closed_form.fixed_point, abs=1e-11
    )


@pytest.mark.parametrize(
    ("gain", "root_count"),
    [(0.8, 1), (1.0, 1), (1.01, 3), (1.6, 3)],
)
def test_saturating_model_has_three_ddges_exactly_when_gain_exceeds_one(
    gain: float, root_count: int
) -> None:
    learning_gain = 0.6
    phi = 1.0 - learning_gain / gain
    config = _config(phi=phi, learning_gain=learning_gain)

    roots = bracketed_fixed_points(config)

    assert len(roots) == root_count
    assert roots == tuple(sorted(roots))
    assert 0.0 in roots
    for root in roots:
        assert outer_update(root, config) == pytest.approx(root, abs=1e-11)
    if root_count == 3:
        assert roots[0] == pytest.approx(-roots[2], abs=1e-12)
        assert abs(outer_derivative(0.0, config)) > 1.0
        assert abs(outer_derivative(roots[0], config)) < 1.0
        assert abs(outer_derivative(roots[2], config)) < 1.0


def test_near_onset_expansion_matches_figure_3_error_ranges() -> None:
    learning_gain = 0.6
    errors: dict[float, float] = {}
    for gain in (1.01, 1.02, 1.03, 1.04, 1.045, 1.05):
        phi = 1.0 - learning_gain / gain
        config = _config(phi=phi, learning_gain=learning_gain)
        exact = bracketed_fixed_points(config)[2]
        approximation = near_onset_expansion(config)
        errors[gain] = abs(approximation - exact) / exact

    assert max(error for gain, error in errors.items() if gain <= 1.045) < 0.0265
    assert errors[1.05] == pytest.approx(0.029, abs=0.0002)


def test_saturating_spectral_prediction_converges_at_first_order() -> None:
    predictions: dict[float, float] = {}
    exact_values: dict[float, float] = {}
    for intervention in (0.05, 0.005):
        config = _config(
            phi=0.4,
            learning_gain=0.4,
            intervention=intervention,
        )
        residual = outer_update(0.0, config)
        prediction = residual / (1.0 - outer_derivative(0.0, config))
        exact = bracketed_fixed_points(config)[0]
        predictions[intervention] = prediction
        exact_values[intervention] = exact

    large_error = abs(predictions[0.05] - exact_values[0.05]) / exact_values[0.05]
    small_error = abs(predictions[0.005] - exact_values[0.005]) / exact_values[0.005]
    assert large_error == pytest.approx(0.041, abs=0.001)
    assert small_error == pytest.approx(0.0005, abs=0.0001)


def test_damping_repairs_contrarian_oscillation_but_not_repelling_origin() -> None:
    self_confirming = _config(phi=0.5, learning_gain=0.8)
    contrarian = _config(phi=0.5, learning_gain=-0.8)

    repelling_paths = tuple(
        retraining_path(1e-3, self_confirming, rounds=80, damping=damping)
        for damping in (1.0, 0.3, 0.1)
    )
    undamped_contrarian = retraining_path(0.2, contrarian, rounds=100, damping=1.0)
    damped_contrarian = retraining_path(0.2, contrarian, rounds=100, damping=0.5)

    assert all(abs(path[-1]) > abs(path[0]) for path in repelling_paths)
    assert abs(undamped_contrarian[-1]) > 0.1
    assert np.sign(undamped_contrarian[-1]) != np.sign(undamped_contrarian[-2])
    assert abs(damped_contrarian[-1]) < 1e-12


def test_one_observed_step_bounds_remaining_distance_in_contraction_regime() -> None:
    config = _config(phi=0.3, learning_gain=0.4, intervention=0.04)
    root = bracketed_fixed_points(config)[0]
    path = retraining_path(-0.2, config, rounds=12, damping=1.0)

    for previous, current in pairwise(path):
        bound = posteriori_distance_bound(
            abs(config.composite_gain), abs(current - previous)
        )
        assert abs(current - root) <= bound + 1e-12


def test_bracketing_and_iteration_independently_agree_on_all_roots() -> None:
    config = _config(phi=0.5, learning_gain=0.8)

    report = scalar_verification_report(config)
    iterative = solve_ddge(
        ScalarProblem(config),
        tuple(np.array([value]) for value in (-1.0, 0.0, 1.0)),
        FixedPointConfig(
            tolerance=1e-12,
            max_iterations=10_000,
            deduplication_tolerance=1e-9,
        ),
    )
    iterative_roots = tuple(
        sorted(float(point.theta[0]) for point in iterative.fixed_points)
    )

    assert len(report.bracketing_roots) == len(iterative_roots) == 3
    assert np.allclose(report.bracketing_roots, iterative_roots, atol=1e-9)
    assert report.stable == (True, False, True)
    assert max(report.fixed_point_residuals) < 1e-10


def test_scalar_scenario_is_available_through_public_package() -> None:
    scenario = ewm.make("scalar", preset="smoke", seed=42)
    result = ewm.solve_ddge(
        scenario.ddge_problem(),
        (np.array([-1.0]), np.array([0.0]), np.array([1.0])),
        FixedPointConfig(tolerance=1e-11, max_iterations=2_000),
    )

    assert len(result.fixed_points) == 3
    assert "scalar" in ewm.list_scenarios()


def test_scalar_configuration_rejects_theorem_domain_violations() -> None:
    with pytest.raises(ValueError, match="inner feedback"):
        _config(phi=1.0, learning_gain=0.4)
    with pytest.raises(ValueError, match="linear displacement requires"):
        linear_displacement(_config(phi=0.4, learning_gain=0.4))
    with pytest.raises(ValueError, match="zero intervention"):
        near_onset_expansion(
            _config(phi=0.5, learning_gain=0.8, intervention=0.01)
        )
