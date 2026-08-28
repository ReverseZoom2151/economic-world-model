"""Provenance contracts for owned randomness."""

import numpy as np
import pytest

from ewm.core import make_rng, spawn_rngs


def test_owned_rng_is_reproducible() -> None:
    assert np.array_equal(make_rng(7).normal(size=8), make_rng(7).normal(size=8))


def test_spawned_rngs_are_reproducible_and_distinct() -> None:
    first = spawn_rngs(11, 3)
    second = spawn_rngs(11, 3)
    first_draws = [rng.integers(0, 2**31, size=8) for rng in first]
    second_draws = [rng.integers(0, 2**31, size=8) for rng in second]

    assert all(np.array_equal(a, b) for a, b in zip(first_draws, second_draws, strict=True))
    assert not np.array_equal(first_draws[0], first_draws[1])


def test_spawn_rngs_rejects_negative_count() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        spawn_rngs(1, -1)
