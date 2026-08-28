from __future__ import annotations

from ewm.ontology.profiles import SCALAR_PROFILE
from ewm.ontology.projection.compiler import ProjectionCompilation


def test_scalar_profile_preserves_fixed_point_multiplicity_and_diagnostics(
    scalar_projection: ProjectionCompilation,
) -> None:
    projection = scalar_projection.projection
    candidates = tuple(obj for obj in projection.objects if obj.ref.kind == "ddge_candidate")
    residuals = tuple(obj for obj in projection.objects if obj.ref.kind == "residual")
    correspondence = next(obj for obj in projection.objects if obj.ref.kind == "inner_equilibrium")

    assert len(candidates) == len(residuals) == 3
    assert correspondence.properties["candidate_count"] == 3
    assert correspondence.properties["selector"] == "retain_all_distinct_roots"
    assert sorted(candidate.properties["theta"] for candidate in candidates) == [
        candidate.properties["theta"] for candidate in candidates
    ]
    assert {candidate.properties["stable"] for candidate in candidates} == {True, False}
    assert all(residual.properties["solver"] for residual in residuals)


def test_scalar_profile_sources_declarations_and_explicit_gaps(
    scalar_projection: ProjectionCompilation,
) -> None:
    projection = scalar_projection.projection
    world = next(obj for obj in projection.objects if obj.ref.kind == "world")
    provenance = next(
        obj
        for obj in projection.objects
        if obj.ref.kind == "source_locator" and obj.properties.get("profile_identity")
    )
    gaps = {entry.field: entry for entry in projection.coverage}

    assert world.properties["evidence_origin"] == "adapter_derived"
    assert world.sources == (world.sources[0],)
    assert world.sources[0].source_kind == "scenario_adapter"
    assert world.sources[0].payload_digest == SCALAR_PROFILE.source_digest
    assert provenance.properties["profile_identity"] == "ewm.scalar-ontology-profile.v1"
    assert gaps["adapter.scalar.distance_bound"].status == "unavailable"
    assert "certificate" in str(gaps["adapter.scalar.distance_bound"].reason)
