"""Truthfulness checks for ontology claims, evidence, and readiness records."""

from __future__ import annotations

import pytest

from ewm.ontology import OntologyObject, OntologyRef
from ewm.ontology.compiler import ProjectionCompilation
from ewm.ontology.projection import seal_projection
from ewm.ontology.schema import validate_projection

pytestmark = pytest.mark.conformance


def _profile_objects(
    compilation: ProjectionCompilation,
    kind: str,
) -> tuple[OntologyObject, ...]:
    return tuple(
        item
        for item in compilation.projection.objects
        if item.ref.kind == kind and item.properties.get("profile_evidence") is True
    )


@pytest.mark.parametrize(
    ("fixture_name", "expected"),
    (
        ("scalar_projection", "exact-replication"),
        ("forecasting_projection", "exact-replication"),
        ("credit_projection", "qualitative-reconstruction"),
        ("fx_projection", "synthetic_systems_conformance"),
    ),
)
def test_profile_evidence_uses_the_validated_classification_without_broadening(
    fixture_name: str,
    expected: str,
    request: pytest.FixtureRequest,
) -> None:
    compilation: ProjectionCompilation = request.getfixturevalue(fixture_name)
    evidence = _profile_objects(compilation, "evidence_artifact")

    assert evidence
    assert {item.properties["evidence_classification"] for item in evidence} == {
        expected
    }


@pytest.mark.parametrize(
    "fixture_name",
    ("scalar_projection", "forecasting_projection", "fx_projection"),
)
def test_every_profile_claim_has_matching_linked_evidence(
    fixture_name: str,
    request: pytest.FixtureRequest,
) -> None:
    compilation: ProjectionCompilation = request.getfixturevalue(fixture_name)
    projection = compilation.projection
    claims = tuple(
        item
        for item in projection.objects
        if item.ref.kind == "claim" and item.properties.get("profile_evidence") is True
    )
    evidence = {
        item.ref: item
        for item in projection.objects
        if item.ref.kind == "evidence_artifact"
    }

    assert claims
    for claim in claims:
        supporters = tuple(
            evidence[item.source]
            for item in projection.relations
            if item.relation_type == "SUPPORTS"
            and item.target == claim.ref
            and item.source in evidence
        )
        assert supporters
        assert {
            item.properties["evidence_classification"] for item in supporters
        } == {claim.properties["evidence_classification"]}


def test_fx_evidence_cannot_award_higher_han_capability(
    fx_projection: ProjectionCompilation,
) -> None:
    claims = tuple(
        item
        for item in fx_projection.projection.objects
        if item.ref.kind == "claim" and item.properties.get("profile_evidence") is True
    )

    assert claims
    assert all(item.properties["capability_ceiling"] == "L2" for item in claims)
    assert all(item.properties["official_award"] is False for item in claims)


def test_ontology_readiness_naming_cannot_mint_han_l3_l6_awards(
    fx_projection: ProjectionCompilation,
) -> None:
    baseline = fx_projection.projection
    source = baseline.objects[0].sources[0]
    fraudulent = OntologyObject(
        ref=OntologyRef("ewm:test:readiness:l6-award", "readiness_assessment"),
        layer="research_evidence",
        properties={
            "classification": "evidence_readiness_only",
            "status": "pass",
            "blocked": False,
            "official_awards": 1,
            "level": "L6",
        },
        sources=(source,),
    )
    projection = seal_projection(
        schema=baseline.schema,
        source_run=baseline.source_run,
        objects=(*baseline.objects, fraudulent),
        relations=baseline.relations,
        measurements=baseline.measurements,
        coverage=baseline.coverage,
    )

    codes = {item.code for item in validate_projection(projection)}

    assert "readiness_award_forbidden" in codes
