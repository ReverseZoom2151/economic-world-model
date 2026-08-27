"""Deterministic event records for audit-friendly economic rollouts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .records import freeze_value

EVENT_SCHEMA_VERSION = "ewm.event.v1"


@dataclass(frozen=True, slots=True)
class Event:
    """One ordered runtime event."""

    sequence: int
    kind: str
    payload: Mapping[str, Any]
    schema_version: str = EVENT_SCHEMA_VERSION
    state_version: int | None = None

    def __post_init__(self) -> None:
        if not self.kind:
            raise ValueError("event kind must not be empty")
        if self.schema_version != EVENT_SCHEMA_VERSION:
            raise ValueError(f"unsupported event schema {self.schema_version!r}")
        if self.state_version is not None and self.state_version < 0:
            raise ValueError("event state_version must be non-negative")
        object.__setattr__(self, "payload", freeze_value(self.payload))


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
        )
        self._events.append(event)
        return event

    def snapshot(self) -> tuple[Event, ...]:
        return tuple(self._events)

    def __len__(self) -> int:
        return len(self._events)
