"""Content-addressed export and deterministic command replay for compiled worlds."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from .contracts import RuntimeContract, runtime_contract_digest
from .events import EVENT_SCHEMA_VERSION, Event, verify_event_chain
from .serialization import StateCodec, action_from_data, state_digest
from .world import World

REPLAY_SCHEMA_VERSION = "ewm.replay.v1"
_REPLAYABLE_EVENTS = frozenset({"reset", "run_agents", "step", "evaluate", "log", "close"})


def _valid_digest(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


@dataclass(frozen=True, slots=True)
class ReplayManifest:
    """Compatibility and content identities for a deterministic replay bundle."""

    seed: int | None
    agent_ids: tuple[str, ...]
    state_codec: str
    runtime_contract_digest: str
    event_count: int
    event_chain_hash: str
    initial_state_digest: str
    final_state_digest: str
    schema_version: str = REPLAY_SCHEMA_VERSION
    event_schema_version: str = EVENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != REPLAY_SCHEMA_VERSION:
            raise ValueError(f"unsupported replay schema {self.schema_version!r}")
        if self.event_schema_version != EVENT_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported replay event schema {self.event_schema_version!r}"
            )
        if not self.agent_ids or len(self.agent_ids) != len(set(self.agent_ids)):
            raise ValueError("replay manifest requires unique agent identifiers")
        if not self.state_codec:
            raise ValueError("replay manifest requires a state codec")
        if self.event_count < 1:
            raise ValueError("replay manifest requires at least one event")
        for label, digest in (
            ("runtime_contract_digest", self.runtime_contract_digest),
            ("event_chain_hash", self.event_chain_hash),
            ("initial_state_digest", self.initial_state_digest),
            ("final_state_digest", self.final_state_digest),
        ):
            if not _valid_digest(digest):
                raise ValueError(f"replay manifest {label} must be a SHA-256 digest")
        object.__setattr__(self, "agent_ids", tuple(self.agent_ids))


@dataclass(frozen=True, slots=True)
class ReplayBundle:
    """Immutable event stream and manifest sufficient for deterministic replay."""

    manifest: ReplayManifest
    events: tuple[Event, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "events", tuple(self.events))


@dataclass(frozen=True, slots=True)
class ReplayReport:
    """Successful replay identities and operation counts."""

    matched: bool
    replayed_event_count: int
    replayed_step_count: int
    event_chain_hash: str
    final_state_digest: str


def _contract_digest(world: World) -> str:
    contract = world.runtime_contract
    if contract is None:
        raise RuntimeError("export requires a compiled replayable world")
    return runtime_contract_digest(contract)


def _replay_components(world: World) -> tuple[RuntimeContract, StateCodec]:
    contract = world.runtime_contract
    codec = world.state_codec
    if contract is None or codec is None:
        raise RuntimeError("operation requires a compiled replayable world")
    return contract, codec


def _validate_supported_events(events: tuple[Event, ...]) -> None:
    unsupported = sorted({event.kind for event in events}.difference(_REPLAYABLE_EVENTS))
    if unsupported:
        raise NotImplementedError(
            f"replay does not support runtime event kinds: {unsupported}"
        )
    if any(event.kind == "reset" for event in events[1:]):
        raise ValueError("replay event stream must contain exactly one leading reset")


def _event_digest(
    payload: Mapping[str, Any],
    field: str,
    *,
    event_kind: str,
) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not _valid_digest(value):
        raise ValueError(f"{event_kind} event is missing valid {field}")
    return value


def replay_bundle_from_events(world: World, events: tuple[Event, ...]) -> ReplayBundle:
    """Build a replay bundle from a fully reconstructed external event stream.

    Reset establishes both initial and provisional final state identity. Each step
    replaces the final identity. Trailing run-agents, evaluate, log, and close
    events do not change it.
    """

    _replay_components(world)
    owned_events = tuple(events)
    if not owned_events or owned_events[0].kind != "reset":
        raise ValueError("replay event stream must start with reset")
    _validate_supported_events(owned_events)
    event_chain_hash = verify_event_chain(owned_events)
    reset_payload = owned_events[0].payload

    seed_value = reset_payload.get("seed")
    if isinstance(seed_value, bool) or not isinstance(seed_value, int | type(None)):
        raise ValueError("reset event seed must be an integer or null")
    raw_agent_ids = reset_payload.get("agent_ids")
    if not isinstance(raw_agent_ids, tuple) or any(
        not isinstance(agent_id, str) for agent_id in raw_agent_ids
    ):
        raise ValueError("reset event agent_ids must be a sequence of strings")
    state_codec = reset_payload.get("state_codec")
    if not isinstance(state_codec, str) or not state_codec:
        raise ValueError("reset event is missing its state codec")
    declared_contract_digest = _event_digest(
        reset_payload,
        "runtime_contract_digest",
        event_kind="reset",
    )
    initial_state_digest = _event_digest(
        reset_payload,
        "state_digest",
        event_kind="reset",
    )
    final_state_digest = initial_state_digest
    for event in owned_events[1:]:
        if event.kind == "step":
            final_state_digest = _event_digest(
                event.payload,
                "after_state_digest",
                event_kind="step",
            )

    bundle = ReplayBundle(
        manifest=ReplayManifest(
            seed=seed_value,
            agent_ids=raw_agent_ids,
            state_codec=state_codec,
            runtime_contract_digest=declared_contract_digest,
            event_count=len(owned_events),
            event_chain_hash=event_chain_hash,
            initial_state_digest=initial_state_digest,
            final_state_digest=final_state_digest,
        ),
        events=owned_events,
    )
    _validate_bundle(world, bundle)
    return bundle


def export_replay(world: World) -> ReplayBundle:
    """Export the current compiled-world event chain as an immutable replay bundle."""

    _, codec = _replay_components(world)
    if world.state_version < 0:
        raise RuntimeError("export requires a reset compiled replayable world")
    events = world.events.snapshot()
    if not events or events[0].kind != "reset":
        raise RuntimeError("replayable event stream must start with reset")
    _validate_supported_events(events)
    bundle = replay_bundle_from_events(world, events)
    if bundle.manifest.final_state_digest != state_digest(codec, world.current_state):
        raise RuntimeError("exported event stream does not identify the current state")
    return bundle


def _validate_bundle(world: World, bundle: ReplayBundle) -> None:
    _, codec = _replay_components(world)
    manifest = bundle.manifest
    events = bundle.events
    if len(events) != manifest.event_count:
        raise ValueError("replay manifest event count does not match bundle")
    if not events or events[0].kind != "reset":
        raise ValueError("replay event stream must start with reset")
    _validate_supported_events(events)
    if verify_event_chain(events) != manifest.event_chain_hash:
        raise ValueError("replay manifest event chain hash does not match bundle")
    if tuple(world.agent_ids) != manifest.agent_ids:
        raise ValueError("replay target agent identifiers do not match manifest")
    if codec.codec_id != manifest.state_codec:
        raise ValueError("replay target state codec does not match manifest")
    if _contract_digest(world) != manifest.runtime_contract_digest:
        raise ValueError("replay target runtime contract does not match manifest")


def _assert_replayed_event(world: World, expected: Event) -> None:
    actual = world.events[-1]
    if actual.event_hash != expected.event_hash:
        raise RuntimeError(
            f"deterministic replay diverged at event {expected.sequence} "
            f"({expected.kind!r})"
        )


def replay_world(world: World, bundle: ReplayBundle) -> ReplayReport:
    """Replay recorded commands, including agent RNG consumption, into a target world."""

    _validate_bundle(world, bundle)
    manifest = bundle.manifest
    events = bundle.events
    world.reset(seed=manifest.seed)
    _assert_replayed_event(world, events[0])
    step_count = 0
    for expected in events[1:]:
        if expected.kind == "run_agents":
            world.run_agents(
                world.current_state,
                parallel=bool(expected.payload["parallel_requested"]),
            )
        elif expected.kind == "step":
            encoded = cast(
                tuple[Mapping[str, Any], ...],
                expected.payload["submitted_actions"],
            )
            world.step(tuple(action_from_data(item) for item in encoded))
            step_count += 1
        elif expected.kind == "evaluate":
            world.evaluate()
        elif expected.kind == "log":
            world.log()
        elif expected.kind == "close":
            world.close()
        else:
            raise AssertionError("validated replay event kind became unreachable")
        _assert_replayed_event(world, expected)
    _, codec = _replay_components(world)
    final_digest = state_digest(codec, world.current_state)
    actual_head = verify_event_chain(world.events.snapshot())
    if final_digest != manifest.final_state_digest:
        raise RuntimeError("deterministic replay produced a different final state")
    if actual_head != manifest.event_chain_hash:
        raise RuntimeError("deterministic replay produced a different event chain")
    return ReplayReport(
        matched=True,
        replayed_event_count=len(events),
        replayed_step_count=step_count,
        event_chain_hash=actual_head,
        final_state_digest=final_digest,
    )
