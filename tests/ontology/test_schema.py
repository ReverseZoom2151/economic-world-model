"""Executable specification of the canonical ontology schema and its invariants."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import pytest

from ewm.ontology import (
    Measurement,
    OntologyObject,
    OntologyProjection,
    OntologyRef,
    RelationAssertion,
    SourceLocator,
)
from ewm.ontology.schema import (
    OBJECT_SPECS,
    RELATION_SPECS,
    OntologyValidationError,
    assert_valid_projection,
    validate_projection,
)

_DIGEST = "a" * 64
_RUN_REF = OntologyRef("ewm:test:run:1", "run")
_WORLD_REF = OntologyRef("ewm:test:world:1", "world")
_LAYERS = {
    "agent": "economic_declaration",
    "certificate": "learning_equilibrium",
    "claim": "research_evidence",
    "dataset": "learning_equilibrium",
    "ddge_candidate": "learning_equilibrium",
    "evidence_artifact": "research_evidence",
    "fixed_point_candidate": "learning_equilibrium",
    "inner_equilibrium": "learning_equilibrium",
    "intervention": "economic_declaration",
    "market": "economic_declaration",
    "measurement": "research_evidence",
    "model_version": "learning_equilibrium",
    "parameter_version": "learning_equilibrium",
    "projection": "provenance",
    "realized_intervention": "runtime_occurrence",
    "residual": "learning_equilibrium",
    "rollout": "runtime_occurrence",
    "run": "runtime_occurrence",
    "step": "runtime_occurrence",
    "training_run": "learning_equilibrium",
    "world": "economic_declaration",
    "action_occurrence": "runtime_occurrence",
}


def _source(source_kind: str = "verified_run") -> SourceLocator:
    return SourceLocator(
        source_kind=source_kind,
        source_id="run-sha256",
        artifact_path="run/events.jsonl",
        record_selector="event_sequence=1",
        payload_digest=_DIGEST,
    )


def _object(
    suffix: str,
    kind: str,
    *,
    layer: str | None = None,
    properties: Mapping[str, object] | None = None,
    source_kind: str = "verified_run",
) -> OntologyObject:
    return OntologyObject(
        ref=OntologyRef(f"ewm:test:{kind}:{suffix}", kind),
        layer=layer or _LAYERS[kind],
        properties=properties or {},
        sources=(_source(source_kind),),
    )


def _relation(
    suffix: str,
    relation_type: str,
    source: OntologyRef,
    target: OntologyRef,
) -> RelationAssertion:
    return RelationAssertion(
        ref=OntologyRef(f"ewm:test:relation:{suffix}", "relation_assertion"),
        relation_type=relation_type,
        source=source,
        target=target,
        properties={},
        sources=(_source(),),
    )


def _projection(
    *,
    objects: Iterable[OntologyObject] = (),
    relations: Iterable[RelationAssertion] = (),
    measurements: Iterable[Measurement] = (),
    source_run: OntologyRef = _RUN_REF,
) -> OntologyProjection:
    world = OntologyObject(
        ref=_WORLD_REF,
        layer="economic_declaration",
        properties={"natural_key": "test-world"},
        sources=(_source("scenario_adapter"),),
    )
    if source_run == _RUN_REF:
        run = OntologyObject(
            ref=_RUN_REF,
            layer="runtime_occurrence",
            properties={"natural_key": "test-run"},
            sources=(_source(),),
        )
    else:
        run = OntologyObject(
            ref=source_run,
            layer=_LAYERS[source_run.kind],
            properties={},
            sources=(_source("derived_projection"),),
        )
    return OntologyProjection(
        schema="ewm.ontology.v1",
        source_run=source_run,
        objects=(world, run, *objects),
        relations=tuple(relations),
        measurements=tuple(measurements),
        coverage=(),
        projection_digest="b" * 64,
    )


def _codes(projection: OntologyProjection) -> set[str]:
    return {violation.code for violation in validate_projection(projection)}


def test_registry_exposes_all_six_layers_and_canonical_relation_families() -> None:
    assert {spec.layer for spec in OBJECT_SPECS.values()} == {
        "schema",
        "economic_declaration",
        "runtime_occurrence",
        "learning_equilibrium",
        "research_evidence",
        "provenance",
    }
    assert {
        "INSTANTIATES",
        "GENERATES",
        "TRAINS",
        "HAS_CANDIDATE",
        "CERTIFIES",
        "SUPPORTS",
        "DERIVED_FROM",
        "GEO_ANCHORED_AT",
    } <= RELATION_SPECS.keys()


def test_minimal_projection_satisfies_all_fourteen_invariants() -> None:
    projection = _projection()

    assert validate_projection(projection) == ()
    assert_valid_projection(projection)


def test_invariant_1_rejects_duplicate_natural_identity() -> None:
    first = _object("1", "agent", properties={"natural_key": "forecaster"})
    second = _object("2", "agent", properties={"natural_key": "forecaster"})

    assert "duplicate_natural_identity" in _codes(_projection(objects=(first, second)))


def test_invariant_2_rejects_unresolved_references() -> None:
    missing = OntologyRef("ewm:test:market:missing", "market")
    relation = _relation("missing", "PARTICIPATES_IN", _WORLD_REF, missing)

    assert "unresolved_reference" in _codes(_projection(relations=(relation,)))


def test_invariant_3_enforces_relation_direction_and_cardinality() -> None:
    agent = _object("1", "agent")
    market = _object("1", "market")
    backwards = _relation("backwards", "PARTICIPATES_IN", market.ref, agent.ref)
    first = _object("1", "step")
    second = _object("2", "step")
    third = _object("3", "step")
    next_a = _relation("next-a", "PRECEDES", first.ref, second.ref)
    next_b = _relation("next-b", "PRECEDES", first.ref, third.ref)

    codes = _codes(
        _projection(
            objects=(agent, market, first, second, third),
            relations=(backwards, next_a, next_b),
        )
    )

    assert "invalid_relation_direction" in codes
    assert "relation_cardinality" in codes


def test_invariant_4_runtime_assertions_trace_to_verified_run() -> None:
    occurrence = _object("1", "action_occurrence", source_kind="scenario_adapter")

    assert "runtime_without_verified_source" in _codes(_projection(objects=(occurrence,)))


def test_invariant_5_rejects_kind_layer_conflation() -> None:
    conflated = _object("1", "agent", layer="runtime_occurrence")

    assert "kind_layer_mismatch" in _codes(_projection(objects=(conflated,)))


def test_invariant_6_requires_runtime_declarations_to_be_instantiated() -> None:
    occurrence = _object("1", "action_occurrence")

    assert "missing_instantiation" in _codes(_projection(objects=(occurrence,)))


def test_invariant_7_keeps_projection_separate_from_sealed_run() -> None:
    projection_ref = OntologyRef("ewm:test:projection:source", "projection")

    assert "invalid_source_run" in _codes(_projection(source_run=projection_ref))


def test_invariant_8_keeps_numerical_and_certified_roles_distinct() -> None:
    conflated = _object(
        "1",
        "rollout",
        properties={"semantic_roles": ["rollout", "ddge_candidate"]},
    )

    assert "conflated_solution_roles" in _codes(_projection(objects=(conflated,)))


def test_invariant_9_preserves_set_valued_correspondence_candidates() -> None:
    correspondence = _object(
        "1",
        "inner_equilibrium",
        properties={"candidate_count": 2, "selector": "first_by_parameter"},
    )
    candidate = _object("1", "fixed_point_candidate")
    one_candidate = _relation(
        "candidate-1",
        "HAS_CANDIDATE",
        correspondence.ref,
        candidate.ref,
    )

    assert "collapsed_correspondence" in _codes(
        _projection(objects=(correspondence, candidate), relations=(one_candidate,))
    )


def test_invariant_10_requires_explicit_coverage_for_closure_gaps() -> None:
    training_run = _object("1", "training_run")

    assert "undocumented_closure_gap" in _codes(_projection(objects=(training_run,)))


def test_invariant_11_requires_complete_residual_semantics() -> None:
    residual = _object("1", "residual", properties={"value": 0.1})

    assert "incomplete_residual" in _codes(_projection(objects=(residual,)))


def test_invariant_12_rejects_uncertified_distance_or_welfare_bounds() -> None:
    residual = _object(
        "1",
        "residual",
        properties={
            "value": [0.1],
            "norm": 0.1,
            "tolerance": 1e-6,
            "solver": "newton",
            "stopping_rule": "norm <= tolerance",
            "status": "diagnostic_only",
        },
    )
    bound = Measurement(
        ref=OntologyRef("ewm:test:measurement:bound", "measurement"),
        subject=residual.ref,
        name="distance_bound",
        value=0.2,
        unit="1",
        status="diagnostic_only",
        sample={},
        uncertainty={},
        sources=(_source(),),
    )

    assert "uncertified_bound" in _codes(
        _projection(objects=(residual,), measurements=(bound,))
    )


def test_invariant_13_separates_declared_realized_and_observed_interventions() -> None:
    realized = _object("1", "realized_intervention")

    assert "incomplete_intervention_chain" in _codes(_projection(objects=(realized,)))


def test_invariant_14_rejects_claims_without_matching_authorizing_evidence() -> None:
    claim = _object(
        "1",
        "claim",
        properties={"evidence_classification": "synthetic_conformance"},
    )

    violations = validate_projection(_projection(objects=(claim,)))

    assert "unsupported_claim" in {violation.code for violation in violations}
    with pytest.raises(OntologyValidationError) as error:
        assert_valid_projection(_projection(objects=(claim,)))
    assert error.value.violations == violations


def test_matching_evidence_authorizes_claim_without_changing_its_classification() -> None:
    claim = _object(
        "1",
        "claim",
        properties={"evidence_classification": "synthetic_conformance"},
    )
    evidence = _object(
        "1",
        "evidence_artifact",
        properties={"evidence_classification": "synthetic_conformance"},
    )
    support = _relation("support", "SUPPORTS", evidence.ref, claim.ref)

    assert validate_projection(_projection(objects=(claim, evidence), relations=(support,))) == ()


def test_violations_are_structured_and_deterministically_sorted() -> None:
    agent = _object("2", "agent", layer="runtime_occurrence")
    claim = _object("1", "claim", properties={"evidence_classification": "not_measured"})

    violations = validate_projection(_projection(objects=(claim, agent)))

    assert violations == tuple(
        sorted(
            violations,
            key=lambda violation: (
                violation.invariant,
                violation.record_id,
                violation.source_location,
                violation.code,
            ),
        )
    )
    assert all(1 <= violation.invariant <= 14 for violation in violations)

