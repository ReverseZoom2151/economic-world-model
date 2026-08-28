"""Conformance boundaries for DDGE and learning-closure ontology semantics."""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from ewm.ontology import OntologyObject, OntologyProjection, OntologyRef, RelationAssertion
from ewm.ontology.graph.schema import OBJECT_SPECS, RELATION_SPECS
from ewm.ontology.projection.compiler import ProjectionCompilation

pytestmark = pytest.mark.conformance

_SOLUTION_KINDS = frozenset(
    {
        "rollout",
        "inner_equilibrium",
        "equilibrium_witness",
        "fixed_point_candidate",
        "ddge_candidate",
        "numerical_validation",
        "certificate",
        "certified_result",
    }
)


def _objects(
    projection: OntologyProjection,
    kind: str,
) -> tuple[OntologyObject, ...]:
    return tuple(item for item in projection.objects if item.ref.kind == kind)


def _relations(
    projection: OntologyProjection,
    relation_type: str,
) -> tuple[RelationAssertion, ...]:
    return tuple(
        item for item in projection.relations if item.relation_type == relation_type
    )


def _targets(
    relations: Iterable[RelationAssertion],
    source: OntologyRef,
) -> tuple[OntologyRef, ...]:
    return tuple(item.target for item in relations if item.source == source)


def test_schema_separates_numerical_validation_from_certification() -> None:
    assert "numerical_validation" in OBJECT_SPECS
    assert "certificate" in OBJECT_SPECS
    assert "VALIDATES" in RELATION_SPECS
    assert OBJECT_SPECS["numerical_validation"].layer == "learning_equilibrium"
    assert OBJECT_SPECS["certificate"].layer == "learning_equilibrium"


@pytest.mark.parametrize(
    "fixture_name",
    ("scalar_projection", "forecasting_projection", "fx_projection"),
)
def test_solution_roles_remain_distinct_objects(
    fixture_name: str,
    request: pytest.FixtureRequest,
) -> None:
    compilation: ProjectionCompilation = request.getfixturevalue(fixture_name)
    solution_objects = tuple(
        item
        for item in compilation.projection.objects
        if item.ref.kind in _SOLUTION_KINDS
    )

    assert solution_objects
    for item in solution_objects:
        raw_roles = item.properties.get("semantic_roles", (item.ref.kind,))
        roles = {raw_roles} if isinstance(raw_roles, str) else set(raw_roles)
        assert roles & _SOLUTION_KINDS == {item.ref.kind}


@pytest.mark.parametrize(
    "fixture_name",
    ("scalar_projection", "forecasting_projection"),
)
def test_ddge_multiplicity_and_selector_metadata_survive_projection(
    fixture_name: str,
    request: pytest.FixtureRequest,
) -> None:
    compilation: ProjectionCompilation = request.getfixturevalue(fixture_name)
    projection = compilation.projection
    correspondence = _objects(projection, "inner_equilibrium")[0]
    candidate_relations = tuple(
        item
        for item in _relations(projection, "HAS_CANDIDATE")
        if item.source == correspondence.ref
    )

    assert correspondence.properties["candidate_count"] == len(candidate_relations)
    assert len(candidate_relations) > 1
    assert correspondence.properties["selector"]
    assert all(
        item.properties["selector"] == correspondence.properties["selector"]
        for item in candidate_relations
    )


def test_scalar_residual_vectors_and_numerical_validations_survive_projection(
    scalar_projection: ProjectionCompilation,
) -> None:
    projection = scalar_projection.projection
    candidates = _objects(projection, "ddge_candidate")
    residuals = _objects(projection, "residual")
    validations = _objects(projection, "numerical_validation")
    residual_links = _relations(projection, "HAS_RESIDUAL")
    validation_links = _relations(projection, "VALIDATES")

    assert len(candidates) == len(residuals) == len(validations) == 3
    for candidate in candidates:
        linked_residuals = _targets(residual_links, candidate.ref)
        assert len(linked_residuals) == 1
        assert candidate.ref in {
            target
            for validation in validations
            for target in _targets(validation_links, validation.ref)
        }
    for residual in residuals:
        assert isinstance(residual.properties["value"], tuple)
        assert len(residual.properties["value"]) == 1
        assert residual.properties["norm"] >= 0.0
        assert residual.properties["tolerance"] > 0.0
        assert residual.properties["solver"]
        assert residual.properties["stopping_rule"]


def test_forecasting_projection_contains_typed_learning_closure(
    forecasting_projection: ProjectionCompilation,
) -> None:
    projection = forecasting_projection.projection
    actions = _objects(projection, "action_occurrence")
    data = _objects(projection, "generated_datum")
    datasets = _objects(projection, "dataset")
    training_runs = _objects(projection, "training_run")
    learners = _objects(projection, "learner")
    models = _objects(projection, "model_version")
    parameters = _objects(projection, "parameter_version")

    assert actions and data and learners
    assert len(datasets) == len(training_runs) == len(models) == 1
    assert parameters
    for action in actions:
        generated = _targets(_relations(projection, "GENERATES"), action.ref)
        assert generated
        for datum in generated:
            assert datum.kind == "generated_datum"
            included = _targets(_relations(projection, "INCLUDED_IN"), datum)
            assert included == (datasets[0].ref,)
    assert _targets(_relations(projection, "TRAINS"), datasets[0].ref) == (
        training_runs[0].ref,
    )
    assert _targets(_relations(projection, "TRAINS"), learners[0].ref) == (
        training_runs[0].ref,
    )
    assert _targets(_relations(projection, "PRODUCES"), training_runs[0].ref) == (
        models[0].ref,
    )
    assert set(_targets(_relations(projection, "DEPLOYS"), models[0].ref)) == {
        item.ref for item in parameters
    }


def test_fx_clearings_retain_accounting_residuals_without_becoming_certificates(
    fx_projection: ProjectionCompilation,
) -> None:
    projection = fx_projection.projection
    rollouts = _objects(projection, "rollout")
    clearings = _objects(projection, "inner_equilibrium")
    witnesses = _objects(projection, "equilibrium_witness")
    residuals = _objects(projection, "residual")
    validations = _objects(projection, "numerical_validation")

    assert len(rollouts) == 1
    assert len(clearings) == len(witnesses) == len(residuals) == len(validations)
    assert not _objects(projection, "certificate")
    assert not _objects(projection, "certified_result")
    assert not _relations(projection, "CERTIFIES")
    for residual in residuals:
        assert len(residual.properties["value"]) == 3
        assert residual.properties["norm"] == max(
            abs(float(value)) for value in residual.properties["value"]
        )
        assert residual.properties["status"] == "within_tolerance"


def test_uncertified_bounds_remain_explicitly_unavailable(
    scalar_projection: ProjectionCompilation,
    forecasting_projection: ProjectionCompilation,
) -> None:
    for compilation, field in (
        (scalar_projection, "adapter.scalar.distance_bound"),
        (forecasting_projection, "adapter.forecasting.welfare_bound"),
    ):
        projection = compilation.projection
        coverage = {item.field: item for item in projection.coverage}
        bound_names = {
            item.name
            for item in projection.measurements
            if item.name in {"distance_bound", "welfare_bound"}
        }

        assert coverage[field].status == "unavailable"
        assert not bound_names
        assert not _objects(projection, "certificate")
