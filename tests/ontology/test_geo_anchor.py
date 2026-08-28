"""Scientific contracts for explicit, sourced geographic placement."""

from __future__ import annotations

from collections.abc import Mapping

import pytest
from ewm.ontology.schema import validate_projection

from ewm.ontology import OntologyObject, OntologyRef, RelationAssertion, SourceLocator
from ewm.ontology.geography import geographic_placements
from ewm.ontology.projection import seal_projection
from ewm.ontology.query import GeoAnchorQuery, OntologyQueryService


def _source(kind: str = "researcher_declaration") -> SourceLocator:
    return SourceLocator(
        source_kind=kind,
        source_id="geo-study:1",
        artifact_path="inputs/geo-overlay.json",
        record_selector="anchors[0]",
        payload_digest="a" * 64,
    )


def _object(ref_id: str, kind: str, layer: str, properties: Mapping[str, object]):
    return OntologyObject(
        ref=OntologyRef(ref_id, kind),
        layer=layer,
        properties=properties,
        sources=(_source("verified_run") if kind == "run" else _source(),),
    )


def _anchor(**overrides: object) -> OntologyObject:
    properties: dict[str, object] = {
        "crs": "EPSG:4326",
        "latitude": 44.4268,
        "longitude": 26.1025,
        "anchor_basis": "declared",
        "evidence_classification": "researcher_declared",
        "validity": {"start": 0, "end": 10},
        "uncertainty_km": 2.5,
    }
    properties.update(overrides)
    return _object("ewm:test:geo:bucharest", "geo_anchor", "provenance", properties)


def _projection(*, anchor: OntologyObject | None = None, linked: bool = True):
    run = _object("ewm:test:run:1", "run", "runtime_occurrence", {})
    market = _object("ewm:test:market:1", "market", "economic_declaration", {})
    agent = _object("ewm:test:agent:unanchored", "agent", "economic_declaration", {})
    geo = anchor or _anchor()
    relations = (
        (
            RelationAssertion(
                ref=OntologyRef("ewm:test:relation:geo", "relation_assertion"),
                relation_type="GEO_ANCHORED_AT",
                source=market.ref,
                target=geo.ref,
                properties={},
                sources=(_source(),),
            ),
        )
        if linked
        else ()
    )
    return seal_projection(
        schema="ewm.ontology.v1",
        source_run=run.ref,
        objects=(run, market, agent, geo),
        relations=relations,
        measurements=(),
        coverage=(),
    )


def test_only_explicit_geo_relations_create_globe_placements() -> None:
    projection = _projection()

    placements = geographic_placements(projection)

    assert tuple(placement.subject.ref.id for placement in placements) == (
        "ewm:test:market:1",
    )
    assert placements[0].anchor.properties["anchor_basis"] == "declared"
    assert placements[0].relation.relation_type == "GEO_ANCHORED_AT"
    assert "ewm:test:agent:unanchored" not in {
        placement.subject.ref.id for placement in placements
    }


@pytest.mark.parametrize(
    ("overrides", "code"),
    (
        ({"crs": "EPSG:3857"}, "invalid_geo_crs"),
        ({"latitude": 91.0}, "invalid_geo_latitude"),
        ({"longitude": -181.0}, "invalid_geo_longitude"),
        ({"latitude": True}, "invalid_geo_latitude"),
        ({"anchor_basis": "inferred"}, "invalid_geo_basis"),
        ({"evidence_classification": "verified_run_evidence"}, "invalid_geo_evidence"),
        ({"validity": {"start": 10, "end": 0}}, "invalid_geo_validity"),
        ({"uncertainty_km": -0.1}, "invalid_geo_uncertainty"),
    ),
)
def test_invalid_geo_semantics_fail_schema_validation(
    overrides: Mapping[str, object],
    code: str,
) -> None:
    violations = validate_projection(_projection(anchor=_anchor(**overrides)))

    assert code in {violation.code for violation in violations}


def test_geo_query_filters_basis_and_validity_without_inference() -> None:
    service = OntologyQueryService.from_projection(_projection())

    active = service.geo_anchors(GeoAnchorQuery(bases=("declared",), valid_at=5))
    inactive = service.geo_anchors(GeoAnchorQuery(bases=("observed",), valid_at=20))

    assert tuple(item.ref.id for item in active.items) == ("ewm:test:geo:bucharest",)
    assert inactive.items == ()
