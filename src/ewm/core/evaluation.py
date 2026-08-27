"""Read-only runtime evaluation over immutable event snapshots."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass

from .events import Event
from .records import freeze_value


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """A compact protocol-level report before the full layered evaluator is added."""

    schema_version: str
    state_version: int
    event_count: int
    metrics: Mapping[str, int]

    def __post_init__(self) -> None:
        object.__setattr__(self, "metrics", freeze_value(self.metrics))


def evaluate_event_log(
    events: tuple[Event, ...],
    *,
    state_version: int,
) -> EvaluationReport:
    """Summarize economic execution events without touching runtime components."""

    counts = Counter(event.kind for event in events)
    violation_count = sum(
        int(event.payload.get("violation_count", 0))
        for event in events
        if event.kind == "step"
    )
    return EvaluationReport(
        schema_version="ewm.evaluation.v1",
        state_version=state_version,
        event_count=len(events),
        metrics={
            "action_batch_count": counts["run_agents"],
            "reset_count": counts["reset"],
            "transition_count": counts["step"],
            "violation_count": violation_count,
        },
    )
