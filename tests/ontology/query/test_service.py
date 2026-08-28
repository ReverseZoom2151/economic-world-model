"""Contracts for bounded, typed, read-only ontology queries."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ewm.ontology import OntologyProjection
from ewm.ontology.query import (
    ClaimQuery,
    CursorError,
    EvidenceQuery,
    MeasurementQuery,
    ObjectQuery,
    OntologyQueryService,
    PathFilter,
    PathQuery,
    QueryCostError,
    QueryLimits,
    RelationQuery,
    SequenceWindow,
    TimeWindow,
)


def test_object_pages_are_stable_bounded_and_cursor_driven(
    query_projection: OntologyProjection,
) -> None:
    service = OntologyQueryService.from_projection(query_projection)
    query = ObjectQuery(layers=("research_evidence",))

    first = service.objects(query, limit=1)
    second = service.objects(query, limit=1, cursor=first.next_cursor)

    assert tuple(item.ref.id for item in first.items + second.items) == (
        "ewm:test:claim:bounded",
        "ewm:test:evidence:verified",
    )
    assert first.next_cursor is not None
    assert second.next_cursor is None
    assert "ewm:test" not in first.next_cursor
    with pytest.raises(FrozenInstanceError):
        first.next_cursor = None  # type: ignore[misc]


def test_cursors_are_bound_to_filter_projection_and_integrity(
    query_projection: OntologyProjection,
) -> None:
    service = OntologyQueryService.from_projection(query_projection)
    first = service.objects(ObjectQuery(), limit=1)
    assert first.next_cursor is not None

    with pytest.raises(CursorError, match="query"):
        service.objects(ObjectQuery(kinds=("claim",)), limit=1, cursor=first.next_cursor)
    with pytest.raises(CursorError, match="invalid"):
        service.objects(ObjectQuery(), limit=1, cursor=first.next_cursor[:-1] + "A")


def test_collection_limits_and_filter_costs_fail_with_structured_errors(
    query_projection: OntologyProjection,
) -> None:
    service = OntologyQueryService.from_projection(
        query_projection,
        limits=QueryLimits(default_page_size=2, max_page_size=2, max_filter_values=2),
    )

    with pytest.raises(QueryCostError) as page_error:
        service.objects(limit=3)
    with pytest.raises(QueryCostError) as filter_error:
        service.objects(ObjectQuery(ids=("a", "b", "c")))

    assert page_error.value.as_dict() == {
        "code": "page_limit_exceeded",
        "operation": "objects",
        "limit": 2,
        "observed": 3,
    }
    assert filter_error.value.code == "filter_limit_exceeded"
    assert filter_error.value.observed == 3


def test_typed_context_relation_measurement_claim_and_evidence_filters(
    query_projection: OntologyProjection,
) -> None:
    service = OntologyQueryService.from_projection(query_projection)

    objects = service.objects(
        ObjectQuery(
            episode_ids=("episode-1",),
            event_sequence=SequenceWindow(start=2, end=3),
            time=TimeWindow(start=15, end=35),
        )
    )
    outgoing = service.relations(
        RelationQuery(incident_ids=("ewm:test:evidence:verified",), direction="outgoing")
    )
    incoming = service.relations(
        RelationQuery(incident_ids=("ewm:test:claim:bounded",), direction="incoming")
    )
    measurements = service.measurements(
        MeasurementQuery(names=("price_error",), statuses=("observed",))
    )
    claims = service.claims(ClaimQuery(classifications=("verified_run_evidence",)))
    evidence = service.evidence(EvidenceQuery(classifications=("verified_run_evidence",)))

    assert tuple(item.ref.kind for item in objects.items) == ("claim", "evidence_artifact")
    assert outgoing.items == incoming.items
    assert outgoing.items[0].relation_type == "SUPPORTS"
    assert measurements.items[0].name == "price_error"
    assert claims.items[0].ref.kind == "claim"
    assert evidence.items[0].ref.kind == "evidence_artifact"


def test_source_locator_filter_is_exact_and_typed(
    query_projection: OntologyProjection,
) -> None:
    service = OntologyQueryService.from_projection(query_projection)
    source = next(item.sources[0] for item in query_projection.objects if item.ref.kind == "claim")

    page = service.objects(ObjectQuery(sources=(source,)))

    assert tuple(item.ref.kind for item in page.items) == ("claim",)


def test_path_queries_are_deterministic_filtered_and_depth_bounded(
    query_projection: OntologyProjection,
) -> None:
    service = OntologyQueryService.from_projection(
        query_projection,
        limits=QueryLimits(
            max_traversal_depth=2,
            max_visited_records=10,
            default_path_limit=4,
            max_paths=4,
        ),
    )
    result = service.paths(
        PathQuery(
            start_id="ewm:test:evidence:verified",
            target_id="ewm:test:claim:bounded",
            max_depth=1,
            filter=PathFilter(relation_types=("SUPPORTS",), direction="outgoing"),
        )
    )

    assert len(result.paths) == 1
    assert tuple(ref.kind for ref in result.paths[0].nodes) == ("evidence_artifact", "claim")
    assert tuple(relation.relation_type for relation in result.paths[0].relations) == ("SUPPORTS",)
    assert result.visited_records == 2
    assert result.truncated is False

    with pytest.raises(QueryCostError) as error:
        service.paths(
            PathQuery(
                start_id="ewm:test:evidence:verified",
                target_id="ewm:test:claim:bounded",
                max_depth=3,
            )
        )
    assert error.value.code == "traversal_depth_exceeded"


def test_time_windows_reject_mixed_or_reversed_bound_types() -> None:
    with pytest.raises(TypeError, match="same type"):
        TimeWindow(start=1, end="2026-08-28")
    with pytest.raises(ValueError, match="start"):
        TimeWindow(start=3, end=2)
