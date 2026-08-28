"""Paper-target verification for Cong's self-fulfilling forecasting laboratory."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.optimize import brentq

from ..economy.model import (
    ForecastingConfig,
    finite_sample_retraining_path,
    population_update,
    simulate_series,
)
from ..economy.presets import paper_config, paper_finite_sample_config


@lru_cache(maxsize=16)
def paper_population_roots(config: ForecastingConfig) -> tuple[float, float, float]:
    """Bracket Figure 4's positive root and use the population map's exact odd symmetry."""

    if config.feedback <= 1.0:
        raise ValueError("paper root oracle requires feedback above one")

    def residual(theta: float) -> float:
        return population_update(theta, config) - theta

    positive = brentq(residual, 1e-8, 1.5, xtol=1e-12)
    return (-positive, 0.0, positive)


def _derivative(theta: float, config: ForecastingConfig, step: float = 1e-5) -> float:
    return (
        population_update(theta + step, config)
        - population_update(theta - step, config)
    ) / (2.0 * step)


def sample_first_autocorrelation(
    theta: float,
    config: ForecastingConfig,
    *,
    seed: int | None = None,
) -> float:
    """Estimate the first autocorrelation of a deployed model's realized aggregate."""

    series = simulate_series(theta, config, seed=seed)
    current = series[:-1]
    following = series[1:]
    if np.std(current) == 0.0 or np.std(following) == 0.0:
        return 0.0
    return float(np.corrcoef(current, following)[0, 1])


@dataclass(frozen=True, slots=True)
class ForecastingReplicationReport:
    """Figure 4 population targets and disclosed finite-sample implementation choices."""

    population_roots: tuple[float, float, float]
    fixed_point_residuals: tuple[float, float, float]
    derivatives: tuple[float, float, float]
    stable: tuple[bool, bool, bool]
    reported_outer_slope: float
    outer_slope_absolute_error: float
    momentum_autocorrelation: float
    zero_autocorrelation: float
    finite_sample_size: int
    finite_sample_rounds: int
    finite_sample_seed: int
    finite_sample_damping: float
    damping_provenance: str
    negative_path: tuple[float, ...]
    positive_path: tuple[float, ...]
    zero_path: tuple[float, ...]


@lru_cache(maxsize=16)
def paper_replication_report(
    *,
    seed: int = 42,
    rounds: int = 40,
    damping: float = 0.5,
) -> ForecastingReplicationReport:
    """Reproduce source-specified Figure 4 targets and disclose omitted path choices."""

    population = paper_config()
    finite = paper_finite_sample_config(seed=seed)
    roots = paper_population_roots(population)
    derivatives = (
        _derivative(roots[0], population),
        _derivative(roots[1], population),
        _derivative(roots[2], population),
    )
    residuals = (
        abs(population_update(roots[0], population) - roots[0]),
        abs(population_update(roots[1], population) - roots[1]),
        abs(population_update(roots[2], population) - roots[2]),
    )
    negative_path = finite_sample_retraining_path(
        -0.1,
        finite,
        rounds=rounds,
        damping=damping,
        seed=seed,
    )
    positive_path = finite_sample_retraining_path(
        0.1,
        finite,
        rounds=rounds,
        damping=damping,
        seed=seed,
    )
    zero_path = finite_sample_retraining_path(
        0.0,
        finite,
        rounds=rounds,
        damping=damping,
        seed=seed,
    )
    reported_outer_slope = 0.795
    return ForecastingReplicationReport(
        population_roots=roots,
        fixed_point_residuals=residuals,
        derivatives=derivatives,
        stable=(
            abs(derivatives[0]) < 1.0,
            abs(derivatives[1]) < 1.0,
            abs(derivatives[2]) < 1.0,
        ),
        reported_outer_slope=reported_outer_slope,
        outer_slope_absolute_error=abs(roots[2] - reported_outer_slope),
        momentum_autocorrelation=sample_first_autocorrelation(
            roots[2], finite, seed=seed
        ),
        zero_autocorrelation=sample_first_autocorrelation(0.0, finite, seed=seed),
        finite_sample_size=finite.sample_size,
        finite_sample_rounds=rounds,
        finite_sample_seed=seed,
        finite_sample_damping=damping,
        damping_provenance="package-authored: coefficient omitted from paper",
        negative_path=negative_path,
        positive_path=positive_path,
        zero_path=zero_path,
    )
