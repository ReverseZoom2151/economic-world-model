"""Fixed-environment equilibrium solving."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, cast

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import root

from ewm.core import EquilibriumProblem, EquilibriumResult


def solve_equilibrium(
    problem: EquilibriumProblem,
    initial: NDArray[np.floating],
    *,
    method: Literal["hybr", "lm"] = "hybr",
    options: Mapping[str, Any] | None = None,
) -> EquilibriumResult:
    """Solve residual equations without conflating them with a rollout."""

    start = np.asarray(initial, dtype=float)
    if start.ndim != 1:
        raise ValueError("initial equilibrium candidate must be one-dimensional")

    def residual(candidate: NDArray[np.float64]) -> NDArray[np.float64]:
        return np.asarray(problem.residual(candidate), dtype=np.float64)

    result = root(
        residual,
        np.asarray(start, dtype=np.float64),
        method=method,
        options=cast(Any, dict(options or {})),
    )
    final_residual = np.asarray(
        problem.residual(np.asarray(result.x, dtype=float)), dtype=float
    )
    return EquilibriumResult(
        solution=np.asarray(result.x, dtype=float),
        residual_norm=float(np.linalg.norm(final_residual)),
        converged=bool(result.success),
        iterations=int(getattr(result, "nfev", 0)),
        message=str(result.message),
        diagnostics={"method": method, "status": int(result.status)},
    )
