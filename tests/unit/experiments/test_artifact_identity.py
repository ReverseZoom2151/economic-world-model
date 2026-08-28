"""Unit contracts for experiment artifact identities."""

from __future__ import annotations

import math

import numpy as np
import pytest
from ewm.experiments.identity import canonical_identity, identity_sha256


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, np.float64(math.nan)])
def test_canonical_identity_rejects_non_finite_numbers(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        canonical_identity({"parameter": value})


@pytest.mark.parametrize(
    "value",
    [
        {1: "integer key"},
        {"negative_zero": -0.0},
        {"array": np.asarray([object()])},
        {"unsupported": object()},
    ],
)
def test_canonical_identity_rejects_ambiguous_values(value: object) -> None:
    with pytest.raises((TypeError, ValueError), match="identity"):
        canonical_identity(value)


def test_identity_digest_is_canonical_and_full_length() -> None:
    first = canonical_identity({"z": np.int64(2), "nested": {"b": True, "a": 1.5}})
    second = canonical_identity({"nested": {"a": 1.5, "b": True}, "z": 2})

    assert first == second
    assert identity_sha256(first) == identity_sha256(second)
    assert len(identity_sha256(first)) == 64
