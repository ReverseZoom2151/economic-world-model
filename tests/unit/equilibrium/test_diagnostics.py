"""Unit contracts for equilibrium diagnostics."""

import numpy as np
import pytest

from ewm.equilibrium import (
    finite_difference_jacobian,
    fixed_point_residual,
    local_modulus,
    posteriori_distance_bound,
)


def test_finite_difference_jacobian_and_modulus_match_linear_map() -> None:
    matrix = np.array([[0.4, 0.1], [0.0, -0.2]])

    def update(theta: np.ndarray) -> np.ndarray:
        return matrix @ theta + np.array([1.0, -1.0])

    jacobian = finite_difference_jacobian(update, np.array([2.0, 3.0]))

    assert np.allclose(jacobian, matrix, atol=1e-6)
    assert np.isclose(local_modulus(jacobian), np.linalg.norm(matrix, ord=2))


def test_residual_and_posteriori_bound_dominate_true_linear_distance() -> None:
    contraction = 0.4

    def update(theta: np.ndarray) -> np.ndarray:
        return contraction * theta + 1.2
    previous = np.array([0.0])
    current = update(previous)
    truth = np.array([2.0])

    residual = fixed_point_residual(update, current)
    bound = posteriori_distance_bound(contraction, np.linalg.norm(current - previous))

    assert np.isclose(residual, 0.48)
    assert bound >= np.linalg.norm(current - truth)


def test_posteriori_bound_requires_a_contraction() -> None:
    with pytest.raises(ValueError, match=r"\[0, 1\)"):
        posteriori_distance_bound(1.0, 0.2)
