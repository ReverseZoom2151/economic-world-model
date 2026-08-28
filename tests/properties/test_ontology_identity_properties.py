"""Property checks for deterministic ontology identity construction."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from ewm.ontology.identity import canonical_bytes, make_ontology_ref

_keys = st.dictionaries(
    keys=st.text(
        alphabet=st.characters(categories=("Ll", "Lu", "Nd")),
        min_size=1,
        max_size=8,
    ),
    values=st.integers(min_value=-1_000_000, max_value=1_000_000),
    max_size=12,
)


@given(keys=_keys)
@settings(max_examples=100, deadline=None)
def test_mapping_insertion_order_never_changes_identity(keys: dict[str, int]) -> None:
    reversed_keys = dict(reversed(tuple(keys.items())))

    first = make_ontology_ref(
        namespace="property",
        kind="object",
        source_identity="source",
        semantic_keys=keys,
    )
    second = make_ontology_ref(
        namespace="property",
        kind="object",
        source_identity="source",
        semantic_keys=reversed_keys,
    )

    assert first == second


@given(values=st.sets(st.integers(), max_size=20))
@settings(max_examples=100, deadline=None)
def test_set_iteration_order_never_changes_identity(values: set[int]) -> None:
    forward = set(values)
    reverse = set(reversed(sorted(values)))

    assert make_ontology_ref(
        namespace="property",
        kind="set",
        source_identity="source",
        semantic_keys={"values": forward},
    ) == make_ontology_ref(
        namespace="property",
        kind="set",
        source_identity="source",
        semantic_keys={"values": reverse},
    )


@given(first=st.text(min_size=1), second=st.text(min_size=1))
@settings(max_examples=100, deadline=None)
def test_ordered_source_records_remain_significant(first: str, second: str) -> None:
    if first == second:
        return

    assert make_ontology_ref(
        namespace="property",
        kind="ordered",
        source_identity=(first, second),
        semantic_keys={},
    ) != make_ontology_ref(
        namespace="property",
        kind="ordered",
        source_identity=(second, first),
        semantic_keys={},
    )


@given(keys=_keys)
@settings(max_examples=100, deadline=None)
def test_repeated_canonical_serialization_is_byte_identical(keys: dict[str, int]) -> None:
    assert canonical_bytes(keys) == canonical_bytes(keys)
