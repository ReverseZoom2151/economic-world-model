"""Property checks for deterministic, fail-closed ontology validation."""

from __future__ import annotations

from collections.abc import Mapping

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ewm.ontology import OntologyObject, OntologyProjection, OntologyRef, SourceLocator
from ewm.ontology.schema import validate_projection

_DIGEST = "a" * 64
_LAYERS = {
    "agent": "economic_declaration",
    "market": "economic_declaration",
    "run": "runtime_occurrence",
    "world": "economic_declaration",
}


def _source(kind: str = "verified_run") -> SourceLocator:
    return SourceLocator(
        source_kind=kind,
        source_id="run-sha256",
        artifact_path="run/events.jsonl",
        record_selector="event_sequence=1",
        payload_digest=_DIGEST,
    )


def _object(
    suffix: str,
    kind: str,
    properties: Mapping[str, object] | None = None,
) -> OntologyObject:
    return OntologyObject(
        ref=OntologyRef(f"ewm:test:{kind}:{suffix}", kind),
        layer=_LAYERS[kind],
        properties=properties or {},
        sources=(_source(),),
    )


def _projection(objects: tuple[OntologyObject, ...]) -> OntologyProjection:
    run = _object("source", "run", {"natural_key": "source"})
    return OntologyProjection(
        schema="ewm.ontology.v1",
        source_run=run.ref,
        objects=(run, *objects),
        relations=(),
        measurements=(),
        coverage=(),
        projection_digest="b" * 64,
    )


@given(order=st.permutations((0, 1, 2)))
@settings(max_examples=12, deadline=None)
def test_validation_is_independent_of_input_order(order: list[int]) -> None:
    objects = (
        _object("2", "agent", {"natural_key": "duplicate"}),
        _object("1", "agent", {"natural_key": "duplicate"}),
        _object("1", "market"),
    )
    reordered = tuple(objects[index] for index in order)

    assert validate_projection(_projection(reordered)) == validate_projection(_projection(objects))


@given(kind=st.sampled_from(("world", "agent", "market")))
@settings(max_examples=12, deadline=None)
def test_duplicate_insertion_always_fails_closed(kind: str) -> None:
    duplicate = _object("duplicate", kind)

    assert "duplicate_identity" in {
        violation.code
        for violation in validate_projection(_projection((duplicate, duplicate)))
    }


@given(value=st.sampled_from((float("nan"), float("inf"), -float("inf"))))
def test_malformed_canonical_values_are_rejected_before_validation(value: float) -> None:
    with pytest.raises(ValueError, match="finite canonical values"):
        _object("malformed", "world", {"value": value})
