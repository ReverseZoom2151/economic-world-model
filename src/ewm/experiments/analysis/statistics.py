"""Paired-effect summaries for synthetic experiment runners."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from statistics import NormalDist

import numpy as np
from numpy.typing import NDArray
from scipy.stats import t


@dataclass(frozen=True, slots=True)
class PairedEstimate:
    """Mean paired difference with a normal-approximation interval."""

    mean_difference: float
    standard_error: float
    interval_low: float
    interval_high: float
    sample_size: int


@dataclass(frozen=True, slots=True)
class RobustPairedEstimate:
    """Student-t paired estimate with a paired-bootstrap robustness interval."""

    mean_difference: float
    standard_error: float
    student_t_interval_low: float
    student_t_interval_high: float
    bootstrap_interval_low: float
    bootstrap_interval_high: float
    sample_size: int
    degrees_of_freedom: int
    t_statistic: float | None
    p_value: float
    standardized_effect: float | None
    confidence: float
    bootstrap_resamples: int
    bootstrap_seed: int
    degenerate_differences: bool
    interval_method: str = "student_t"
    bootstrap_method: str = "paired_percentile"


@dataclass(frozen=True, slots=True)
class BinomialEstimate:
    """Binomial rate with a Wilson score interval."""

    successes: int
    trials: int
    rate: float
    interval_low: float
    interval_high: float
    confidence: float
    method: str = "wilson"


@dataclass(frozen=True, slots=True)
class HolmCorrection:
    """Family-wise Holm correction in the hypotheses' original order."""

    adjusted_p_values: tuple[float, ...]
    rejected: tuple[bool, ...]
    alpha: float
    method: str = "holm"


def paired_estimate(
    baseline: NDArray[np.floating],
    intervention: NDArray[np.floating],
    *,
    confidence: float = 0.95,
) -> PairedEstimate:
    """Summarize common-random-number paired differences without a p-value claim."""

    base: NDArray[np.float64] = np.asarray(baseline, dtype=np.float64)
    changed: NDArray[np.float64] = np.asarray(intervention, dtype=np.float64)
    if base.ndim != 1 or changed.shape != base.shape or base.size < 2:
        raise ValueError("paired samples must be equal one-dimensional arrays of size >= 2")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie in (0, 1)")
    differences: NDArray[np.float64] = changed - base
    mean = float(np.mean(differences))
    standard_error = float(np.std(differences, ddof=1) / np.sqrt(differences.size))
    critical = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    return PairedEstimate(
        mean_difference=mean,
        standard_error=standard_error,
        interval_low=mean - critical * standard_error,
        interval_high=mean + critical * standard_error,
        sample_size=int(differences.size),
    )


def robust_paired_estimate(
    baseline: NDArray[np.floating],
    intervention: NDArray[np.floating],
    *,
    confidence: float = 0.95,
    bootstrap_resamples: int = 1_999,
    bootstrap_seed: int = 0,
) -> RobustPairedEstimate:
    """Return prespecified small-sample paired inference and bootstrap robustness."""

    differences = _paired_differences(baseline, intervention)
    _validate_confidence(confidence)
    if bootstrap_resamples < 1:
        raise ValueError("bootstrap_resamples must be positive")
    if not isinstance(bootstrap_seed, int):
        raise TypeError("bootstrap_seed must be an integer")

    sample_size = int(differences.size)
    degrees_of_freedom = sample_size - 1
    mean = float(np.mean(differences))
    standard_deviation = float(np.std(differences, ddof=1))
    standard_error = standard_deviation / sqrt(sample_size)
    critical = float(t.ppf(0.5 + confidence / 2.0, df=degrees_of_freedom))
    if standard_error == 0.0:
        t_statistic = None
        p_value = 1.0 if mean == 0.0 else 0.0
        standardized_effect = None
    else:
        t_statistic = mean / standard_error
        p_value = float(2.0 * t.sf(abs(t_statistic), df=degrees_of_freedom))
        standardized_effect = mean / standard_deviation

    rng = np.random.default_rng(bootstrap_seed)
    indices = rng.integers(
        0,
        sample_size,
        size=(bootstrap_resamples, sample_size),
    )
    bootstrap_means = np.mean(differences[indices], axis=1)
    tail_probability = (1.0 - confidence) / 2.0
    bootstrap_low, bootstrap_high = np.quantile(
        bootstrap_means,
        (tail_probability, 1.0 - tail_probability),
    )
    return RobustPairedEstimate(
        mean_difference=mean,
        standard_error=standard_error,
        student_t_interval_low=mean - critical * standard_error,
        student_t_interval_high=mean + critical * standard_error,
        bootstrap_interval_low=float(bootstrap_low),
        bootstrap_interval_high=float(bootstrap_high),
        sample_size=sample_size,
        degrees_of_freedom=degrees_of_freedom,
        t_statistic=t_statistic,
        p_value=p_value,
        standardized_effect=standardized_effect,
        confidence=confidence,
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=bootstrap_seed,
        degenerate_differences=standard_error == 0.0,
    )


