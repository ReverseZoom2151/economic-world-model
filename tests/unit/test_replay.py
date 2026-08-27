from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
from typing import Any

import numpy as np
import pytest

import ewm
from ewm.core import (
    EVENT_SCHEMA_VERSION,
    Action,
    CanonicalStateCodec,
    Event,
    EventLog,
    EventLogView,
    FunctionalAgent,
    FunctionalConstraint,
    FunctionalMechanism,
    ReplayBundle,
    RuntimeAdapter,
    RuntimeAdapterRegistry,
    World,
    WorldBindings,
    WorldSpecification,
    state_digest,
    verify_event_chain,
)

MECHANISM_KEY = (
    "batch_clearing",
    "uniform_clearing",
    "cash_asset_delivery",
)


def _specification() -> WorldSpecification:
    participant = ewm.agent(
        role="trader",
        objective="Submit reproducible stochastic additions.",
        state_variables=["balance"],
        information_channels={"public": ["total"]},
        action_space=["add"],
        constraints=["non_negative"],
        count=2,
    )
    environment = ewm.environment(
        state=ewm.state(
            variables={"total": 0.0},
            accounts={"trader": {"balance": 10.0}},
        ),
        constraints=ewm.constraints(rules=["non_negative"]),
        scheduler=ewm.scheduler(policy="submission_order"),
        mechanism=ewm.mechanism(
            type=MECHANISM_KEY[0],
            participants=["trader"],
            input_actions=["add"],
            pricing_rule=MECHANISM_KEY[1],
            settlement_rule=MECHANISM_KEY[2],
        ),
    )
    specification = ewm.make(
        "replay-fixture",
        agents=[participant],
        environment=environment,
    )
    assert isinstance(specification, WorldSpecification)
    return specification


def _bindings() -> WorldBindings:
    def agent_factory(_specification, agent_id):
        return FunctionalAgent(
            agent_id,
            lambda _state, rng: Action(
                agent_id,
                "add",
                {"amount": float(rng.uniform(0.1, 1.0))},
            ),
        )

    return WorldBindings(
        initial_state=lambda rng: {
            "total": 0.0,
            "initial_draw": float(rng.normal()),
        },
        agent_factories={"trader": agent_factory},
        constraints={
            "non_negative": FunctionalConstraint(
                "non_negative",
                lambda _state, action: (
                    "amount must be non-negative"
                    if float(action.values["amount"]) < 0.0
                    else None
                ),
            )
        },
    )


def _registry() -> RuntimeAdapterRegistry:
    def mechanism_factory(_specification, _options):
        def clear(state: dict[str, Any], actions, rng):
            shock = float(rng.normal())
            state["total"] += shock + sum(
                float(action.values["amount"]) for action in actions
            )
            return state, {"shock": shock, "accepted": len(actions)}

        return FunctionalMechanism(clear)

    return RuntimeAdapterRegistry(
        (
            RuntimeAdapter(
                adapter_id="replay_v1",
                mechanism_key=MECHANISM_KEY,
                mechanism_factory=mechanism_factory,
            ),
        )
    )


def _world() -> World:
    return ewm.compile_world(
        _specification(),
        bindings=_bindings(),
        adapters=_registry(),
    )


def test_event_v1_hash_chain_is_canonical_and_log_view_is_read_only() -> None:
    first = Event(
        0,
        "reset",
        {"z": 2, "a": 1},
        EVENT_SCHEMA_VERSION,
        0,
    )
    equivalent = Event(
        0,
        "reset",
        {"a": 1, "z": 2},
        EVENT_SCHEMA_VERSION,
        0,
    )
    log = EventLog()
    appended_first = log.append("reset", {"z": 2, "a": 1}, state_version=0)
    appended_second = log.append("step", {"value": np.int64(3)}, state_version=1)
    view = EventLogView(log)

    assert first.event_hash == equivalent.event_hash
    assert appended_second.previous_hash == appended_first.event_hash
    assert verify_event_chain(view.snapshot()) == appended_second.event_hash
    assert tuple(view) == view.snapshot()
    assert len(view) == 2
    assert not hasattr(view, "append")


