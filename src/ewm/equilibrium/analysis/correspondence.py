"""Verification tools for set-valued inner equilibria and DDGE candidates."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from math import isfinite

import numpy as np
from numpy.typing import NDArray

from ewm.core import ConsistencyCheck, DDGECandidate, DDGEConsistencyCertificate

ResidualFunction = Callable[[DDGECandidate], float]
LearningFunction = Callable[[DDGECandidate], NDArray[np.floating]]


def _zero_residual(_candidate: DDGECandidate) -> float:
    return 0.0


def _vector(value: NDArray[np.floating]) -> NDArray[np.float64]:
    vector = np.asarray(value, dtype=float)
    if vector.ndim != 1 or not np.all(np.isfinite(vector)):
        raise ValueError("learned parameters must be a finite one-dimensional array")
    return vector


class EquilibriumCorrespondence:
    """Enumerate finite inner sets and certify all DDGE consistency conditions.

    Callers provide residual functions derived from their economic model. This class verifies a
    finite declared candidate set. It is not a generic Kakutani correspondence solver.
    """

    def __init__(
        self,
        *,
        behavioral_residual: ResidualFunction,
        belief_residual: ResidualFunction,
        learning_update: LearningFunction,
        feasibility_residual: ResidualFunction | None = None,
        aggregate_residual: ResidualFunction | None = None,
        tolerance: float = 1e-8,
    ) -> None:
        if not isfinite(tolerance) or tolerance < 0.0:
            raise ValueError("tolerance must be finite and non-negative")
        self._behavioral_residual = behavioral_residual
        self._belief_residual = belief_residual
        self._feasibility_residual = feasibility_residual or _zero_residual
        self._aggregate_residual = aggregate_residual or _zero_residual
        self._learning_update = learning_update
        self._tolerance = tolerance

    @property
    def tolerance(self) -> float:
        return self._tolerance

    def _check(
        self,
        component: str,
        residual_function: ResidualFunction,
        candidate: DDGECandidate,
    ) -> ConsistencyCheck:
        return ConsistencyCheck(
            component=component,
            residual=float(residual_function(candidate)),
            tolerance=self._tolerance,
        )

    def _inner_checks(self, candidate: DDGECandidate) -> tuple[ConsistencyCheck, ...]:
        return (
            self._check("behavioral_optimality", self._behavioral_residual, candidate),
            self._check("belief_consistency", self._belief_residual, candidate),
            self._check("feasibility", self._feasibility_residual, candidate),
            self._check("aggregate_consistency", self._aggregate_residual, candidate),
        )

    def inner_equilibria(
        self,
        theta: NDArray[np.floating],
        candidates: Iterable[DDGECandidate],
    ) -> tuple[DDGECandidate, ...]:
        """Return all declared candidates satisfying the fixed-environment conditions."""

        fixed_theta = _vector(theta)
        equilibria: list[DDGECandidate] = []
        for candidate in candidates:
            if candidate.theta.shape != fixed_theta.shape or not np.array_equal(
                candidate.theta, fixed_theta
            ):
                raise ValueError("candidate theta must equal the fixed-environment theta")
            if all(check.passed for check in self._inner_checks(candidate)):
                equilibria.append(candidate)
        return tuple(equilibria)

    def select(
        self,
        theta: NDArray[np.floating],
        candidates: Iterable[DDGECandidate],
    ) -> DDGECandidate:
        """Return a unique selector or surface empty/set-valued inner equilibrium."""

        equilibria = self.inner_equilibria(theta, candidates)
        if not equilibria:
            raise ValueError("inner equilibrium set is empty")
        if len(equilibria) > 1:
            raise ValueError(f"inner equilibrium is set-valued with {len(equilibria)} candidates")
        return equilibria[0]

    def verify(self, candidate: DDGECandidate) -> DDGEConsistencyCertificate:
        """Certify inner consistency and the outer learning equation separately."""

        learned_theta = _vector(self._learning_update(candidate))
        if learned_theta.shape != candidate.theta.shape:
            raise ValueError("learning update changed candidate theta dimension")
        learning = ConsistencyCheck(
            component="learning",
            residual=float(np.linalg.norm(learned_theta - candidate.theta)),
            tolerance=self._tolerance,
        )
        return DDGEConsistencyCertificate(
            candidate=candidate,
            checks=(*self._inner_checks(candidate), learning),
        )
