"""Deterministic ontology identity and serialization contract."""

from __future__ import annotations

import json

import pytest

from ewm.ontology import (
    CoverageEntry,
    Measurement,
    OntologyObject,
    OntologyProjection,
    OntologyRef,
    RelationAssertion,
    SourceLocator,
    identity,
)
from ewm.ontology.graph.identity import (
    IdentityCollisionError,
    OntologyIdentityRegistry,
    canonical_bytes,
    make_ontology_ref,
    ontology_record_from_data,
    ontology_record_to_data,
    projection_from_data,
    projection_to_data,
)

_DIGEST = "a" * 64


def _source(source_id: str = "run-sha256") -> SourceLocator:
    return SourceLocator(
        source_kind="verified_run",
        source_id=source_id,
        artifact_path="run/events.jsonl",
        record_selector="event_sequence=1",
        code_symbol=None,
        paper_anchor=None,
        payload_digest=_DIGEST,
    )


def _projection() -> OntologyProjection:
    source = _source()
    run_ref = OntologyRef("ewm:runtime:run:" + "1" * 64, "run")
    agent_ref = OntologyRef("ewm:declaration:agent:" + "2" * 64, "agent")
    run = OntologyObject(
        ref=run_ref,
        layer="runtime_occurrence",
        properties={"seed": 7, "nested": {"values": [1, 2]}},
        sources=(source,),
    )
    agent = OntologyObject(
        ref=agent_ref,
        layer="economic_declaration",
        properties={"role": "forecaster"},
        sources=(source,),
    )
    relation = RelationAssertion(
        ref=OntologyRef("ewm:runtime:relation_assertion:" + "3" * 64, "relation_assertion"),
        relation_type="CHOOSES",
        source=agent_ref,
        target=run_ref,
        properties={"sequence": 1},
        sources=(source,),
    )
    measurement = Measurement(
        ref=OntologyRef("ewm:evidence:measurement:" + "4" * 64, "measurement"),
        subject=run_ref,
        name="residual",
        value=(0.0, 0.1),
        unit="1",
        status="diagnostic_only",
        sample={"count": 2},
        uncertainty={"standard_error": 0.05},
        sources=(source,),
    )
    coverage = CoverageEntry(
        source=source,
        field="events[1]",
        status="projected",
        targets=(run_ref, measurement.ref),
        reason=None,
    )
    return OntologyProjection(
        schema="ewm.ontology.v1",
        source_run=run_ref,
        objects=(run, agent),
        relations=(relation,),
        measurements=(measurement,),
        coverage=(coverage,),
        projection_digest="5" * 64,
    )


def test_display_labels_do_not_affect_identity() -> None:
    first = make_ontology_ref(
        namespace="declaration",
        kind="agent",
        source_identity="scenario:forecasting:v1",
        semantic_keys={"agent_id": "forecaster-1"},
        display_label="Baseline forecaster",
    )
    renamed = make_ontology_ref(
        namespace="declaration",
        kind="agent",
        source_identity="scenario:forecasting:v1",
        semantic_keys={"agent_id": "forecaster-1"},
        display_label="Renamed in the UI",
    )

    assert first == renamed
    assert first.id.startswith("ewm:declaration:agent:")
    assert len(first.id.rsplit(":", maxsplit=1)[1]) == 64


def test_source_and_semantic_keys_change_identity() -> None:
    baseline = make_ontology_ref(
        namespace="runtime",
        kind="step",
        source_identity="run-a",
        semantic_keys={"sequence": 1},
    )

    assert baseline != make_ontology_ref(
        namespace="runtime",
        kind="step",
        source_identity="run-b",
        semantic_keys={"sequence": 1},
    )
    assert baseline != make_ontology_ref(
        namespace="runtime",
        kind="step",
        source_identity="run-a",
        semantic_keys={"sequence": 2},
    )


def test_source_record_order_is_significant_but_sets_are_not() -> None:
    ordered = make_ontology_ref(
        namespace="derived",
        kind="dataset",
        source_identity=("event:1", "event:2"),
        semantic_keys={"fields": {"outcome", "action"}},
    )
    same_set = make_ontology_ref(
        namespace="derived",
        kind="dataset",
        source_identity=("event:1", "event:2"),
        semantic_keys={"fields": {"action", "outcome"}},
    )
    reversed_sources = make_ontology_ref(
        namespace="derived",
        kind="dataset",
        source_identity=("event:2", "event:1"),
        semantic_keys={"fields": {"action", "outcome"}},
    )

    assert ordered == same_set
    assert ordered != reversed_sources


def test_identity_registry_fails_closed_on_digest_collision() -> None:
    registry = OntologyIdentityRegistry()
    ref = OntologyRef("ewm:test:agent:" + "f" * 64, "agent")
    registry.reserve(ref, {"source": "a", "semantic_keys": {"id": 1}})
    registry.reserve(ref, {"source": "a", "semantic_keys": {"id": 1}})

    with pytest.raises(IdentityCollisionError, match="collision"):
        registry.reserve(ref, {"source": "b", "semantic_keys": {"id": 1}})


def test_every_record_has_an_explicit_lossless_serializer() -> None:
    projection = _projection()
    records = (
        projection.source_run,
        projection.objects[0].sources[0],
        projection.objects[0],
        projection.relations[0],
        projection.measurements[0],
        projection.coverage[0],
        projection,
    )

    assert projection_from_data(projection_to_data(projection)) == projection
    for record in records:
        encoded = ontology_record_to_data(record)
        assert ontology_record_from_data(encoded) == record


def test_serialization_is_canonical_utf8_and_byte_identical() -> None:
    projection = _projection()

    first = canonical_bytes(projection_to_data(projection))
    second = canonical_bytes(projection_to_data(projection))

    assert first == second
    assert first == first.decode("utf-8").encode("utf-8")
    assert json.loads(first) == projection_to_data(projection)
    assert b" " not in first


def test_serializers_reject_unknown_records_and_unknown_fields() -> None:
    with pytest.raises(TypeError, match="ontology record"):
        ontology_record_to_data(object())
    with pytest.raises(ValueError, match="unknown fields"):
        ontology_record_from_data(
            {"record_type": "ontology_ref", "id": "id", "kind": "run", "label": "invented"}
        )


def test_identity_and_bytes_delegate_to_existing_canonical_functions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    digest_calls: list[object] = []
    json_calls: list[object] = []

    def fake_digest(value: object) -> str:
        digest_calls.append(value)
        return "d" * 64

    def fake_json(value: object) -> str:
        json_calls.append(value)
        return "{}"

    monkeypatch.setattr(identity.serialization, "content_digest", fake_digest)
    ref = make_ontology_ref(
        namespace="test",
        kind="agent",
        source_identity="source",
        semantic_keys={"id": 1},
    )
    monkeypatch.setattr(identity.serialization, "canonical_json", fake_json)

    assert canonical_bytes({"key": "value"}) == b"{}"
    assert ref.id.endswith("d" * 64)
    assert len(digest_calls) == 1
    assert json_calls == [{"key": "value"}]