def test_canonical_state_codec_round_trips_supported_state_values() -> None:
    codec = CanonicalStateCodec()
    state = {
        "array": np.array([[1.0, 2.0]], dtype=np.float64),
        "history": (1, 2),
        "owners": frozenset({"b", "a"}),
    }

    encoded = codec.encode(state)
    restored = codec.decode(encoded)

    assert codec.codec_id == "ewm.state.canonical.v1"
    assert isinstance(encoded, MappingProxyType)
    assert np.array_equal(restored["array"], state["array"])
    assert restored["history"] == (1, 2)
    assert restored["owners"] == frozenset({"a", "b"})
    assert state_digest(codec, restored) == state_digest(codec, state)


def test_compiled_step_event_contains_complete_transition_provenance() -> None:
    world = _world()
    before = world.reset(seed=5)
    submitted = (
        Action("trader-1", "add", {"amount": -1.0}),
        Action("trader-0", "add", {"amount": 2.0}),
    )

    transition = world.step(submitted)
    event = world.events.snapshot()[-1]

    assert event.payload["submitted_actions"] == (
        {
            "agent_id": "trader-1",
            "kind": "add",
            "values": {"amount": -1.0},
        },
        {
            "agent_id": "trader-0",
            "kind": "add",
            "values": {"amount": 2.0},
        },
    )
    assert event.payload["accepted_actions"] == (
        {
            "agent_id": "trader-0",
            "kind": "add",
            "values": {"amount": 2.0},
        },
    )
    assert event.payload["violations"] == (
        {
            "agent_id": "trader-1",
            "constraint": "non_negative",
            "reason": "amount must be non-negative",
        },
    )
    assert event.payload["outcomes"] == transition.outcomes
    assert event.payload["diagnostics"] == transition.diagnostics
    assert event.payload["before_state_digest"] == state_digest(
        world.state_codec,
        before,
    )
    assert event.payload["after_state_digest"] == state_digest(
        world.state_codec,
        transition.state,
    )


def test_compiled_world_replays_stochastic_agent_and_mechanism_operations() -> None:
    original = _world()
    state = original.reset(seed=29)
    for _ in range(2):
        actions = original.run_agents(state)
        state = original.step(actions).state
    original.evaluate()
    original.log()

    bundle = ewm.export_replay(original)
    replayed = _world()
    report = ewm.replay_world(replayed, bundle)

    assert isinstance(bundle, ReplayBundle)
    assert report.matched
    assert report.replayed_event_count == len(bundle.events)
    assert report.replayed_step_count == 2
    assert report.final_state_digest == bundle.manifest.final_state_digest
    assert replayed.current_state == original.current_state
    assert replayed.events.snapshot()[-1].event_hash == bundle.manifest.event_chain_hash


def test_replay_rejects_tampered_event_payload_before_execution() -> None:
    original = _world()
    original.reset(seed=11)
    original.step((Action("trader-0", "add", {"amount": 1.0}),))
    bundle = ewm.export_replay(original)
    step_event = bundle.events[-1]
    payload = dict(step_event.payload)
    payload["outcomes"] = {"shock": 999.0, "accepted": 1}
    tampered_event = replace(step_event, payload=payload)
    tampered = ReplayBundle(
        manifest=bundle.manifest,
        events=(*bundle.events[:-1], tampered_event),
    )
    target = _world()

    with pytest.raises(ValueError, match=r"event hash|tampered"):
        ewm.replay_world(target, tampered)

    with pytest.raises(RuntimeError, match="compiled replayable world"):
        ewm.export_replay(
            World(
                initial_state=lambda _rng: {"total": 0.0},
                agents=(),
                mechanism=FunctionalMechanism(
                    lambda state, _actions, _rng: (state, {})
                ),
            )
        )
