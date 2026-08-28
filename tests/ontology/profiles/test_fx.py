from __future__ import annotations

from ewm.ontology.compiler import ProjectionCompilation


def test_fx_profile_projects_clearing_transactions_and_rejections(
    fx_projection: ProjectionCompilation,
) -> None:
    projection = fx_projection.projection
    transactions = tuple(obj for obj in projection.objects if obj.ref.kind == "transaction")
    rejection_outcomes = tuple(
        obj
        for obj in projection.objects
        if obj.ref.kind == "outcome" and obj.properties.get("outcome_kind") == "order_rejections"
    )
    clearings = tuple(
        obj for obj in projection.objects if obj.ref.kind == "inner_equilibrium"
    )
    total_volume = next(
        measurement
        for measurement in projection.measurements
        if measurement.name == "total_volume"
    )

    assert len(transactions) == len(rejection_outcomes) == len(clearings) == 24
    assert sum(float(item.properties["volume"]) for item in transactions) == float(
        total_volume.value
    )
    assert sum(int(item.properties["rejected_count"]) for item in rejection_outcomes) == 0
    assert all(item.sources[0].artifact_path == "run/events.jsonl" for item in transactions)
    assert all(item.properties["candidate_count"] == 1 for item in clearings)


def test_fx_profile_preserves_market_and_provenance_boundaries(
    fx_projection: ProjectionCompilation,
) -> None:
    projection = fx_projection.projection
    market = next(obj for obj in projection.objects if obj.ref.kind == "market")
    relations = {relation.relation_type for relation in projection.relations}
    gaps = {entry.field: entry for entry in projection.coverage}

    assert market.properties["base_asset"] == "cash"
    assert market.properties["quote_asset"] == "foreign_currency"
    assert {"CLEARS", "REALIZES", "INSTANTIATES"} <= relations
    assert gaps["adapter.fx.transaction_counterparties"].status == "unavailable"
