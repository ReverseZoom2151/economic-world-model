"""Layered EWM evaluation over immutable event snapshots."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite

from ewm.core import (
    EvaluationLayerReport,
    Event,
    LayeredEvaluationReport,
    MeasurementStatus,
    MetricMeasurement,
)

LAYER_METRICS: Mapping[str, Mapping[str, str]] = {
    "agents": {
        "action_validity_rate": "ratio",
        "role_consistency_rate": "ratio",
        "belief_calibration_error": "absolute_error",
        "behavioral_diversity": "index",
    },
    "environment": {
        "constraint_violation_rate": "ratio",
        "clearing_error": "absolute_residual",
        "accounting_error": "absolute_residual",
        "settlement_error": "absolute_residual",
    },
    "coevolution": {
        "adaptation_gain": "score_delta",
        "stability_rate": "ratio",
        "component_drift": "normalized_delta",
        "policy_change": "normalized_delta",
        "mechanism_recalibration_count": "count",
    },
    "alignment": {
        "state_error": "absolute_error",
        "trend_error": "absolute_error",
        "correction_magnitude": "absolute_delta",
    },
    "efficiency": {
        "runtime_seconds": "seconds",
        "peak_memory_bytes": "bytes",
        "agent_scaling_ratio": "runtime_ratio",
        "market_scaling_ratio": "runtime_ratio",
        "horizon_scaling_ratio": "runtime_ratio",
    },
}


@dataclass(frozen=True, slots=True)
class MetricEvidence:
    """Externally computed scalar evidence supplied to the read-only evaluator."""

    value: float
    unit: str
    provenance: str
    sample_size: int

    def __post_init__(self) -> None:
        if not isfinite(self.value):
            raise ValueError("metric evidence value must be finite")
        if not self.unit or not self.provenance:
            raise ValueError("metric evidence unit and provenance must not be empty")
        if self.sample_size < 1:
            raise ValueError("metric evidence sample_size must be positive")


def evaluate_layered(
    events: tuple[Event, ...],
    *,
    state_version: int,
    evidence: Mapping[str, Mapping[str, MetricEvidence]],
) -> LayeredEvaluationReport:
    """Combine event-derived and supplied evidence without mutating either input."""

    if state_version < 0:
        raise ValueError("state_version must be non-negative")
    unknown_layers = set(evidence).difference(LAYER_METRICS)
    if unknown_layers:
        raise ValueError(f"unknown evaluation layer: {sorted(unknown_layers)}")
    for layer, supplied in evidence.items():
        unknown_metrics = set(supplied).difference(LAYER_METRICS[layer])
        if unknown_metrics:
            raise ValueError(
                f"unknown metric for layer {layer!r}: {sorted(unknown_metrics)}"
            )

    derived = _event_measurements(tuple(events))
    layers: dict[str, EvaluationLayerReport] = {}
    for layer, metrics in LAYER_METRICS.items():
        measurements: dict[str, MetricMeasurement] = {}
        supplied = evidence.get(layer, {})
        for name, unit in metrics.items():
            automatic = derived.get((layer, name))
            manual = supplied.get(name)
            if automatic is not None and manual is not None:
                raise ValueError(
                    f"metric {layer}.{name} has both event-derived and supplied evidence"
                )
            if automatic is not None:
                measurements[name] = automatic
            elif manual is not None:
                if manual.unit != unit:
                    raise ValueError(
                        f"metric {layer}.{name} requires unit {unit!r}, "
                        f"got {manual.unit!r}"
                    )
                measurements[name] = MetricMeasurement(
                    status=MeasurementStatus.MEASURED,
                    value=manual.value,
                    unit=unit,
                    sample_size=manual.sample_size,
                    provenance=manual.provenance,
                )
            else:
                measurements[name] = MetricMeasurement(
                    status=MeasurementStatus.NOT_MEASURED,
                    value=None,
                    unit=unit,
                    sample_size=0,
                    provenance=None,
                )
        layers[layer] = EvaluationLayerReport(metrics=measurements)
    return LayeredEvaluationReport(
        schema_version="ewm.layered-evaluation.v1",
        state_version=state_version,
        event_count=len(events),
        layers=layers,
    )


def _event_measurements(
    events: tuple[Event, ...],
) -> dict[tuple[str, str], MetricMeasurement]:
    derived: dict[tuple[str, str], MetricMeasurement] = {}
    steps = tuple(event for event in events if event.kind == "step")
    submitted = sum(int(event.payload.get("submitted_count", 0)) for event in steps)
    accepted = sum(int(event.payload.get("accepted_count", 0)) for event in steps)
    violations = sum(int(event.payload.get("violation_count", 0)) for event in steps)
    if submitted > 0:
        derived[("agents", "action_validity_rate")] = _event_metric(
            accepted / submitted,
            unit="ratio",
            sample_size=submitted,
        )
        derived[("environment", "constraint_violation_rate")] = _event_metric(
            violations / submitted,
            unit="ratio",
            sample_size=submitted,
        )

    coevolution = tuple(event for event in events if event.kind == "coevolve")
    if coevolution:
        derived[("coevolution", "stability_rate")] = _event_metric(
            sum(bool(event.payload.get("stable", False)) for event in coevolution)
            / len(coevolution),
            unit="ratio",
            sample_size=len(coevolution),
        )
        derived[("coevolution", "component_drift")] = _event_metric(
            max(
                float(event.payload.get("max_normalized_delta", 0.0))
                for event in coevolution
            ),
            unit="normalized_delta",
            sample_size=len(coevolution),
        )
        derived[("coevolution", "mechanism_recalibration_count")] = _event_metric(
            float(sum(int(event.payload.get("update_count", 0)) for event in coevolution)),
            unit="count",
            sample_size=len(coevolution),
        )

    alignment = tuple(event for event in events if event.kind == "align")
    if alignment:
        derived[("alignment", "state_error")] = _event_metric(
            max(float(event.payload["max_discrepancy"]) for event in alignment),
            unit="absolute_error",
            sample_size=len(alignment),
        )
        correction_events = tuple(
            event
            for event in alignment
            if int(event.payload.get("correction_count", 0)) > 0
        )
        if correction_events:
            derived[("alignment", "correction_magnitude")] = _event_metric(
                max(
                    float(event.payload["max_correction_magnitude"])
                    for event in correction_events
                ),
                unit="absolute_delta",
                sample_size=len(correction_events),
            )
    return derived


def _event_metric(
    value: float,
    *,
    unit: str,
    sample_size: int,
) -> MetricMeasurement:
    return MetricMeasurement(
        status=MeasurementStatus.MEASURED,
        value=float(value),
        unit=unit,
        sample_size=sample_size,
        provenance="event_log:ewm.event.v1",
    )
