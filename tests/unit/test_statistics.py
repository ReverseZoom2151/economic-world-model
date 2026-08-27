from __future__ import annotations

from math import sqrt

import numpy as np
import pytest
from scipy.stats import t

from ewm.experiments import (
    holm_correction,
    paired_estimate,
    robust_paired_estimate,
    wilson_interval,
)


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


def test_robust_paired_estimate_uses_student_t_and_paired_bootstrap() -> None:
    baseline = np.array([100.0, 200.0, 300.0, 400.0])
    differences = np.array([-1.0, 0.0, 1.0, 2.0])
    confidence = 0.95
    resamples = 999
    seed = 123

    estimate = robust_paired_estimate(
        baseline,
        baseline + differences,
        confidence=confidence,
        bootstrap_resamples=resamples,
        bootstrap_seed=seed,
    )

    standard_deviation = float(np.std(differences, ddof=1))
    standard_error = standard_deviation / sqrt(differences.size)
    critical = float(t.ppf(0.5 + confidence / 2.0, df=differences.size - 1))
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, differences.size, size=(resamples, differences.size))
    bootstrap_means = np.mean(differences[indices], axis=1)
    expected_bootstrap = np.quantile(
        bootstrap_means,
        ((1.0 - confidence) / 2.0, 1.0 - (1.0 - confidence) / 2.0),
    )

    assert estimate.mean_difference == pytest.approx(0.5)
    assert estimate.standard_error == pytest.approx(standard_error)
    assert estimate.student_t_interval_low == pytest.approx(
        0.5 - critical * standard_error
    )
    assert estimate.student_t_interval_high == pytest.approx(
        0.5 + critical * standard_error
    )
    assert estimate.bootstrap_interval_low == pytest.approx(expected_bootstrap[0])
    assert estimate.bootstrap_interval_high == pytest.approx(expected_bootstrap[1])
    assert estimate.standardized_effect == pytest.approx(0.5 / standard_deviation)
    assert estimate.degrees_of_freedom == 3
    assert estimate.bootstrap_resamples == resamples
    assert estimate.bootstrap_seed == seed
    assert estimate.degenerate_differences is False
    assert estimate.interval_method == "student_t"
    assert estimate.bootstrap_method == "paired_percentile"


def test_robust_paired_estimate_marks_zero_variance_effect_as_undefined() -> None:
    baseline = np.array([1.0, 2.0, 3.0])

    estimate = robust_paired_estimate(
        baseline,
        baseline + 1.0,
        bootstrap_resamples=99,
        bootstrap_seed=1,
    )

    assert estimate.standardized_effect is None
    assert estimate.t_statistic is None
    assert estimate.p_value == 0.0
    assert estimate.degenerate_differences is True


def test_wilson_interval_reports_finite_small_sample_bounds() -> None:
    estimate = wilson_interval(successes=3, trials=4)
    z = 1.959963984540054
    denominator = 1.0 + z**2 / 4.0
    center = (3.0 / 4.0 + z**2 / 8.0) / denominator
    half_width = z / denominator * sqrt(3.0 / 16.0 / 4.0 + z**2 / 64.0)

    assert estimate.rate == pytest.approx(0.75)
    assert estimate.interval_low == pytest.approx(center - half_width)
    assert estimate.interval_high == pytest.approx(center + half_width)
    assert estimate.method == "wilson"


@pytest.mark.parametrize(
    ("successes", "trials"),
    ((-1, 4), (5, 4), (0, 0)),
)
def test_wilson_interval_rejects_invalid_counts(successes: int, trials: int) -> None:
    with pytest.raises(ValueError, match="successes and trials"):
        wilson_interval(successes=successes, trials=trials)


@pytest.mark.parametrize(
    "confidence",
    (float("-inf"), -0.5, 0.0, 1.0, 1.5, float("inf"), float("nan")),
)
def test_wilson_interval_rejects_nonfinite_and_out_of_range_confidence(
    confidence: float,
) -> None:
    with pytest.raises(ValueError) as error:
        wilson_interval(successes=1, trials=2, confidence=confidence)

    assert error.value.args == ("confidence must lie in (0, 1)",)


def test_holm_correction_preserves_original_hypothesis_order() -> None:
    correction = holm_correction((0.01, 0.04, 0.03), alpha=0.05)

    assert correction.adjusted_p_values == pytest.approx((0.03, 0.06, 0.06))
    assert correction.rejected == (True, False, False)
    assert correction.method == "holm"


def test_holm_correction_is_deterministic_for_tied_p_values() -> None:
    correction = holm_correction((0.02, 0.01, 0.02), alpha=0.05)

    assert correction.adjusted_p_values == pytest.approx((0.04, 0.03, 0.04))
    assert correction.rejected == (True, True, True)


@pytest.mark.parametrize("p_values", ((float("nan"),), (-0.1,), (1.1,)))
def test_holm_correction_rejects_invalid_p_values(p_values: tuple[float, ...]) -> None:
    with pytest.raises(ValueError, match="finite and lie"):
        holm_correction(p_values)
