"""Assurance contracts for state reconciliation."""

from __future__ import annotations

import pytest

from ewm.core import (
    Action,
    FunctionalMechanism,
    FunctionalStateReconciler,
    World,
)


def _project_balance(
    _state: object,
    _actions: tuple[Action, ...],
    intervention: object,
    candidate: dict[str, float],
) -> dict[str, float]:
    floor = float(intervention)
    return {"balance": max(floor, candidate["balance"])}


def _world(initial_balance: float = 1.0) -> World:
    mechanism = FunctionalMechanism(
        lambda state, _actions, _rng: (
            {"balance": float(state["balance"]) - 0.75},
            {},
        )
    )
    reconciler = FunctionalStateReconciler(
        "non-negative-balance",
        _project_balance,
        lambda state: bool(float(state["balance"]) >= 0.0),
    )
    return World(
        initial_state=lambda _rng: {"balance": initial_balance},
        agents=(),
        mechanism=mechanism,
        state_reconciler=reconciler,
        intervention=0.0,
    )


def test_reconciliation_preserves_feasibility_by_induction() -> None:
    world = _world()
    state = world.reset(seed=4)

    for _ in range(5):
        transition = world.step(state, ())
        state = transition.state
        assert state["balance"] >= 0.0
        assert transition.diagnostics["state_reconciled"] is True

    assert state["balance"] == 0.0
    assert world.state_version == 5


def test_initial_state_must_be_feasible_when_reconciliation_is_configured() -> None:
    with pytest.raises(ValueError, match="initial world state"):
        _world(initial_balance=-0.1).reset(seed=4)


def test_infeasible_reconciliation_fails_before_state_commit() -> None:
    reconciler = FunctionalStateReconciler(
        "broken-projection",
        lambda _state, _actions, _intervention, candidate: candidate,
        lambda state: bool(float(state["balance"]) >= 0.0),
    )
    world = World(
        initial_state=lambda _rng: {"balance": 0.25},
        agents=(),
        mechanism=FunctionalMechanism(
            lambda _state, _actions, _rng: ({"balance": -1.0}, {})
        ),
        state_reconciler=reconciler,
    )
    initial = world.reset(seed=4)

    with pytest.raises(RuntimeError, match="infeasible next state"):
        world.step(())

    assert world.current_state == initial
    assert world.state_version == 0


def test_reconciler_requires_a_name() -> None:
    with pytest.raises(ValueError, match="name"):
        FunctionalStateReconciler("", lambda *_args: {}, lambda _state: True)
