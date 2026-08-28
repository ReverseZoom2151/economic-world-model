"""Runtime contracts for controlled co-evolution."""

from __future__ import annotations

import pytest

from ewm.core import (
    Action,
    CoevolutionProposal,
    CoevolutionSpecification,
    ControlledCoevolution,
    FunctionalAgent,
    FunctionalMechanism,
    UpdateSpecification,
    World,
)


def _specification() -> CoevolutionSpecification:
    return CoevolutionSpecification(
        agent_updates=UpdateSpecification(
            targets=("belief",),
            signals=("realized_price",),
        ),
        environment_updates=UpdateSpecification(
            targets=("mechanism_parameters",),
            signals=("order_imbalance",),
        ),
    )


def _engine(*, bad_target: bool = False, excessive: bool = False) -> ControlledCoevolution:
    def propose(state, actions, next_state, _snapshot):
        del state
        belief_target = "memory" if bad_target else "belief"
        belief_delta = 0.5 if excessive else 0.1
        imbalance = sum(float(action.values["amount"]) for action in actions)
        return (
            CoevolutionProposal(
                scope="agent",
                owner_id="buyer",
                target=belief_target,
                signal="realized_price",
                signal_value=float(next_state["price"]),
                delta=belief_delta,
            ),
            CoevolutionProposal(
                scope="environment",
                owner_id=None,
                target="mechanism_parameters",
                signal="order_imbalance",
                signal_value=imbalance,
                delta=0.05,
            ),
        )

    return ControlledCoevolution(
        specification=_specification(),
        agent_components={"buyer": {"belief": 1.0}},
        environment_components={"mechanism_parameters": 0.5},
        agent_bounds={"belief": 0.2},
        environment_bounds={"mechanism_parameters": 0.1},
        proposal_rule=propose,
    )


def _world(engine: ControlledCoevolution) -> World:
    agent = FunctionalAgent(
        "buyer",
        lambda _state, _rng: Action("buyer", "order", {"amount": 2.0}),
    )

    def clear(state, actions, _rng):
        state["price"] += 0.1 * sum(action.values["amount"] for action in actions)
        return state, {"price": state["price"]}

    return World(
        initial_state=lambda _rng: {"price": 1.0},
        agents=(agent,),
        mechanism=FunctionalMechanism(clear),
        coevolution=engine,
    )


def test_world_coevolve_applies_bidirectional_bounded_updates() -> None:
    engine = _engine()
    world = _world(engine)
    state = world.reset(seed=4)
    actions = world.run_agents(state)
    transition = world.step(actions)

    report = world.coevolve(state, actions, transition.state)
    snapshot = world.coevolution_state

    assert report.before_version == 0
    assert report.after_version == 1
    assert report.stable
    assert report.max_normalized_delta == pytest.approx(0.5)
    assert report.signals == {
        "order_imbalance": 2.0,
        "realized_price": 1.2,
    }
    assert [(update.scope, update.target) for update in report.updates] == [
        ("agent", "belief"),
        ("environment", "mechanism_parameters"),
    ]
    assert snapshot.agent_components["buyer"]["belief"] == pytest.approx(1.1)
    assert snapshot.environment_components["mechanism_parameters"] == pytest.approx(
        0.55
    )
    assert world.events.snapshot()[-1].kind == "coevolve"
    assert world.events.snapshot()[-1].payload["after_version"] == 1


@pytest.mark.parametrize(
    ("bad_target", "excessive", "message"),
    [(True, False, "undeclared agent target"), (False, True, "exceeds bound")],
)
def test_invalid_proposals_are_rejected_atomically(
    bad_target: bool,
    excessive: bool,
    message: str,
) -> None:
    engine = _engine(bad_target=bad_target, excessive=excessive)
    world = _world(engine)
    state = world.reset(seed=2)
    actions = world.run_agents(state)
    transition = world.step(actions)
    before = world.coevolution_state

    with pytest.raises(ValueError, match=message):
        world.coevolve(state, actions, transition.state)

    assert world.coevolution_state == before
    assert engine.version == 0


def test_world_without_coevolution_reports_configuration_error() -> None:
    world = World(
        initial_state=lambda _rng: {"value": 0.0},
        agents=(),
        mechanism=FunctionalMechanism(lambda state, _actions, _rng: (state, {})),
    )
    state = world.reset(seed=0)

    with pytest.raises(RuntimeError, match="not configured"):
        world.coevolve(state, (), state)
