"""Integration contracts for the Han runtime protocol."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from ewm.core import (
    Action,
    EvaluationReport,
    FunctionalAgent,
    FunctionalMechanism,
    World,
)


def _world() -> World:
    agents = (
        FunctionalAgent(
            "household-0",
            lambda state, _rng: Action(
                "household-0", "add", {"amount": state["increment"]}
            ),
        ),
        FunctionalAgent(
            "firm-0",
            lambda state, _rng: Action(
                "firm-0", "add", {"amount": state["increment"] * 2.0}
            ),
        ),
    )

    def clear(state, actions, _rng):
        state["total"] += sum(action.values["amount"] for action in actions)
        state["period"] += 1
        return state, {"cleared": len(actions)}

    return World(
        initial_state=lambda _rng: {"period": 0, "total": 0.0, "increment": 1.0},
        agents=agents,
        mechanism=FunctionalMechanism(clear),
    )


def test_han_runtime_calls_are_stateful_logged_and_versioned() -> None:
    world = _world()

    state = world.reset(seed=42)
    actions = world.run_agents(state, parallel=True)
    transition = world.step(actions)
    report = world.evaluate()
    events = world.log()
    world.close()
    count_after_close = len(world.events)
    world.close()

    assert transition.state["period"] == 1
    assert transition.state["total"] == 3.0
    assert world.current_state == transition.state
    assert isinstance(report, EvaluationReport)
    assert report.state_version == 1
    assert [event.kind for event in events] == [
        "reset",
        "run_agents",
        "step",
        "evaluate",
        "log",
    ]
    assert all(event.schema_version == "ewm.event.v1" for event in world.events.snapshot())
    assert [event.sequence for event in world.events.snapshot()] == list(
        range(len(world.events))
    )
    run_event = next(event for event in events if event.kind == "run_agents")
    assert run_event.payload["parallel_requested"] is True
    assert run_event.payload["parallel_executed"] is False
    assert len(world.events) == count_after_close


def test_evaluate_is_read_only_except_for_its_audit_event() -> None:
    world = _world()
    state = world.reset(seed=7)
    transition = world.step(world.run_agents(state))
    before = deepcopy(dict(transition.state))
    version = world.state_version

    first = world.evaluate()
    second = world.evaluate()

    assert dict(world.current_state) == before
    assert world.state_version == version
    assert first.metrics == second.metrics
    assert first.event_count + 1 == second.event_count


def test_backward_compatible_step_state_actions_form_remains_available() -> None:
    world = _world()
    state = {"period": 4, "total": 2.0, "increment": 1.0}
    actions = (Action("external", "add", {"amount": 5.0}),)

    transition = world.step(state, actions)

    assert state == {"period": 4, "total": 2.0, "increment": 1.0}
    assert transition.state["period"] == 5
    assert transition.state["total"] == 7.0
    assert world.current_state == transition.state


def test_stateful_calls_enforce_reset_and_close_lifecycle() -> None:
    world = _world()

    with pytest.raises(RuntimeError, match="reset"):
        world.step(())
    world.reset(seed=0)
    world.close()
    with pytest.raises(RuntimeError, match="closed"):
        world.run_agents(world.current_state)
    with pytest.raises(RuntimeError, match="closed"):
        world.reset(seed=0)


def test_protocol_does_not_draw_randomness_during_evaluation() -> None:
    def random_world() -> World:
        return World(
            initial_state=lambda _rng: {"value": 0.0},
            agents=(
                FunctionalAgent(
                    "agent-0",
                    lambda _state, rng: Action(
                        "agent-0", "draw", {"value": float(rng.normal())}
                    ),
                ),
            ),
            mechanism=FunctionalMechanism(
                lambda state, _actions, _rng: (state, {})
            ),
        )

    evaluated = random_world()
    control = random_world()
    evaluated_state = evaluated.reset(seed=11)
    control_state = control.reset(seed=11)
    _ = evaluated.evaluate()

    evaluated_action = evaluated.run_agents(evaluated_state)[0]
    control_action = control.run_agents(control_state)[0]

    assert np.isclose(
        evaluated_action.values["value"], control_action.values["value"]
    )
