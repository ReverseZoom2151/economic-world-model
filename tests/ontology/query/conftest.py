"""Shared validated projection for ontology query contract tests."""

from __future__ import annotations

import pytest

from ewm.ontology import (
    Measurement,
    OntologyObject,
    OntologyProjection,
    OntologyRef,
    RelationAssertion,
    SourceLocator,
)
from ewm.ontology.graph.schema import assert_valid_projection

_DIGEST = "a" * 64


def _source(
    source_kind: str,
    source_id: str,
    *,
    selector: str,
) -> SourceLocator:
    return SourceLocator(
        source_kind=source_kind,
        source_id=source_id,
        artifact_path="runs/query-fixture.jsonl",
        record_selector=selector,
        payload_digest=_DIGEST,
    )


@pytest.fixture
def query_projection() -> OntologyProjection:
    """Return a small valid graph spanning every Task 9 index family."""

    run = OntologyObject(
        ref=OntologyRef("ewm:test:run:query", "run"),
        layer="runtime_occurrence",
        properties={"natural_key": "query-run", "time": 0},
        sources=(_source("verified_run", "query-run", selector="run"),),
    )
    world = OntologyObject(
        ref=OntologyRef("ewm:test:world:query", "world"),
        layer="economic_declaration",
        properties={
            "natural_key": "query-world",
            "episode_id": "episode-1",
            "event_sequence": 1,
            "time": 10,
        },
        sources=(_source("scenario_adapter", "query-world", selector="world"),),
    )
    evidence = OntologyObject(
        ref=OntologyRef("ewm:test:evidence:verified", "evidence_artifact"),
        layer="research_evidence",
        properties={
            "evidence_classification": "verified_run_evidence",
            "episode_id": "episode-1",
            "event_sequence": 2,
            "time": 20,
        },
        sources=(_source("verified_run", "query-run", selector="evidence"),),
    )
    claim = OntologyObject(
        ref=OntologyRef("ewm:test:claim:bounded", "claim"),
        layer="research_evidence",
        properties={
            "evidence_classification": "verified_run_evidence",
            "episode_id": "episode-1",
            "event_sequence": 3,
            "time": 30,
        },
        sources=(_source("derived_projection", "query-projection", selector="claim"),),
    )
    supports = RelationAssertion(
        ref=OntologyRef("ewm:test:relation:supports", "relation_assertion"),
        relation_type="SUPPORTS",
        source=evidence.ref,
        target=claim.ref,
        properties={"episode_id": "episode-1", "event_sequence": 4, "time": 40},
        sources=(_source("derived_projection", "query-projection", selector="supports"),),
    )
    measurement = Measurement(
        ref=OntologyRef("ewm:test:measurement:error", "measurement"),
        subject=world.ref,
        name="price_error",
        value=0.125,
        unit="index",
        status="observed",
        sample={"episode_id": "episode-1", "event_sequence": 5, "time": 50},
        uncertainty={"method": "none"},
        sources=(_source("verified_run", "query-run", selector="measurement"),),
    )
    projection = OntologyProjection(
        schema="ewm.ontology.v1",
        source_run=run.ref,
        objects=(claim, world, evidence, run),
        relations=(supports,),
        measurements=(measurement,),
        coverage=(),
        projection_digest="b" * 64,
    )
    assert_valid_projection(projection)
    return projection
