from __future__ import annotations

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from ewm.experiments import holm_correction, wilson_interval


@given(
    p_values=st.lists(
        st.floats(
            min_value=0.0,
            max_value=1.0,
            allow_nan=False,
            allow_infinity=False,
        ),
        min_size=1,
        max_size=20,
    )
)
@settings(max_examples=100, deadline=None)
def test_holm_adjustment_is_bounded_and_never_smaller(
    p_values: list[float],
) -> None:
    result = holm_correction(tuple(p_values))

    assert all(
        original <= adjusted <= 1.0
        for original, adjusted in zip(p_values, result.adjusted_p_values, strict=True)
    )
    assert result.rejected == tuple(
        adjusted <= result.alpha for adjusted in result.adjusted_p_values
    )


@given(
    trials=st.integers(min_value=1, max_value=10_000),
    success_fraction=st.floats(
        min_value=0.0,
        max_value=1.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
@settings(max_examples=100, deadline=None)
def test_wilson_interval_contains_rate_and_contracts_with_replication(
    trials: int,
    success_fraction: float,
) -> None:
    successes = min(trials, math.floor(success_fraction * trials))
    estimate = wilson_interval(successes=successes, trials=trials)
    replicated = wilson_interval(successes=successes * 2, trials=trials * 2)

    assert 0.0 <= estimate.interval_low <= 1.0
    assert 0.0 <= estimate.interval_high <= 1.0
    assert estimate.interval_low <= estimate.rate or math.isclose(
        estimate.interval_low,
        estimate.rate,
        abs_tol=1e-15,
    )
    assert estimate.rate <= estimate.interval_high or math.isclose(
        estimate.rate,
        estimate.interval_high,
        abs_tol=1e-15,
    )
    assert (
        replicated.interval_high - replicated.interval_low
        <= estimate.interval_high - estimate.interval_low
    )
