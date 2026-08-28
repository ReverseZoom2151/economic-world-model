"""Unit contracts for external replay bundles."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ewm.core import (
    EVENT_GENESIS_HASH,
    Event,
    replay_bundle_from_events,
    replay_world,
)
from ewm.scenarios.fx import fx_world_blueprint, smoke_config


def _executed_events(*, periods: int = 2) -> tuple[Event, ...]:
    world = fx_world_blueprint(smoke_config(periods=periods)).compile()
    state = world.reset(seed=31)
    for _ in range(periods):
        state = world.step(world.run_agents(state)).state
    return world.events.snapshot()


def _rehash(
    events: tuple[Event, ...],
    *,
    reset_payload: dict[str, object] | None = None,
) -> tuple[Event, ...]:
    rebuilt: list[Event] = []
    previous_hash = EVENT_GENESIS_HASH
    for source in events:
        payload = (
            reset_payload
            if source.sequence == 0 and reset_payload is not None
            else source.payload
        )
        event = Event(
            sequence=source.sequence,
            kind=source.kind,
            payload=payload,
            schema_version=source.schema_version,
            state_version=source.state_version,
            previous_hash=previous_hash,
        )
        rebuilt.append(event)
        previous_hash = event.event_hash
    return tuple(rebuilt)


def test_external_event_bundle_replays_against_an_exact_compiled_runtime() -> None:
    events = _executed_events()
    target = fx_world_blueprint(smoke_config(periods=2)).compile()

    bundle = replay_bundle_from_events(target, events)
    report = replay_world(target, bundle)

    assert report.matched
    assert report.replayed_event_count == 5
    assert report.replayed_step_count == 2
    assert bundle.manifest.event_chain_hash == events[-1].event_hash
    assert bundle.manifest.runtime_contract_digest == events[0].payload[
        "runtime_contract_digest"
    ]


def test_external_bundle_selects_final_digest_for_reset_only_stream() -> None:
    world = fx_world_blueprint(smoke_config(periods=1)).compile()
    world.reset(seed=5)
    events = world.events.snapshot()
    target = fx_world_blueprint(smoke_config(periods=1)).compile()

    bundle = replay_bundle_from_events(target, events)
    report = replay_world(target, bundle)

    assert bundle.manifest.initial_state_digest == bundle.manifest.final_state_digest
    assert report.replayed_step_count == 0
    assert report.final_state_digest == bundle.manifest.initial_state_digest


def test_external_bundle_retains_last_step_digest_through_trailing_read_only_events() -> None:
    world = fx_world_blueprint(smoke_config(periods=1)).compile()
    state = world.reset(seed=7)
    world.step(world.run_agents(state))
    final_step_digest = world.events.snapshot()[-1].payload["after_state_digest"]
    world.evaluate()
    world.log()
    world.close()
    events = world.events.snapshot()
    target = fx_world_blueprint(smoke_config(periods=1)).compile()

    bundle = replay_bundle_from_events(target, events)
    report = replay_world(target, bundle)

    assert bundle.manifest.final_state_digest == final_step_digest
    assert report.replayed_event_count == len(events)
    assert report.replayed_step_count == 1


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("state_codec", "ewm.fx.state.v999", "state codec"),
        ("runtime_contract_digest", "f" * 64, "runtime contract"),
    ],
)
def test_external_bundle_rejects_incompatible_reset_runtime_provenance(
    field: str,
    replacement: str,
    message: str,
) -> None:
    events = _executed_events(periods=1)
    reset_payload = dict(events[0].payload)
    reset_payload[field] = replacement
    rebuilt = _rehash(events, reset_payload=reset_payload)
    target = fx_world_blueprint(smoke_config(periods=1)).compile()

    with pytest.raises(ValueError, match=message):
        replay_bundle_from_events(target, rebuilt)


def test_external_bundle_rejects_tampered_events() -> None:
    events = _executed_events(periods=1)
    tampered = (replace(events[0], event_hash="f" * 64), *events[1:])
    target = fx_world_blueprint(smoke_config(periods=1)).compile()

    with pytest.raises(ValueError, match=r"event hash|previous hash|tampered"):
        replay_bundle_from_events(target, tampered)


@pytest.mark.parametrize("kind", ["align", "coevolve"])
def test_external_bundle_rejects_unsupported_state_changing_events(kind: str) -> None:
    events = _executed_events(periods=1)
    target = fx_world_blueprint(smoke_config(periods=1)).compile()
    unsupported = Event(
        sequence=1,
        kind=kind,
        payload={},
        state_version=0,
        previous_hash=events[0].event_hash,
    )

    with pytest.raises(NotImplementedError, match=kind):
        replay_bundle_from_events(target, (events[0], unsupported))
