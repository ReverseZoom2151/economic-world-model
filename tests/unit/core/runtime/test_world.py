"""Runtime contracts for world execution."""

from __future__ import annotations

from typing import Any

import numpy as np
from ewm.core.agents import FunctionalAgent
from ewm.core.constraints import ConstraintSet, FunctionalConstraint

from ewm.core import Action
from ewm.core.world import World


class CapturingSumMechanism:
    def __init__(self) -> None:
        self.seen: tuple[Action, ...] = ()

    def clear(self, state: dict[str, float], actions, rng):
        self.seen = actions
        state["total"] += sum(action.values["amount"] for action in actions)
        return state, {"accepted_count": len(actions)}


def make_test_world(mechanism: CapturingSumMechanism) -> World:
    agents = (
        FunctionalAgent(
            "b", lambda _observation, rng: Action("b", "add", {"amount": rng.random()})
        ),
        FunctionalAgent(
            "a", lambda _observation, rng: Action("a", "add", {"amount": rng.random()})
        ),
    )
    constraints = ConstraintSet(
        (
            FunctionalConstraint(
                "non_negative",
                lambda _state, action: (
                    "amount must be non-negative" if action.values["amount"] < 0 else None
                ),
            ),
        )
    )
    return World(
        initial_state=lambda rng: {"total": 0.0, "draw": float(rng.normal())},
        agents=agents,
        mechanism=mechanism,
        constraints=constraints,
    )


def test_world_rejects_before_mechanism_and_logs_violation() -> None:
    mechanism = CapturingSumMechanism()
    world = make_test_world(mechanism)
    state = world.reset(seed=3)
    actions = (
        Action("accepted", "add", {"amount": 2.0}),
        Action("rejected", "add", {"amount": -1.0}),
    )

    transition = world.step(state, actions)

    assert [action.agent_id for action in mechanism.seen] == ["accepted"]
    assert transition.state["total"] == 2.0
    assert transition.violations[0].agent_id == "rejected"
    assert world.events.snapshot()[-1].payload["violation_count"] == 1


def test_world_runs_agents_in_deterministic_identifier_order() -> None:
    world = make_test_world(CapturingSumMechanism())
    first_state = world.reset(seed=7)
    first = world.run_agents(first_state)
    second_state = world.reset(seed=7)
    second = world.run_agents(second_state)

    assert [action.agent_id for action in first] == ["a", "b"]
    assert [action.values["amount"] for action in first] == [
        action.values["amount"] for action in second
    ]


def test_world_step_does_not_mutate_input_state() -> None:
    world = make_test_world(CapturingSumMechanism())
    state: dict[str, Any] = {"total": 1.0, "nested": {"values": np.array([2.0])}}

    transition = world.step(state, (Action("a", "add", {"amount": 3.0}),))

    assert state["total"] == 1.0
    assert transition.state["total"] == 4.0
    assert np.array_equal(state["nested"]["values"], np.array([2.0]))


def test_world_reset_is_seed_reproducible_and_restarts_event_sequence() -> None:
    world = make_test_world(CapturingSumMechanism())

    first = world.reset(seed=19)
    world.step(first, ())
    second = world.reset(seed=19)

    assert first["draw"] == second["draw"]
    assert len(world.events) == 1
    assert world.events.snapshot()[0].kind == "reset"
