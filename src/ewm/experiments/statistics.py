"""Small paired-effect summaries used by synthetic experiment runners."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class PairedEstimate:
    """Mean paired difference with a normal-approximation interval."""

    mean_difference: float
    standard_error: float
    interval_low: float
    interval_high: float
    sample_size: int


def paired_estimate(
    baseline: NDArray[np.floating],
    intervention: NDArray[np.floating],
    *,
    confidence: float = 0.95,
) -> PairedEstimate:
    """Summarize common-random-number paired differences without a p-value claim."""

    base = np.asarray(baseline, dtype=float)
    changed = np.asarray(intervention, dtype=float)
    if base.ndim != 1 or changed.shape != base.shape or base.size < 2:
        raise ValueError("paired samples must be equal one-dimensional arrays of size >= 2")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie in (0, 1)")
    differences = changed - base
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
