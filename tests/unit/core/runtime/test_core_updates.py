"""Runtime contracts for core update primitives."""

from __future__ import annotations

import numpy as np
import pytest

from ewm.core import convex_update


def test_convex_update_blends_equal_shaped_finite_values() -> None:
    current = np.array([2.0, -2.0])
    proposal = np.array([6.0, 2.0])

    updated = convex_update(current, proposal, weight=0.25)

    assert np.array_equal(updated, np.array([3.0, -1.0]))
    assert updated.dtype == np.float64


@pytest.mark.parametrize("weight", [0.0, -0.1, 1.01, np.inf, np.nan])
def test_convex_update_rejects_invalid_weight(weight: float) -> None:
    with pytest.raises(ValueError, match="weight must lie"):
        convex_update(np.array([0.0]), np.array([1.0]), weight)


def test_convex_update_rejects_shape_and_finiteness_errors() -> None:
    with pytest.raises(ValueError, match="equal shape"):
        convex_update(np.array([0.0]), np.array([1.0, 2.0]), 0.5)
    with pytest.raises(ValueError, match="finite"):
        convex_update(np.array([np.nan]), np.array([1.0]), 0.5)
    with pytest.raises(ValueError, match="finite"):
        convex_update(np.array([0.0]), np.array([np.inf]), 0.5)
