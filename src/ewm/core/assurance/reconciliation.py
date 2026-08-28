"""Next-state reconciliation from Cong Proposition A.3."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..domain.records import Action

ReconciliationRule = Callable[[Any, tuple[Action, ...], Any, Any], Any]
StateFeasibilityRule = Callable[[Any], bool]


@dataclass(frozen=True, slots=True)
class FunctionalStateReconciler:
    """Callable-backed projection with an explicit feasible-state predicate."""

    name: str
    rule: ReconciliationRule
    feasibility: StateFeasibilityRule

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("state reconciler name must not be empty")

    def reconcile(
        self,
        state: Any,
        actions: tuple[Action, ...],
        intervention: Any,
        candidate_state: Any,
    ) -> Any:
        return self.rule(state, tuple(actions), intervention, candidate_state)

    def is_feasible(self, state: Any) -> bool:
        return bool(self.feasibility(state))
