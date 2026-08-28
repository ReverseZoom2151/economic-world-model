"""Generated checks for stable ordering and bounded ontology pagination."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from ewm.ontology import OntologyObject, OntologyProjection, OntologyRef, SourceLocator
from ewm.ontology.query import ObjectQuery, OntologyQueryService, build_indexes

_DIGEST = "a" * 64


def _object(index: int, kind: str = "world") -> OntologyObject:
    source_kind = "verified_run" if kind == "run" else "scenario_adapter"
    return OntologyObject(
        ref=OntologyRef(f"ewm:property:{kind}:{index:02d}", kind),
        layer="runtime_occurrence" if kind == "run" else "economic_declaration",
        properties={"natural_key": f"{kind}-{index}"},
        sources=(
            SourceLocator(
                source_kind=source_kind,
                source_id=f"source-{index}",
                record_selector=f"record={index}",
                payload_digest=_DIGEST,
            ),
        ),
    )


def _projection(order: tuple[int, ...]) -> OntologyProjection:
    run = _object(99, "run")
    worlds = tuple(_object(index) for index in order)
    return OntologyProjection(
        schema="ewm.ontology.v1",
        source_run=run.ref,
        objects=(run, *worlds),
        relations=(),
        measurements=(),
        coverage=(),
        projection_digest="b" * 64,
    )


@given(order=st.permutations((0, 1, 2, 3, 4)))
@settings(max_examples=20, deadline=None)
def test_index_and_query_order_do_not_depend_on_projection_order(order: list[int]) -> None:
    projection = _projection(tuple(order))

    assert build_indexes(projection).object_ids_by_kind["world"] == tuple(
        f"ewm:property:world:{index:02d}" for index in range(5)
    )
    assert tuple(
        item.ref.id
        for item in OntologyQueryService.from_projection(projection)
        .objects(ObjectQuery(kinds=("world",)))
        .items
    ) == tuple(f"ewm:property:world:{index:02d}" for index in range(5))


@given(page_size=st.integers(min_value=1, max_value=5))
def test_cursor_pagination_returns_every_match_once_within_requested_bound(
    page_size: int,
) -> None:
    service = OntologyQueryService.from_projection(_projection((4, 3, 2, 1, 0)))
    query = ObjectQuery(kinds=("world",))
    cursor: str | None = None
    pages: list[tuple[str, ...]] = []

    while True:
        page = service.objects(query, limit=page_size, cursor=cursor)
        assert 0 < len(page.items) <= page_size
        pages.append(tuple(item.ref.id for item in page.items))
        cursor = page.next_cursor
        if cursor is None:
            break

    flattened = tuple(item for page in pages for item in page)
    assert flattened == tuple(f"ewm:property:world:{index:02d}" for index in range(5))
