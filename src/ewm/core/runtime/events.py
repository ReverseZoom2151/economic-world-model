"""Deterministic event records for auditable economic rollouts."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, overload

from ..domain.records import freeze_value
from ..provenance.serialization import content_digest

EVENT_SCHEMA_VERSION = "ewm.event.v1"
EVENT_GENESIS_HASH = "0" * 64


def _valid_digest(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _event_digest(event: Event) -> str:
    return content_digest(
        {
            "kind": event.kind,
            "payload": event.payload,
            "previous_hash": event.previous_hash,
            "schema_version": event.schema_version,
            "sequence": event.sequence,
            "state_version": event.state_version,
        }
    )


@dataclass(frozen=True, slots=True)
class Event:
    """One ordered runtime event."""

    sequence: int
    kind: str
    payload: Mapping[str, Any]
    schema_version: str = EVENT_SCHEMA_VERSION
    state_version: int | None = None
    previous_hash: str = EVENT_GENESIS_HASH
    event_hash: str = ""

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise ValueError("event sequence must be non-negative")
        if not self.kind:
            raise ValueError("event kind must not be empty")
        if self.schema_version != EVENT_SCHEMA_VERSION:
            raise ValueError(f"unsupported event schema {self.schema_version!r}")
        if self.state_version is not None and self.state_version < 0:
            raise ValueError("event state_version must be non-negative")
        if not _valid_digest(self.previous_hash):
            raise ValueError("event previous_hash must be a SHA-256 digest")
        object.__setattr__(self, "payload", freeze_value(self.payload))
        if not self.event_hash:
            object.__setattr__(self, "event_hash", _event_digest(self))
        elif not _valid_digest(self.event_hash):
            raise ValueError("event event_hash must be a SHA-256 digest")


def verify_event_chain(events: tuple[Event, ...]) -> str:
    """Validate sequence, links, and content hashes and return the chain head."""

    previous = EVENT_GENESIS_HASH
    for sequence, event in enumerate(events):
        if event.sequence != sequence:
            raise ValueError("event chain has a non-contiguous sequence")
        if event.previous_hash != previous:
            raise ValueError("event chain previous hash does not match")
        if event.event_hash != _event_digest(event):
            raise ValueError("event hash does not match payload; log may be tampered")
        previous = event.event_hash
    return previous


class EventLog:
    """Append-only in-memory log with immutable snapshots."""

    def __init__(self) -> None:
        self._events: list[Event] = []

    def append(
        self,
        kind: str,
        payload: Mapping[str, Any],
        *,
        state_version: int | None = None,
    ) -> Event:
        event = Event(
            sequence=len(self._events),
            kind=kind,
            payload=payload,
            state_version=state_version,
            previous_hash=(
                self._events[-1].event_hash if self._events else EVENT_GENESIS_HASH
            ),
        )
        self._events.append(event)
        return event

    def snapshot(self) -> tuple[Event, ...]:
        return tuple(self._events)

    def __len__(self) -> int:
        return len(self._events)


class EventLogView:
    """Read-only live view of one append-only event log."""

    __slots__ = ("_log",)

    def __init__(self, log: EventLog) -> None:
        self._log = log

    def snapshot(self) -> tuple[Event, ...]:
        return self._log.snapshot()

    def __len__(self) -> int:
        return len(self._log)

    def __iter__(self) -> Iterator[Event]:
        return iter(self._log.snapshot())

    @overload
    def __getitem__(self, index: int) -> Event: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[Event, ...]: ...

    def __getitem__(self, index: int | slice) -> Event | tuple[Event, ...]:
        return self._log.snapshot()[index]
