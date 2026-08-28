"""Value-object contract for the canonical ontology model."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ewm.ontology import (
    CoverageEntry,
    Measurement,
    OntologyObject,
    OntologyProjection,
    OntologyRef,
    RelationAssertion,
    SourceLocator,
)


def _source(**overrides: object) -> SourceLocator:
    values: dict[str, object] = {
        "source_kind": "verified_run",
        "source_id": "sha256:run",
        "artifact_path": "runs/example/events.jsonl",
        "record_selector": "event_sequence=1",
        "payload_digest": "a" * 64,
    }
    values.update(overrides)
    return SourceLocator(**values)  # type: ignore[arg-type]


def _object(ref_id: str = "ewm:test:run:1") -> OntologyObject:
    return OntologyObject(
        ref=OntologyRef(ref_id, "run"),
        layer="runtime_occurrence",
        properties={"nested": {"values": [1, 2]}},
        sources=(_source(),),
    )


def test_ontology_refs_validate_and_have_deterministic_ordering() -> None:
    refs = (
        OntologyRef("ewm:test:world:2", "world"),
        OntologyRef("ewm:test:agent:1", "agent"),
    )

    assert tuple(ref.id for ref in sorted(refs)) == (
        "ewm:test:agent:1",
        "ewm:test:world:2",
    )
    with pytest.raises(ValueError, match="id"):
        OntologyRef("  ", "world")
    with pytest.raises(ValueError, match="kind"):
        OntologyRef("ewm:test:world:1", "")


@pytest.mark.parametrize(
    "path",
    (
        "/tmp/run/manifest.json",
        r"C:\Users\researcher\run\manifest.json",
        r"\\server\share\run\manifest.json",
    ),
)
def test_source_locators_reject_absolute_exported_paths(path: str) -> None:
    with pytest.raises(ValueError, match="relative"):
        _source(artifact_path=path)


def test_source_locators_normalize_portable_relative_paths() -> None:
    locator = _source(artifact_path=r"runs\example\.\events.jsonl")

    assert locator.artifact_path == "runs/example/events.jsonl"


def test_ontology_properties_are_recursively_immutable_and_owned() -> None:
    source_properties = {"nested": {"values": [1, 2]}}
    ontology_object = OntologyObject(
        ref=OntologyRef("ewm:test:agent:1", "agent"),
        layer="economic_declaration",
        properties=source_properties,
        sources=(_source(),),
    )
    source_properties["nested"] = {"values": [99]}

    assert ontology_object.properties["nested"]["values"] == (1, 2)  # type: ignore[index]
    with pytest.raises(TypeError):
        ontology_object.properties["new"] = "value"  # type: ignore[index]
    with pytest.raises(TypeError):
        ontology_object.properties["nested"]["new"] = "value"  # type: ignore[index]


@pytest.mark.parametrize("value", (True, float("nan"), float("inf"), -float("inf")))
def test_measurements_reject_boolean_and_non_finite_values(value: object) -> None:
    with pytest.raises(ValueError, match="measurement value"):
        Measurement(
            ref=OntologyRef("ewm:test:measurement:1", "measurement"),
            subject=OntologyRef("ewm:test:run:1", "run"),
            name="residual",
            value=value,
            unit="1",
            status="observed",
            sample={},
            uncertainty={},
            sources=(_source(),),
        )


def test_canonical_records_construct_as_one_immutable_projection() -> None:
    source = _source()
    run = _object()
    agent = OntologyObject(
        ref=OntologyRef("ewm:test:agent:1", "agent"),
        layer="economic_declaration",
        properties={"role": "forecaster"},
        sources=(source,),
    )
    relation = RelationAssertion(
        ref=OntologyRef("ewm:test:relation:1", "relation_assertion"),
        relation_type="PARTICIPATES_IN",
        source=agent.ref,
        target=run.ref,
        properties={},
        sources=(source,),
    )
    measurement = Measurement(
        ref=OntologyRef("ewm:test:measurement:1", "measurement"),
        subject=run.ref,
        name="residual",
        value=(0.0, 0.25),
        unit="1",
        status="observed",
        sample={"count": 2},
        uncertainty={"standard_error": 0.1},
        sources=(source,),
    )
    coverage = CoverageEntry(
        source=source,
        field="events[1]",
        status="projected",
        targets=(run.ref, measurement.ref),
        reason=None,
    )
    projection = OntologyProjection(
        schema="ewm.ontology.v1",
        source_run=run.ref,
        objects=(run, agent),
        relations=(relation,),
        measurements=(measurement,),
        coverage=(coverage,),
        projection_digest="b" * 64,
    )

    assert projection.objects == (run, agent)
    assert projection.coverage[0].targets == (run.ref, measurement.ref)
    assert measurement.value == (0.0, 0.25)
    with pytest.raises(FrozenInstanceError):
        projection.schema = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        relation.relation_type = "CHANGED"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("factory", "message"),
    (
        (
            lambda: OntologyObject(
                ref=OntologyRef("ewm:test:agent:1", "agent"),
                layer="invalid",
                properties={},
                sources=(_source(),),
            ),
            "layer",
        ),
        (
            lambda: CoverageEntry(
                source=_source(),
                field="events[1]",
                status="invented",
                targets=(),
                reason=None,
            ),
            "coverage status",
        ),
    ),
)
def test_records_reject_unknown_closed_vocabulary(
    factory: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        factory()  # type: ignore[operator]
