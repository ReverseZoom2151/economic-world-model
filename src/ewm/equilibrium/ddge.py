"""DDGE-specific wrappers around the generic multistart solver."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
from numpy.typing import NDArray

from ewm.core import DDGEProblem, DDGEResult

from .fixed_point import FixedPointConfig, solve_multistart


def solve_ddge(
    problem: DDGEProblem,
    initializations: Iterable[NDArray[np.floating]],
    config: FixedPointConfig | None = None,
) -> DDGEResult:
    """Solve ``theta = L(D(E(theta), theta))`` from declared starts."""

    starts = tuple(np.asarray(initial, dtype=float) for initial in initializations)
    if not starts:
        raise ValueError("at least one initialization is required")
    if any(start.shape != (problem.dimension,) for start in starts):
        raise ValueError("initialization dimension does not match problem.dimension")
    return solve_multistart(problem.update, starts, config)

