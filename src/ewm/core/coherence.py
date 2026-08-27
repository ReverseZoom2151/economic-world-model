"""Executable coherence checks with explicit measurement semantics."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Any


class CoherenceRelation(StrEnum):
    """A hard equality or directed inequality relation."""

    EQUAL = "equal"
    LESS_EQUAL = "less_equal"
    GREATER_EQUAL = "greater_equal"


def _validate_measurement_contract(
    *,
    name: str,
    unit: str,
    scale: float,
    tolerance: float,
) -> None:
    if not name:
        raise ValueError("coherence condition name must not be empty")
    if not unit:
        raise ValueError("coherence condition unit must not be empty")
    if not isfinite(scale) or scale <= 0.0:
        raise ValueError("coherence condition scale must be finite and positive")
    if not isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("coherence condition tolerance must be finite and non-negative")


def _measurement(value: float) -> float:
    result = float(value)
    if not isfinite(result):
        raise ValueError("coherence evaluators must return finite numeric measurements")
    return result


@dataclass(frozen=True, slots=True)
class HardCoherenceResult:
    """Atomic outcome for one hard equality or inequality."""

    name: str
    relation: CoherenceRelation
    unit: str
    scale: float
    tolerance: float
    left: float
    right: float
    signed_gap: float
    absolute_gap: float
    normalized_gap: float
    normalized_violation: float
    passed: bool


@dataclass(frozen=True, slots=True)
class HardCoherenceCondition:
    """A hard scalar condition whose tolerance has the declared unit.

    ``scale`` also has the declared unit and only normalizes diagnostics. It never
    changes the raw-unit pass threshold.
    """

    name: str
    relation: CoherenceRelation
    unit: str
    scale: float
    tolerance: float
    left: Callable[[Any], float]
    right: Callable[[Any], float]

    def __post_init__(self) -> None:
        _validate_measurement_contract(
            name=self.name,
            unit=self.unit,
            scale=self.scale,
            tolerance=self.tolerance,
        )
        if not isinstance(self.relation, CoherenceRelation):
            raise ValueError("hard coherence relation is unsupported")

    def evaluate(self, state: Any) -> HardCoherenceResult:
        """Evaluate this condition independently against one state."""

        left = _measurement(self.left(state))
        right = _measurement(self.right(state))
        signed_gap = left - right
        absolute_gap = abs(signed_gap)
        if self.relation is CoherenceRelation.EQUAL:
            raw_violation = max(absolute_gap - self.tolerance, 0.0)
        elif self.relation is CoherenceRelation.LESS_EQUAL:
            raw_violation = max(signed_gap - self.tolerance, 0.0)
        else:
            raw_violation = max(-signed_gap - self.tolerance, 0.0)
        return HardCoherenceResult(
            name=self.name,
            relation=self.relation,
            unit=self.unit,
            scale=self.scale,
            tolerance=self.tolerance,
            left=left,
            right=right,
            signed_gap=signed_gap,
            absolute_gap=absolute_gap,
            normalized_gap=signed_gap / self.scale,
            normalized_violation=raw_violation / self.scale,
            passed=raw_violation == 0.0,
        )


@dataclass(frozen=True, slots=True)
class SoftCoherenceResult:
    """A diagnostic measurement that does not decide hard coherence."""

    name: str
    unit: str
    scale: float
    tolerance: float
    left: float
    right: float
    signed_deviation: float
    absolute_deviation: float
    normalized_deviation: float
    within_tolerance: bool


@dataclass(frozen=True, slots=True)
class SoftCoherenceDiagnostic:
    """A scalar fit diagnostic kept separate from hard conditions."""

    name: str
    unit: str
    scale: float
    tolerance: float
    left: Callable[[Any], float]
    right: Callable[[Any], float]

    def __post_init__(self) -> None:
        _validate_measurement_contract(
            name=self.name,
            unit=self.unit,
            scale=self.scale,
            tolerance=self.tolerance,
        )

    def evaluate(self, state: Any) -> SoftCoherenceResult:
        """Measure fit without changing the hard-coherence verdict."""

        left = _measurement(self.left(state))
        right = _measurement(self.right(state))
        signed_deviation = left - right
        absolute_deviation = abs(signed_deviation)
        return SoftCoherenceResult(
            name=self.name,
            unit=self.unit,
            scale=self.scale,
            tolerance=self.tolerance,
            left=left,
            right=right,
            signed_deviation=signed_deviation,
            absolute_deviation=absolute_deviation,
            normalized_deviation=absolute_deviation / self.scale,
            within_tolerance=absolute_deviation <= self.tolerance,
        )


@dataclass(frozen=True, slots=True)
class CoherenceReport:
    """Per-condition hard results and separately reported soft diagnostics."""

    hard_results: tuple[HardCoherenceResult, ...]
    soft_diagnostics: tuple[SoftCoherenceResult, ...]

    @property
    def coherent(self) -> bool:
        """Whether every hard condition passes independently."""

        return all(result.passed for result in self.hard_results)

    @property
    def failed_conditions(self) -> tuple[str, ...]:
        """Hard-condition names that fail at their own tolerances."""

        return tuple(result.name for result in self.hard_results if not result.passed)


def evaluate_coherence(
    state: Any,
    *,
    hard_conditions: Sequence[HardCoherenceCondition] = (),
    soft_diagnostics: Sequence[SoftCoherenceDiagnostic] = (),
) -> CoherenceReport:
    """Evaluate declared conditions without aggregating or cancelling residuals."""

    hard = tuple(hard_conditions)
    soft = tuple(soft_diagnostics)
    names = tuple(condition.name for condition in hard) + tuple(
        diagnostic.name for diagnostic in soft
    )
    if len(names) != len(set(names)):
        raise ValueError("coherence condition names must be unique")
    return CoherenceReport(
        hard_results=tuple(condition.evaluate(state) for condition in hard),
        soft_diagnostics=tuple(diagnostic.evaluate(state) for diagnostic in soft),
    )
