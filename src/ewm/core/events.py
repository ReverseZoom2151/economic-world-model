"""Deterministic event records for audit-friendly economic rollouts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .records import freeze_value


@dataclass(frozen=True, slots=True)
class Event:
    """One ordered runtime event."""

    sequence: int
    kind: str
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", freeze_value(self.payload))


class EventLog:
    """Append-only in-memory log with immutable snapshots."""

    def __init__(self) -> None:
        self._events: list[Event] = []

    def append(self, kind: str, payload: Mapping[str, Any]) -> Event:
        event = Event(sequence=len(self._events), kind=kind, payload=payload)
        self._events.append(event)
        return event

    def snapshot(self) -> tuple[Event, ...]:
        return tuple(self._events)

    def __len__(self) -> int:
        return len(self._events)

