from __future__ import annotations

from ewm.ontology.compiler import ProjectionCompilation


def test_forecasting_profile_preserves_roots_and_learned_coefficients(
    forecasting_projection: ProjectionCompilation,
) -> None:
    projection = forecasting_projection.projection
    candidates = tuple(obj for obj in projection.objects if obj.ref.kind == "ddge_candidate")
    parameters = tuple(obj for obj in projection.objects if obj.ref.kind == "parameter_version")
    correspondence = next(obj for obj in projection.objects if obj.ref.kind == "inner_equilibrium")

    assert len(candidates) == len(parameters) == 3
    assert correspondence.properties == {
        "candidate_count": 3,
        "selector": "retain_all_independently_bracketed_roots",
        "status": "numerically_validated",
    }
    assert [candidate.properties["theta"] for candidate in candidates] == sorted(
        candidate.properties["theta"] for candidate in candidates
    )
    assert all(parameter.properties["coefficient_name"] == "forecast" for parameter in parameters)
    assert all(
        candidate.sources[0].artifact_path == "run/events.jsonl" for candidate in candidates
    )
    assert [candidate.sources[0].record_selector for candidate in candidates] == [
        "sequence=0",
        "sequence=1",
        "sequence=2",
    ]


def test_forecasting_profile_records_missing_welfare_evidence(
    forecasting_projection: ProjectionCompilation,
) -> None:
    gaps = {entry.field: entry for entry in forecasting_projection.projection.coverage}

    assert gaps["adapter.forecasting.welfare_bound"].status == "unavailable"
    assert gaps["adapter.forecasting.external_validation"].status == "unavailable"
