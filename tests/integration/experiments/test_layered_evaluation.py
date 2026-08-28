"""Integration contracts for layered economic evaluation."""

from __future__ import annotations

from copy import deepcopy

import pytest

from ewm.core import Event, MeasurementStatus
from ewm.experiments import MetricEvidence, evaluate_layered


def _events() -> tuple[Event, ...]:
    return (
        Event(0, "reset", {"seed": 4}, state_version=0),
        Event(1, "run_agents", {"agent_ids": ("a", "b")}, state_version=0),
        Event(
            2,
            "step",
            {"submitted_count": 4, "accepted_count": 3, "violation_count": 1},
            state_version=1,
        ),
        Event(
            3,
            "coevolve",
            {
                "update_count": 2,
                "max_normalized_delta": 0.4,
                "stable": True,
            },
            state_version=1,
        ),
        Event(
            4,
            "align",
            {
                "correction_count": 1,
                "max_correction_magnitude": 0.1,
                "max_discrepancy": 0.2,
                "within_tolerance": False,
            },
            state_version=1,
        ),
    )


def _evidence() -> dict[str, dict[str, MetricEvidence]]:
    return {
        "agents": {
            "role_consistency_rate": MetricEvidence(
                value=0.98,
                unit="ratio",
                provenance="evaluations/roles.json",
                sample_size=50,
            )
        },
        "environment": {
            "clearing_error": MetricEvidence(
                value=1e-12,
                unit="absolute_residual",
                provenance="evaluations/clearing.json",
                sample_size=10,
            ),
            "accounting_error": MetricEvidence(
                value=2e-12,
                unit="absolute_residual",
                provenance="evaluations/accounting.json",
                sample_size=10,
            ),
        },
        "coevolution": {
            "adaptation_gain": MetricEvidence(
                value=0.07,
                unit="score_delta",
                provenance="evaluations/adaptation.json",
                sample_size=6,
            )
        },
        "efficiency": {
            "runtime_seconds": MetricEvidence(
                value=0.42,
                unit="seconds",
                provenance="benchmarks/run.json",
                sample_size=3,
            ),
            "peak_memory_bytes": MetricEvidence(
                value=12_000_000.0,
                unit="bytes",
                provenance="benchmarks/run.json",
                sample_size=3,
            ),
            "agent_scaling_ratio": MetricEvidence(
                value=1.8,
                unit="runtime_ratio",
                provenance="benchmarks/scaling.json",
                sample_size=4,
            ),
        },
    }


def test_five_layer_report_combines_event_and_supplied_evidence() -> None:
    report = evaluate_layered(_events(), state_version=1, evidence=_evidence())

    assert tuple(report.layers) == (
        "agents",
        "environment",
        "coevolution",
        "alignment",
        "efficiency",
    )
    assert report.layers["agents"].metrics["action_validity_rate"].value == 0.75
    assert report.layers["agents"].metrics["role_consistency_rate"].value == 0.98
    assert (
        report.layers["environment"].metrics["constraint_violation_rate"].value
        == 0.25
    )
    assert report.layers["environment"].metrics["clearing_error"].value == 1e-12
    assert report.layers["coevolution"].metrics["adaptation_gain"].value == 0.07
    assert report.layers["coevolution"].metrics["stability_rate"].value == 1.0
    assert report.layers["coevolution"].metrics["component_drift"].value == 0.4
    assert report.layers["alignment"].metrics["state_error"].value == 0.2
    assert report.layers["alignment"].metrics["correction_magnitude"].value == 0.1
    assert report.layers["efficiency"].metrics["runtime_seconds"].value == 0.42


def test_missing_evidence_is_not_measured_and_never_zero_filled() -> None:
    report = evaluate_layered((), state_version=0, evidence={})

    for layer in report.layers.values():
        for measurement in layer.metrics.values():
            assert measurement.status is MeasurementStatus.NOT_MEASURED
            assert measurement.value is None
            assert measurement.sample_size == 0
    assert (
        report.layers["alignment"].metrics["trend_error"].status
        is MeasurementStatus.NOT_MEASURED
    )


def test_layered_evaluation_is_read_only_over_events_and_inputs() -> None:
    events = _events()
    evidence = _evidence()
    before_events = events
    before_payloads = tuple(dict(event.payload) for event in events)
    before_evidence = deepcopy(evidence)

    first = evaluate_layered(events, state_version=1, evidence=evidence)
    second = evaluate_layered(events, state_version=1, evidence=evidence)

    assert events == before_events
    assert tuple(dict(event.payload) for event in events) == before_payloads
    assert evidence == before_evidence
    assert first == second


def test_unknown_layer_or_metric_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown evaluation layer"):
        evaluate_layered(
            (),
            state_version=0,
            evidence={"unknown": {}},
        )
    with pytest.raises(ValueError, match="unknown metric"):
        evaluate_layered(
            (),
            state_version=0,
            evidence={
                "agents": {
                    "made_up": MetricEvidence(
                        value=1.0,
                        unit="score",
                        provenance="invalid.json",
                        sample_size=1,
                    )
                }
            },
        )
