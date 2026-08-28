"""Unit contracts for Cong-style quantitative bounds."""

from __future__ import annotations

from collections.abc import Callable
from itertools import pairwise

import numpy as np
import pytest

from ewm.equilibrium import (
    damping_stability_certificate,
    fragility_upper_bound,
    frozen_counterfactual_bounds,
    linear_center_displacement,
    outer_contraction_certificate,
    posteriori_welfare_bounds,
    transition_robustness_bounds,
)


def test_primitive_outer_modulus_bounds_a_composed_linear_map() -> None:
    certificate = outer_contraction_certificate(
        equilibrium_sensitivity=0.5,
        data_behavior_sensitivity=0.4,
        data_parameter_sensitivity=0.1,
        learner_stability=0.8,
    )

    def outer(theta: float) -> float:
        equilibrium = 0.5 * theta
        data = 0.4 * equilibrium + 0.1 * theta
        return 0.8 * data

    samples = np.linspace(-2.0, 2.0, 21)
    measured = max(
        abs(outer(right) - outer(left)) / abs(right - left)
        for left, right in pairwise(samples)
    )

    assert np.isclose(certificate.modulus, 0.24)
    assert certificate.is_contraction
    assert np.isclose(measured, certificate.modulus)


def test_center_displacement_matches_direct_solve_and_back_substitution() -> None:
    average_jacobian = np.array([[0.2, 0.1], [0.0, 0.3]])
    residual = np.array([1.0, -0.5])

    certificate = linear_center_displacement(average_jacobian, residual)
    independent = np.linalg.solve(np.eye(2) - average_jacobian, residual)

    assert np.allclose(certificate.displacement, independent)
    assert np.allclose(
        (np.eye(2) - average_jacobian) @ certificate.displacement,
        residual,
    )
    assert certificate.displacement_norm <= certificate.norm_bound
    assert not certificate.displacement.flags.writeable


def test_frozen_welfare_bound_matches_direct_bellman_solution_in_linear_case() -> None:
    certificate = frozen_counterfactual_bounds(
        residual_norm=0.5,
        contraction=0.5,
        discount=0.8,
        utility_sensitivity=0.2,
        transition_sensitivity=0.0,
        reward_bound=1.2,
    )
    transition = np.array([[0.7, 0.3], [0.2, 0.8]])
    baseline_utility = np.array([0.5, 0.8])
    fixed_utility = baseline_utility + 0.2
    baseline_value = np.linalg.solve(np.eye(2) - 0.8 * transition, baseline_utility)
    fixed_value = np.linalg.solve(np.eye(2) - 0.8 * transition, fixed_utility)
    actual_welfare_gap = np.linalg.norm(fixed_value - baseline_value, ord=np.inf)

    assert np.isclose(certificate.displacement_bound, 1.0)
    assert np.isclose(certificate.welfare_lipschitz, 1.0)
    assert np.isclose(certificate.welfare_bound, 1.0)
    assert np.isclose(actual_welfare_gap, certificate.welfare_bound)


def test_posteriori_welfare_bound_dominates_remaining_linear_gap() -> None:
    contraction = 0.4
    previous = np.array([0.0])
    current = contraction * previous + 1.2
    fixed_point = np.array([2.0])

    certificate = posteriori_welfare_bounds(
        contraction=contraction,
        step_norm=float(np.linalg.norm(current - previous)),
        discount=0.5,
        utility_sensitivity=0.3,
        transition_sensitivity=0.0,
        reward_bound=1.0,
    )
    actual_parameter_gap = float(np.linalg.norm(current - fixed_point))
    actual_welfare_gap = 0.3 / (1.0 - 0.5) * actual_parameter_gap

    assert certificate.distance_bound >= actual_parameter_gap
    assert certificate.welfare_bound >= actual_welfare_gap


def test_transition_bounds_dominate_direct_bellman_difference() -> None:
    discount = 0.5
    delta = 0.1
    reward = np.array([1.0, -1.0])
    baseline = np.eye(2)
    perturbed = np.array([[1.0 - delta, delta], [delta, 1.0 - delta]])
    baseline_value = np.linalg.solve(np.eye(2) - discount * baseline, reward)
    perturbed_value = np.linalg.solve(np.eye(2) - discount * perturbed, reward)
    actual_gap = np.linalg.norm(baseline_value - perturbed_value, ord=np.inf)

    certificate = transition_robustness_bounds(
        total_variation_radius=delta,
        discount=discount,
        reward_bound=1.0,
    )

    assert actual_gap <= certificate.value_bound
    assert np.isclose(certificate.value_bound, 0.4)
    assert np.isclose(certificate.robust_regret_bound, 0.8)
    assert np.isclose(fragility_upper_bound(0.03, 0.08), 0.11)


def test_damping_distinguishes_repelling_and_oscillatory_instability() -> None:
    repelling = damping_stability_certificate(np.array([[1.6]]))
    oscillatory = damping_stability_certificate(np.array([[-1.6]]))
    already_stable = damping_stability_certificate(np.array([[0.4]]))

    assert not repelling.stabilizable
    assert repelling.maximum_damping is None
    assert oscillatory.stabilizable
    assert np.isclose(oscillatory.maximum_damping, 2.0 / 2.6)
    assert oscillatory.suggested_damping is not None
    assert abs(1.0 + oscillatory.suggested_damping * (-1.6 - 1.0)) < 1.0
    assert already_stable.full_step_stable
    assert already_stable.suggested_damping == 1.0


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (
            lambda: outer_contraction_certificate(-0.1, 0.2, 0.1, 0.5),
            "non-negative",
        ),
        (
            lambda: frozen_counterfactual_bounds(0.1, 1.0, 0.9, 0.1, 0.1, 1.0),
            "contraction",
        ),
        (
            lambda: transition_robustness_bounds(0.1, 1.0, 1.0),
            "discount",
        ),
        (
            lambda: linear_center_displacement(np.array([[1.1]]), np.array([1.0])),
            "operator norm",
        ),
        (
            lambda: damping_stability_certificate(np.ones((2, 3))),
            "square",
        ),
    ],
)
def test_theorem_certificates_reject_violated_assumptions(
    call: Callable[[], object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        call()
