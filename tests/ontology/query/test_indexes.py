"""Contracts for deterministic immutable ontology indexes."""

from __future__ import annotations

from collections.abc import Mapping

import pytest
from ewm.ontology.schema import OntologyValidationError

from ewm.ontology import OntologyObject, OntologyProjection
from ewm.ontology.query import build_indexes


def test_indexes_cover_identity_graph_context_sources_and_evidence(
    query_projection: OntologyProjection,
) -> None:
    indexes = build_indexes(query_projection)
    run_id = query_projection.source_run.id
    evidence_id = "ewm:test:evidence:verified"
    claim_id = "ewm:test:claim:bounded"
    relation_id = "ewm:test:relation:supports"
    measurement_id = "ewm:test:measurement:error"

    assert indexes.records_by_id[claim_id].ref.kind == "claim"
    assert indexes.object_ids_by_kind["claim"] == (claim_id,)
    assert indexes.object_ids_by_layer["research_evidence"] == (claim_id, evidence_id)
    assert indexes.outgoing_relation_ids[evidence_id] == (relation_id,)
    assert indexes.incoming_relation_ids[claim_id] == (relation_id,)
    assert indexes.record_ids_by_run[run_id] == tuple(sorted(indexes.records_by_id))
    assert indexes.record_ids_by_episode["episode-1"] == (
        claim_id,
        evidence_id,
        measurement_id,
        relation_id,
        "ewm:test:world:query",
    )
    assert indexes.record_ids_by_event_sequence[3] == (claim_id,)
    assert indexes.record_ids_by_time[50] == (measurement_id,)
    assert indexes.measurement_ids_by_name["price_error"] == (measurement_id,)
    assert indexes.measurement_ids_by_status["observed"] == (measurement_id,)
    assert indexes.claim_ids_by_classification["verified_run_evidence"] == (claim_id,)
    assert indexes.evidence_ids_by_classification["verified_run_evidence"] == (evidence_id,)
    claim_source = next(
        source
        for source in indexes.record_ids_by_source
        if source.record_selector == "claim"
    )
    assert indexes.record_ids_by_source[claim_source] == (claim_id,)


def test_index_mappings_and_buckets_cannot_be_mutated(
    query_projection: OntologyProjection,
) -> None:
    indexes = build_indexes(query_projection)

    with pytest.raises(TypeError):
        indexes.object_ids_by_kind["claim"] = ()  # type: ignore[index]
    with pytest.raises(AttributeError):
        indexes.object_ids_by_kind["claim"].append("mutable")  # type: ignore[attr-defined]


def test_index_construction_rejects_an_invalid_projection(
    query_projection: OntologyProjection,
) -> None:
    claim = next(
        item
        for item in query_projection.objects
        if isinstance(item, OntologyObject) and item.ref.kind == "claim"
    )
    invalid = OntologyProjection(
        schema=query_projection.schema,
        source_run=query_projection.source_run,
        objects=query_projection.objects,
        relations=(),
        measurements=query_projection.measurements,
        coverage=query_projection.coverage,
        projection_digest=query_projection.projection_digest,
    )

    with pytest.raises(OntologyValidationError) as error:
        build_indexes(invalid)

    assert claim.ref.id in str(error.value)


def test_public_index_annotations_are_read_only_mappings() -> None:
    annotations = build_indexes.__annotations__

    assert isinstance(annotations, Mapping)
