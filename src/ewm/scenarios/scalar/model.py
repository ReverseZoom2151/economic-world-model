"""Cong Appendix A.8 scalar behavior, belief-response, and learning loop."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite, sqrt, tanh
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ewm.equilibrium import damped_update


class ScalarLearner(StrEnum):
    """Learning maps used in Proposition A.5 and Figure 3."""

    LINEAR = "linear"
    TANH = "tanh"


@dataclass(frozen=True, slots=True)
class ScalarConfig:
    """Parameters in Cong's equation (A.1)."""

    kappa: float
    gamma: float
    learning_gain: float
    intervention: float = 0.0
    learner: ScalarLearner = ScalarLearner.TANH

    def __post_init__(self) -> None:
        values = (self.kappa, self.gamma, self.learning_gain, self.intervention)
        if not all(isfinite(value) for value in values):
            raise ValueError("scalar parameters must be finite")
        if abs(self.inner_feedback) >= 1.0:
            raise ValueError("inner feedback must satisfy abs(kappa * gamma) < 1")

    @property
    def inner_feedback(self) -> float:
        """The behavior-response feedback ``phi = kappa * gamma``."""

        return self.kappa * self.gamma

    @property
    def composite_gain(self) -> float:
        """The signed outer gain ``g = Lambda / (1 - phi)``."""

        return self.learning_gain / (1.0 - self.inner_feedback)


@dataclass(frozen=True, slots=True)
class ScalarInnerSolution:
    """Closed-form fixed-environment behavior and response."""

    behavior: float
    response: float
    sensitivity: float


@dataclass(frozen=True, slots=True)
class ScalarDisplacement:
    """Proposition A.5(i) residual and exact linear displacement."""

    residual: float
    fixed_point: float
    displacement: float


def inner_solution(theta: float, config: ScalarConfig) -> ScalarInnerSolution:
    """Solve ``a = kappa b + theta + delta`` and ``b = gamma a``."""

    if not isfinite(theta):
        raise ValueError("theta must be finite")
    denominator = 1.0 - config.inner_feedback
    behavior = (theta + config.intervention) / denominator
    return ScalarInnerSolution(
        behavior=behavior,
        response=config.gamma * behavior,
        sensitivity=1.0 / denominator,
    )


def outer_update(theta: float, config: ScalarConfig) -> float:
    """Apply the linear or saturating learner to equilibrium-generated behavior."""

    behavior = inner_solution(theta, config).behavior
    if config.learner is ScalarLearner.LINEAR:
        return config.learning_gain * behavior
    return config.learning_gain * tanh(behavior)


def outer_derivative(theta: float, config: ScalarConfig) -> float:
    """Return the analytical derivative of the outer learning map."""

    if config.learner is ScalarLearner.LINEAR:
        return config.composite_gain
    value = tanh(inner_solution(theta, config).behavior)
    return config.composite_gain * (1.0 - value * value)


def linear_displacement(config: ScalarConfig) -> ScalarDisplacement:
    """Evaluate the exact intervention displacement in Proposition A.5(i)."""

    if config.learner is not ScalarLearner.LINEAR:
        raise ValueError("linear displacement requires the linear learner")
    gain = config.composite_gain
    if abs(gain) >= 1.0:
        raise ValueError("linear displacement requires abs(composite_gain) < 1")
    residual = gain * config.intervention
    fixed_point = residual / (1.0 - gain)
    return ScalarDisplacement(
        residual=residual,
        fixed_point=fixed_point,
        displacement=fixed_point,
    )


def near_onset_expansion(config: ScalarConfig) -> float:
    """Return Proposition A.5(ii)'s positive-root expansion as ``g`` approaches one."""

    if config.learner is not ScalarLearner.TANH:
        raise ValueError("near-onset expansion requires the saturating learner")
    if config.intervention != 0.0:
        raise ValueError("near-onset expansion requires zero intervention")
    gain = config.composite_gain
    if config.learning_gain <= 0.0 or gain <= 1.0:
        raise ValueError("near-onset expansion requires positive composite gain above one")
    return (1.0 - config.inner_feedback) * sqrt(3.0 * (gain - 1.0) / gain)


def retraining_path(
    initial_theta: float,
    config: ScalarConfig,
    *,
    rounds: int,
    damping: float = 1.0,
) -> tuple[float, ...]:
    """Simulate raw or damped scalar retraining for a declared number of rounds."""

    if rounds < 0:
        raise ValueError("rounds must be non-negative")
    theta = float(initial_theta)
    path = [theta]
    for _round in range(rounds):
        raw = outer_update(theta, config)
        theta = float(
            damped_update(np.array([theta]), np.array([raw]), damping)[0]
        )
        path.append(theta)
    return tuple(path)


@dataclass(frozen=True, slots=True)
class ScalarProblem:
    """One-dimensional DDGE problem for the scalar laboratory."""

    config: ScalarConfig

    @property
    def dimension(self) -> int:
        return 1

    def update(
        self, theta: NDArray[np.floating[Any]]
    ) -> NDArray[np.floating[Any]]:
        candidate = np.asarray(theta, dtype=float)
        if candidate.shape != (1,):
            raise ValueError("scalar theta must have shape (1,)")
        return np.array([outer_update(float(candidate[0]), self.config)])


def paper_config() -> ScalarConfig:
    """Return Figure 3(c)'s self-confirming ``g = 1.6`` configuration."""

    return ScalarConfig(kappa=0.5, gamma=1.0, learning_gain=0.8)
