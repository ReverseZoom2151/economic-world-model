from __future__ import annotations

import numpy as np
import pytest

from ewm.experiments import paired_estimate


def test_paired_estimate_reports_effect_and_normal_interval() -> None:
    baseline = np.array([1.0, 2.0, 4.0, 8.0])
    differences = np.array([-1.0, 0.0, 1.0, 2.0])

    estimate = paired_estimate(baseline, baseline + differences)

    expected_error = np.std(differences, ddof=1) / np.sqrt(differences.size)
    assert estimate.mean_difference == pytest.approx(0.5)
    assert estimate.standard_error == pytest.approx(expected_error)
    assert estimate.interval_low == pytest.approx(0.5 - 1.959963984540054 * expected_error)
    assert estimate.interval_high == pytest.approx(0.5 + 1.959963984540054 * expected_error)
    assert estimate.sample_size == 4


@pytest.mark.parametrize(
    ("baseline", "intervention"),
    (
        (np.array([1.0]), np.array([2.0])),
        (np.array([[1.0, 2.0]]), np.array([[2.0, 3.0]])),
        (np.array([1.0, 2.0]), np.array([2.0, 3.0, 4.0])),
    ),
)
def test_paired_estimate_rejects_invalid_samples(
    baseline: np.ndarray, intervention: np.ndarray
) -> None:
    with pytest.raises(ValueError, match="equal one-dimensional arrays"):
        paired_estimate(baseline, intervention)


@pytest.mark.parametrize("confidence", (0.0, 1.0, -0.5, 1.5))
def test_paired_estimate_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence must lie"):
        paired_estimate(
            np.array([1.0, 2.0]),
            np.array([2.0, 3.0]),
            confidence=confidence,
        )
