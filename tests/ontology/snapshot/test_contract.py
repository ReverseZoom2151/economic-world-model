"""Canonical portable-investigation selection and integrity contracts."""

from __future__ import annotations

import pytest

from ewm._internal.canonical import content_digest
from ewm.ontology.graph.model import (
    Measurement,
    OntologyObject,
    OntologyRef,
    RelationAssertion,
    SourceLocator,
)
from ewm.ontology.projection.service import seal_projection
from ewm.ontology.snapshot import (
    SnapshotLimits,
    SnapshotSelection,
    SnapshotSizeError,
    SnapshotSource,
    compile_investigation,
    investigation_from_bytes,
    investigation_to_bytes,
)


def _projection():
    source = SourceLocator(
        source_kind="verified_run",
        source_id="a" * 64,
        artifact_path="run/events.jsonl",
        payload_digest="b" * 64,
    )
    run = OntologyObject(
        ref=OntologyRef("ewm:test:run", "run"),
        layer="runtime_occurrence",
        properties={"event_sequence": 0, "natural_key": "test-run"},
        sources=(source,),
    )
    agent = OntologyObject(
        ref=OntologyRef("ewm:test:agent", "agent"),
        layer="economic_declaration",
        properties={"natural_key": "agent"},
        sources=(source,),
    )
    event = OntologyObject(
        ref=OntologyRef("ewm:test:event", "transition_event"),
        layer="runtime_occurrence",
        properties={"event_sequence": 1, "natural_key": "event"},
        sources=(source,),
    )
    relation = RelationAssertion(
        ref=OntologyRef("ewm:test:relation", "relation_assertion"),
        relation_type="ACTED_IN",
        source=agent.ref,
        target=event.ref,
        properties={},
        sources=(source,),
    )
    measurement = Measurement(
        ref=OntologyRef("ewm:test:measurement", "measurement"),
        subject=agent.ref,
        name="utility",
        value=1.0,
        unit="index",
        status="observed",
        sample={},
        uncertainty={},
        sources=(source,),
    )
    return seal_projection(
        schema="ewm.ontology.v1",
        source_run=run.ref,
        objects=(run, agent, event),
        relations=(relation,),
        measurements=(measurement,),
        coverage=(),
    )


def _source() -> SnapshotSource:
    return SnapshotSource(
        run_id="run-a",
        source_run_hash="a" * 20,
        source_identity_sha256="a" * 64,
        source_bundle_sha256="b" * 64,
        profile_identity="ewm.test.v1",
        profile_digest="c" * 64,
        integrity_level="checksummed",
    )


def test_selection_is_canonical_and_snapshot_bytes_are_reproducible() -> None:
    projection = _projection()
    left = SnapshotSelection.from_data(
        {
            "object_ids": ["ewm:test:event", "ewm:test:agent"],
            "event_ids": ["ewm:test:event"],
            "relation_ids": ["ewm:test:relation"],
            "lens": "scene",
            "filters": {
                "kinds": ["transition_event", "agent", "agent"],
                "layers": ["runtime_occurrence", "economic_declaration"],
                "query": "market",
            },
            "time_window": {"start": 8, "end": 2},
            "camera": {
                "projection": "perspective",
                "position": [3, 4, 5],
                "target": [0, 0, 0],
            },
            "layout": {"mode": "semantic", "dimension": "3d"},
        }
    )
    right = SnapshotSelection.from_data(
        {
            "layout": {"dimension": "3d", "mode": "semantic"},
            "camera": {
                "target": [0, 0, 0],
                "position": [3, 4, 5],
                "projection": "perspective",
            },
            "time_window": {"end": 8, "start": 2},
            "filters": {
                "query": "market",
                "layers": ["economic_declaration", "runtime_occurrence"],
                "kinds": ["agent", "transition_event"],
            },
            "lens": "scene",
            "relation_ids": ["ewm:test:relation"],
            "event_ids": ["ewm:test:event"],
            "object_ids": ["ewm:test:agent", "ewm:test:event"],
        }
    )

    first = compile_investigation(projection, _source(), left)
    second = compile_investigation(projection, _source(), right)
    encoded = investigation_to_bytes(first)

    assert left == right
    assert investigation_to_bytes(second) == encoded
    assert investigation_from_bytes(encoded) == first
    assert first.schema == "ewm.investigation.v1"
    assert first.projection_digest == projection.projection_digest
    assert first.source_bundle_sha256 == "b" * 64
    assert first.subset_digest == content_digest(first.semantic_data())
    assert [item.ref.id for item in first.objects] == [
        "ewm:test:agent",
        "ewm:test:event",
    ]
    assert first.selection.time_window == (2.0, 8.0)
    assert first.selection.layout == {"dimension": "3d", "mode": "semantic"}


def test_globe_geometry_is_bundled_only_for_the_globe_lens() -> None:
    geometry = {"type": "FeatureCollection", "features": []}
    projection = _projection()

    world = compile_investigation(
        projection,
        _source(),
        SnapshotSelection.from_data({"lens": "world"}),
        globe_geometry=geometry,
    )
    globe = compile_investigation(
        projection,
        _source(),
        SnapshotSelection.from_data({"lens": "globe"}),
        globe_geometry=geometry,
    )

    assert world.globe_geometry is None
    assert globe.globe_geometry == geometry


def test_snapshot_limits_return_a_structured_scope_reduction_diagnostic() -> None:
    with pytest.raises(SnapshotSizeError) as caught:
        compile_investigation(
            _projection(),
            _source(),
            SnapshotSelection.from_data({"lens": "world"}),
            limits=SnapshotLimits(max_objects=1),
        )

    diagnostic = caught.value.as_dict()
    assert diagnostic["code"] == "snapshot_scope_exceeded"
    assert diagnostic["counts"]["objects"] == 3
    assert diagnostic["limits"]["objects"] == 1
    assert diagnostic["reductions"]