def wilson_interval(
    *,
    successes: int,
    trials: int,
    confidence: float = 0.95,
) -> BinomialEstimate:
    """Return a Wilson score interval without a fragile normal approximation."""

    if trials < 1 or successes < 0 or successes > trials:
        raise ValueError(
            "successes and trials must satisfy 0 <= successes <= trials and trials > 0"
        )
    _validate_confidence(confidence)
    rate = successes / trials
    z = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    z_squared = z**2
    denominator = 1.0 + z_squared / trials
    center = (rate + z_squared / (2.0 * trials)) / denominator
    half_width = z / denominator * sqrt(
        rate * (1.0 - rate) / trials + z_squared / (4.0 * trials**2)
    )
    return BinomialEstimate(
        successes=successes,
        trials=trials,
        rate=rate,
        interval_low=max(0.0, center - half_width),
        interval_high=min(1.0, center + half_width),
        confidence=confidence,
    )


def holm_correction(
    p_values: tuple[float, ...],
    *,
    alpha: float = 0.05,
) -> HolmCorrection:
    """Control family-wise error with Holm's step-down adjustment."""

    if not p_values:
        raise ValueError("p_values must not be empty")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie in (0, 1)")
    if any(not isfinite(value) or not 0.0 <= value <= 1.0 for value in p_values):
        raise ValueError("p_values must be finite and lie in [0, 1]")

    count = len(p_values)
    ordered_indices = sorted(range(count), key=p_values.__getitem__)
    adjusted = [0.0] * count
    running_maximum = 0.0
    for rank, index in enumerate(ordered_indices):
        candidate = min(1.0, (count - rank) * p_values[index])
        running_maximum = max(running_maximum, candidate)
        adjusted[index] = running_maximum
    adjusted_values = tuple(adjusted)
    return HolmCorrection(
        adjusted_p_values=adjusted_values,
        rejected=tuple(value <= alpha for value in adjusted_values),
        alpha=alpha,
    )


def _paired_differences(
    baseline: NDArray[np.floating],
    intervention: NDArray[np.floating],
) -> NDArray[np.float64]:
    base: NDArray[np.float64] = np.asarray(baseline, dtype=np.float64)
    changed: NDArray[np.float64] = np.asarray(intervention, dtype=np.float64)
    if base.ndim != 1 or changed.shape != base.shape or base.size < 2:
        raise ValueError("paired samples must be equal one-dimensional arrays of size >= 2")
    differences: NDArray[np.float64] = changed - base
    if not bool(np.isfinite(differences).all()):
        raise ValueError("paired samples must contain only finite values")
    return differences


def _validate_confidence(confidence: float) -> None:
    if not isfinite(confidence) or not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie in (0, 1)")
