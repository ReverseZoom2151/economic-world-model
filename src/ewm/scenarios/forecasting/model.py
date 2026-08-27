"""Self-fulfilling forecasting model and population learning map."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class ForecastingConfig:
    """Numerical configuration for the synthetic forecasting laboratory."""

    feedback: float
    noise_std: float = 0.35
    burn_in: int = 256
    sample_size: int = 4_096
    chains: int = 64
    seed: int = 123

    def __post_init__(self) -> None:
        if self.feedback < 0.0:
            raise ValueError("feedback must be non-negative")
        if self.noise_std <= 0.0:
            raise ValueError("noise_std must be positive")
        if self.burn_in < 0:
            raise ValueError("burn_in must be non-negative")
        if self.sample_size < 2:
            raise ValueError("sample_size must be at least two")
        if self.chains < 1:
            raise ValueError("chains must be positive")


def stationary_samples(theta: float, config: ForecastingConfig) -> NDArray[np.float64]:
    """Simulate a symmetric stationary sample using common antithetic shocks."""

    periods = int(np.ceil(config.sample_size / (2 * config.chains)))
    rng = np.random.default_rng(config.seed)
    shocks = rng.normal(size=(config.burn_in + periods, config.chains))
    positive = np.zeros(config.chains, dtype=float)
    negative = np.zeros(config.chains, dtype=float)
    samples: list[NDArray[np.float64]] = []

    for period, shock in enumerate(shocks):
        positive = (
            np.tanh(config.feedback * theta * positive) + config.noise_std * shock
        )
        negative = (
            np.tanh(config.feedback * theta * negative) - config.noise_std * shock
        )
        if period >= config.burn_in:
            samples.extend((positive.copy(), negative.copy()))

    return np.concatenate(samples)[: config.sample_size]


def population_update(theta: float, config: ForecastingConfig) -> float:
    """Return the noise-free OLS update under the deployment-induced stationary law."""

    if theta == 0.0:
        return 0.0
    states = stationary_samples(theta, config)
    conditional_mean = np.tanh(config.feedback * theta * states)
    denominator = float(np.mean(states * states))
    if denominator <= 0.0:
        raise ValueError("stationary sample has zero second moment")
    return float(np.mean(states * conditional_mean) / denominator)


def simulate_series(
    theta: float,
    config: ForecastingConfig,
    *,
    seed: int | None = None,
) -> NDArray[np.float64]:
    """Simulate one realized post-burn-in series under a deployed slope."""

    rng = np.random.default_rng(config.seed if seed is None else seed)
    total = config.burn_in + config.sample_size
    series = np.zeros(total + 1, dtype=float)
    for period in range(total):
        series[period + 1] = (
            np.tanh(config.feedback * theta * series[period])
            + config.noise_std * rng.normal()
        )
    return series[config.burn_in :]


def finite_sample_update(theta: float, config: ForecastingConfig) -> float:
    """Regress realized transitions, retaining the sampling noise absent from the population map."""

    series = simulate_series(theta, config)
    current = series[:-1]
    following = series[1:]
    denominator = float(current @ current)
    if denominator <= 0.0:
        raise ValueError("realized sample has zero second moment")
    return float((current @ following) / denominator)


@dataclass(frozen=True, slots=True)
class ForecastingProblem:
    """One-dimensional DDGE problem induced by self-fulfilling forecasting."""

    config: ForecastingConfig

    @property
    def dimension(self) -> int:
        return 1

    def update(
        self, theta: NDArray[np.floating[Any]]
    ) -> NDArray[np.floating[Any]]:
        candidate = np.asarray(theta, dtype=float)
        if candidate.shape != (1,):
            raise ValueError("forecasting theta must have shape (1,)")
        return np.array([population_update(float(candidate[0]), self.config)])
