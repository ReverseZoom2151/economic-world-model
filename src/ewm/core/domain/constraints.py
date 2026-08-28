"""Composable feasibility checks for economic actions."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from .protocols import Constraint
from .records import Action, ConstraintViolation


@dataclass(frozen=True, slots=True)
class FunctionalConstraint:
    """A named constraint backed by a predicate function."""

    name: str
    predicate: Callable[[Any, Action], str | None]

    def check(self, state: Any, action: Action) -> str | None:
        return self.predicate(state, action)


class ConstraintSet:
    """Validate actions and preserve every failed feasibility reason."""

    def __init__(self, constraints: Iterable[Constraint] = ()) -> None:
        self._constraints = tuple(constraints)

    @property
    def constraints(self) -> tuple[Constraint, ...]:
        return self._constraints

    def validate(
        self,
        state: Any,
        actions: tuple[Action, ...],
    ) -> tuple[tuple[Action, ...], tuple[ConstraintViolation, ...]]:
        accepted: list[Action] = []
        violations: list[ConstraintViolation] = []
        for action in actions:
            action_violations = []
            for constraint in self._constraints:
                reason = constraint.check(state, action)
                if reason is not None:
                    action_violations.append(
                        ConstraintViolation(
                            agent_id=action.agent_id,
                            constraint=constraint.name,
                            reason=reason,
                        )
                    )
            if action_violations:
                violations.extend(action_violations)
            else:
                accepted.append(action)
        return tuple(accepted), tuple(violations)
