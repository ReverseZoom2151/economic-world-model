"""Residual, Jacobian, contraction, and fixed-point stability diagnostics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite

import numpy as np
from numpy.typing import NDArray

UpdateFunction = Callable[[NDArray[np.float64]], NDArray[np.floating]]


def _nonnegative(value: float, name: str) -> float:
    result = float(value)
    if not isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


def _contraction(value: float) -> float:
    result = float(value)
    if not isfinite(result) or not 0.0 <= result < 1.0:
        raise ValueError("contraction must lie in [0, 1)")
    return result


def _discount(value: float) -> float:
    result = float(value)
    if not isfinite(result) or not 0.0 <= result < 1.0:
        raise ValueError("discount must lie in [0, 1)")
    return result


def _total_variation(value: float, name: str) -> float:
    result = float(value)
    if not isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must lie in [0, 1]")
    return result


def _readonly(value: NDArray[np.floating]) -> NDArray[np.float64]:
    owned = np.array(value, dtype=float, copy=True)
    owned.setflags(write=False)
    return owned


@dataclass(frozen=True, slots=True)
class OuterContractionCertificate:
    """Proposition A.8 primitive constants and their composed modulus."""

    equilibrium_sensitivity: float
    data_behavior_sensitivity: float
    data_parameter_sensitivity: float
    learner_stability: float
    modulus: float

    @property
    def is_contraction(self) -> bool:
        return self.modulus < 1.0


@dataclass(frozen=True, slots=True)
class FrozenCounterfactualBounds:
    """Theorem 3.4 displacement and welfare bounds under stated constants."""

    residual_norm: float
    contraction: float
    discount: float
    utility_sensitivity: float
    transition_sensitivity: float
    reward_bound: float
    displacement_bound: float
    welfare_lipschitz: float
    welfare_bound: float


@dataclass(frozen=True, slots=True)
class CenterDisplacementCertificate:
    """Equation 3.1 for a caller-supplied averaged Jacobian."""

    average_jacobian: NDArray[np.float64]
    residual: NDArray[np.float64]
    displacement: NDArray[np.float64]
    operator_norm: float
    displacement_norm: float
    norm_bound: float


@dataclass(frozen=True, slots=True)
class PosterioriWelfareBounds:
    """Corollary A.9 parameter and welfare bounds from one observed step."""

    contraction: float
    step_norm: float
    distance_bound: float
    welfare_lipschitz: float
    welfare_bound: float


@dataclass(frozen=True, slots=True)
class TransitionRobustnessBounds:
    """Proposition 4.1 value and robust-regret bounds in total variation."""

    total_variation_radius: float
    discount: float
    reward_bound: float
    value_bound: float
    robust_regret_bound: float


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


def outer_contraction_certificate(
    equilibrium_sensitivity: float,
    data_behavior_sensitivity: float,
    data_parameter_sensitivity: float,
    learner_stability: float,
) -> OuterContractionCertificate:
    """Evaluate ``L_L (L_D,S L_S + L_D,theta)`` from Proposition A.8."""

    equilibrium = _nonnegative(equilibrium_sensitivity, "equilibrium_sensitivity")
    data_behavior = _nonnegative(data_behavior_sensitivity, "data_behavior_sensitivity")
    data_parameter = _nonnegative(data_parameter_sensitivity, "data_parameter_sensitivity")
    learner = _nonnegative(learner_stability, "learner_stability")
    modulus = learner * (data_behavior * equilibrium + data_parameter)
    return OuterContractionCertificate(
        equilibrium_sensitivity=equilibrium,
        data_behavior_sensitivity=data_behavior,
        data_parameter_sensitivity=data_parameter,
        learner_stability=learner,
        modulus=modulus,
    )


def _welfare_lipschitz(
    discount: float,
    utility_sensitivity: float,
    transition_sensitivity: float,
    reward_bound: float,
) -> float:
    beta = _discount(discount)
    utility = _nonnegative(utility_sensitivity, "utility_sensitivity")
    transition = _nonnegative(transition_sensitivity, "transition_sensitivity")
    reward = _nonnegative(reward_bound, "reward_bound")
    return utility / (1.0 - beta) + (
        2.0 * beta * reward * transition / (1.0 - beta) ** 2
    )


def frozen_counterfactual_bounds(
    residual_norm: float,
    contraction: float,
    discount: float,
    utility_sensitivity: float,
    transition_sensitivity: float,
    reward_bound: float,
) -> FrozenCounterfactualBounds:
    """Evaluate the displacement and welfare inequalities in Theorem 3.4."""

    residual = _nonnegative(residual_norm, "residual_norm")
    modulus = _contraction(contraction)
    beta = _discount(discount)
    utility = _nonnegative(utility_sensitivity, "utility_sensitivity")
    transition = _nonnegative(transition_sensitivity, "transition_sensitivity")
    reward = _nonnegative(reward_bound, "reward_bound")
    displacement = residual / (1.0 - modulus)
    welfare_lipschitz = _welfare_lipschitz(beta, utility, transition, reward)
    return FrozenCounterfactualBounds(
        residual_norm=residual,
        contraction=modulus,
        discount=beta,
        utility_sensitivity=utility,
        transition_sensitivity=transition,
        reward_bound=reward,
        displacement_bound=displacement,
        welfare_lipschitz=welfare_lipschitz,
        welfare_bound=welfare_lipschitz * displacement,
    )


def linear_center_displacement(
    average_jacobian: NDArray[np.floating],
    residual: NDArray[np.floating],
) -> CenterDisplacementCertificate:
    """Evaluate Equation 3.1 when the supplied averaged Jacobian is contractive."""

    jacobian = np.asarray(average_jacobian, dtype=float)
    residual_vector = _vector(residual)
    if jacobian.ndim != 2 or jacobian.shape[0] != jacobian.shape[1]:
        raise ValueError("average_jacobian must be square")
    if not np.all(np.isfinite(jacobian)):
        raise ValueError("average_jacobian must be finite")
    if jacobian.shape[0] != residual_vector.size:
        raise ValueError("average_jacobian and residual dimensions must match")
    operator_norm = float(np.linalg.norm(jacobian, ord=2))
    if operator_norm >= 1.0:
        raise ValueError("average_jacobian operator norm must be below one")
    displacement = np.linalg.solve(np.eye(jacobian.shape[0]) - jacobian, residual_vector)
    displacement_norm = float(np.linalg.norm(displacement))
    return CenterDisplacementCertificate(
        average_jacobian=_readonly(jacobian),
        residual=_readonly(residual_vector),
        displacement=_readonly(displacement),
        operator_norm=operator_norm,
        displacement_norm=displacement_norm,
        norm_bound=float(np.linalg.norm(residual_vector)) / (1.0 - operator_norm),
    )


def posteriori_welfare_bounds(
    contraction: float,
    step_norm: float,
    discount: float,
    utility_sensitivity: float,
    transition_sensitivity: float,
    reward_bound: float,
) -> PosterioriWelfareBounds:
    """Evaluate Corollary A.9 from one observed outer-iteration step."""

    modulus = _contraction(contraction)
    step = _nonnegative(step_norm, "step_norm")
    distance = posteriori_distance_bound(modulus, step)
    welfare_lipschitz = _welfare_lipschitz(
        discount,
        utility_sensitivity,
        transition_sensitivity,
        reward_bound,
    )
    return PosterioriWelfareBounds(
        contraction=modulus,
        step_norm=step,
        distance_bound=distance,
        welfare_lipschitz=welfare_lipschitz,
        welfare_bound=welfare_lipschitz * distance,
    )


def fragility_upper_bound(estimation_error: float, regime_shift: float) -> float:
    """Apply Proposition 4.1's total-variation triangle decomposition."""

    estimation = _total_variation(estimation_error, "estimation_error")
    shift = _total_variation(regime_shift, "regime_shift")
    return estimation + shift


def transition_robustness_bounds(
    total_variation_radius: float,
    discount: float,
    reward_bound: float,
) -> TransitionRobustnessBounds:
    """Evaluate Proposition 4.1's fixed-policy value and robust-regret bounds."""

    delta = _total_variation(total_variation_radius, "total_variation_radius")
    beta = _discount(discount)
    reward = _nonnegative(reward_bound, "reward_bound")
    scale = beta * reward / (1.0 - beta) ** 2
    return TransitionRobustnessBounds(
        total_variation_radius=delta,
        discount=beta,
        reward_bound=reward,
        value_bound=2.0 * scale * delta,
        robust_regret_bound=4.0 * scale * delta,
    )
