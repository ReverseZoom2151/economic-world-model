"""Read-only evaluation over immutable runtime event snapshots."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

from ..domain.records import freeze_value
from ..runtime.records.events import Event


class MeasurementStatus(StrEnum):
    """Whether an evaluation metric has evidence or remains explicitly unmeasured."""

    MEASURED = "measured"
    NOT_MEASURED = "not_measured"


@dataclass(frozen=True, slots=True)
class MetricMeasurement:
    """One scalar metric with units, sample size, and evidence provenance."""

    status: MeasurementStatus
    value: float | None
    unit: str
    sample_size: int
    provenance: str | None

    def __post_init__(self) -> None:
        if not self.unit:
            raise ValueError("measurement unit must not be empty")
        if self.status is MeasurementStatus.MEASURED:
            if self.value is None or not isfinite(self.value):
                raise ValueError("measured metric requires a finite value")
            if self.sample_size < 1:
                raise ValueError("measured metric requires a positive sample size")
            if not self.provenance:
                raise ValueError("measured metric requires provenance")
        elif self.value is not None or self.sample_size != 0 or self.provenance is not None:
            raise ValueError("not-measured metric cannot contain fabricated evidence")


@dataclass(frozen=True, slots=True)
class EvaluationLayerReport:
    """Named metrics for one of Han's five evaluation layers."""

    metrics: Mapping[str, MetricMeasurement]

    def __post_init__(self) -> None:
        if not self.metrics or any(not name for name in self.metrics):
            raise ValueError("evaluation layer metrics must not be empty")
        object.__setattr__(self, "metrics", freeze_value(self.metrics))


@dataclass(frozen=True, slots=True)
class LayeredEvaluationReport:
    """Read-only agent, environment, co-evolution, alignment, and efficiency report."""

    schema_version: str
    state_version: int
    event_count: int
    layers: Mapping[str, EvaluationLayerReport]

    def __post_init__(self) -> None:
        if self.schema_version != "ewm.layered-evaluation.v1":
            raise ValueError("unsupported layered evaluation schema")
        if self.state_version < 0 or self.event_count < 0:
            raise ValueError("evaluation versions and counts must be non-negative")
        object.__setattr__(self, "layers", freeze_value(self.layers))


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
