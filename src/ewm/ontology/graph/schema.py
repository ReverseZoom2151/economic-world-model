"""Ontology vocabulary and cross-record scientific invariants."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from types import MappingProxyType
from typing import Any

from ewm.core.provenance.serialization import canonical_json

from .model import (
    GEO_ANCHOR_BASES,
    GEO_COORDINATE_REFERENCE_SYSTEMS,
    GEO_EVIDENCE_CLASSIFICATIONS,
    Measurement,
    OntologyObject,
    OntologyProjection,
    OntologyRef,
    RelationAssertion,
    SourceLocator,
)


@dataclass(frozen=True, slots=True)
class ObjectSpec:
    """Layer and required semantics for one canonical object kind."""

    kind: str
    layer: str
    required_properties: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RelationSpec:
    """Allowed direction and cardinality for one canonical relation."""

    relation_type: str
    source_kinds: frozenset[str]
    target_kinds: frozenset[str]
    max_outgoing: int | None = None
    max_incoming: int | None = None


@dataclass(frozen=True, slots=True)
class SchemaViolation:
    """One deterministic, machine-readable ontology validation failure."""

    invariant: int
    code: str
    message: str
    record_id: str
    source_location: str


class OntologyValidationError(ValueError):
    """Raised when a projection violates the canonical ontology schema."""

    def __init__(self, violations: tuple[SchemaViolation, ...]) -> None:
        self.violations = violations
        summary = "; ".join(
            f"I{violation.invariant}:{violation.code}:{violation.record_id}"
            for violation in violations
        )
        super().__init__(f"ontology projection is invalid: {summary}")


_KINDS_BY_LAYER: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "schema": (
            "object_type",
            "relation_type",
            "property_specification",
            "profile",
            "invariant",
        ),
        "economic_declaration": (
            "world",
            "agent",
            "institution",
            "market",
            "asset",
            "action",
            "belief",
            "objective",
            "constraint",
            "mechanism",
            "kernel",
            "learner",
            "intervention",
        ),
        "runtime_occurrence": (
            "run",
            "episode",
            "step",
            "rollout",
            "state_observation",
            "action_occurrence",
            "mechanism_invocation",
            "transaction",
            "outcome",
            "generated_datum",
            "realized_intervention",
        ),
        "learning_equilibrium": (
            "dataset",
            "training_run",
            "model_version",
            "parameter_version",
            "inner_equilibrium",
            "equilibrium_witness",
            "fixed_point_candidate",
            "ddge_candidate",
            "residual",
            "numerical_validation",
            "certificate",
            "certified_result",
            "basin",
            "stability_diagnostic",
        ),
        "research_evidence": (
            "experiment",
            "protocol",
            "comparison",
            "estimand",
            "measurement",
            "claim",
            "evidence_artifact",
            "limitation",
            "readiness_assessment",
        ),
        "provenance": (
            "projection",
            "coverage_entry",
            "source_locator",
            "derivation",
            "software_identity",
            "digest",
            "paper_anchor",
            "external_source",
            "geo_anchor",
        ),
    }
)

_REQUIRED_PROPERTIES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "residual": ("value", "norm", "tolerance", "solver", "stopping_rule", "status"),
        "claim": ("evidence_classification",),
        "geo_anchor": (
            "crs",
            "latitude",
            "longitude",
            "anchor_basis",
            "evidence_classification",
            "validity",
            "uncertainty_km",
        ),
    }
)

OBJECT_SPECS: Mapping[str, ObjectSpec] = MappingProxyType(
    {
        kind: ObjectSpec(
            kind=kind,
            layer=layer,
            required_properties=_REQUIRED_PROPERTIES.get(kind, ()),
        )
        for layer, kinds in _KINDS_BY_LAYER.items()
        for kind in kinds
    }
)

_ALL_KINDS = frozenset(OBJECT_SPECS)
_DECLARATION_KINDS = frozenset(_KINDS_BY_LAYER["economic_declaration"])
_RUNTIME_KINDS = frozenset(_KINDS_BY_LAYER["runtime_occurrence"])
_LEARNING_KINDS = frozenset(_KINDS_BY_LAYER["learning_equilibrium"])
_RESEARCH_KINDS = frozenset(_KINDS_BY_LAYER["research_evidence"])


def _relation_spec(
    relation_type: str,
    source_kinds: Iterable[str],
    target_kinds: Iterable[str],
    *,
    max_outgoing: int | None = None,
    max_incoming: int | None = None,
) -> RelationSpec:
    return RelationSpec(
        relation_type=relation_type,
        source_kinds=frozenset(source_kinds),
        target_kinds=frozenset(target_kinds),
        max_outgoing=max_outgoing,
        max_incoming=max_incoming,
    )


RELATION_SPECS: Mapping[str, RelationSpec] = MappingProxyType(
    {
        "DECLARES": _relation_spec("DECLARES", {"world"}, _DECLARATION_KINDS - {"world"}),
        "CONTAINS": _relation_spec("CONTAINS", _ALL_KINDS, _ALL_KINDS),
        "PARTICIPATES_IN": _relation_spec("PARTICIPATES_IN", {"agent"}, {"market"}),
        "SUBJECT_TO": _relation_spec(
            "SUBJECT_TO",
            {"world", "agent", "institution", "market", "action"},
            {"constraint"},
        ),
        "OBSERVES": _relation_spec(
            "OBSERVES",
            {"agent", "learner"},
            {"state_observation", "generated_datum", "outcome"},
        ),
        "OPTIMIZES": _relation_spec("OPTIMIZES", {"agent"}, {"objective"}),
        "GOVERNED_BY": _relation_spec(
            "GOVERNED_BY",
            {"world", "market", "action"},
            {"institution", "mechanism", "kernel"},
        ),
        "INSTANTIATES": _relation_spec(
            "INSTANTIATES",
            _RUNTIME_KINDS,
            _DECLARATION_KINDS,
            max_outgoing=1,
        ),
        "PRECEDES": _relation_spec(
            "PRECEDES",
            _RUNTIME_KINDS,
            _RUNTIME_KINDS,
            max_outgoing=1,
            max_incoming=1,
        ),
        "CHOOSES": _relation_spec("CHOOSES", {"agent"}, {"action_occurrence"}),
        "ACTS_ON": _relation_spec(
            "ACTS_ON", {"action_occurrence"}, {"world", "market", "asset"}
        ),
        "INVOKES": _relation_spec(
            "INVOKES",
            {"step", "action_occurrence"},
            {"mechanism", "mechanism_invocation"},
        ),
        "TRANSITIONS_TO": _relation_spec(
            "TRANSITIONS_TO", {"state_observation"}, {"state_observation"}
        ),
        "CLEARS": _relation_spec("CLEARS", {"mechanism_invocation"}, {"market"}),
        "REALIZES": _relation_spec(
            "REALIZES",
            {"mechanism_invocation", "realized_intervention"},
            {"outcome", "transaction"},
        ),
        "GENERATES": _relation_spec(
            "GENERATES",
            {"run", "episode", "step", "action_occurrence", "outcome"},
            {"generated_datum"},
        ),
        "INCLUDED_IN": _relation_spec("INCLUDED_IN", {"generated_datum"}, {"dataset"}),
        "TRAINS": _relation_spec("TRAINS", {"dataset", "learner"}, {"training_run"}),
        "PRODUCES": _relation_spec(
            "PRODUCES",
            {"training_run", "experiment", "protocol"},
            {"model_version", "evidence_artifact", "measurement"},
        ),
        "DEPLOYS": _relation_spec(
            "DEPLOYS", {"model_version"}, {"parameter_version", "run"}
        ),
        "UPDATES": _relation_spec(
            "UPDATES", {"model_version", "parameter_version"}, {"parameter_version"}
        ),
        "HAS_CANDIDATE": _relation_spec(
            "HAS_CANDIDATE",
            {"run", "inner_equilibrium", "parameter_version"},
            {"equilibrium_witness", "fixed_point_candidate", "ddge_candidate"},
        ),
        "WITNESSED_BY": _relation_spec(
            "WITNESSED_BY",
            {"inner_equilibrium", "fixed_point_candidate", "ddge_candidate"},
            {"equilibrium_witness"},
        ),
        "SATISFIES": _relation_spec(
            "SATISFIES",
            {"equilibrium_witness", "fixed_point_candidate", "ddge_candidate"},
            {"constraint"},
        ),
        "HAS_RESIDUAL": _relation_spec(
            "HAS_RESIDUAL",
            {"equilibrium_witness", "fixed_point_candidate", "ddge_candidate"},
            {"residual"},
        ),
        "VALIDATES": _relation_spec(
            "VALIDATES",
            {"numerical_validation"},
            {
                "inner_equilibrium",
                "equilibrium_witness",
                "fixed_point_candidate",
                "ddge_candidate",
                "residual",
            },
        ),
        "HAS_BASIN": _relation_spec(
            "HAS_BASIN", {"fixed_point_candidate", "ddge_candidate"}, {"basin"}
        ),
        "CERTIFIES": _relation_spec(
            "CERTIFIES",
            {"certificate"},
            {
                "equilibrium_witness",
                "fixed_point_candidate",
                "ddge_candidate",
                "residual",
                "measurement",
                "certified_result",
            },
        ),
        "MEASURES": _relation_spec(
            "MEASURES", {"experiment", "protocol", "estimand"}, {"measurement"}
        ),
        "COMPARES": _relation_spec(
            "COMPARES", {"comparison"}, {"experiment", "measurement", "estimand"}
        ),
        "SUPPORTS": _relation_spec("SUPPORTS", {"evidence_artifact"}, {"claim"}),
        "LIMITS": _relation_spec("LIMITS", {"limitation"}, {"claim"}),
        "ASSESSES": _relation_spec(
            "ASSESSES",
            {"readiness_assessment"},
            {"claim", "model_version", "ddge_candidate"},
        ),
        "DERIVED_FROM": _relation_spec("DERIVED_FROM", _ALL_KINDS, _ALL_KINDS),
        "LOCATED_AT": _relation_spec(
            "LOCATED_AT", _ALL_KINDS, {"source_locator", "paper_anchor"}
        ),
        "VERIFIED_BY": _relation_spec(
            "VERIFIED_BY",
            _ALL_KINDS,
            {"evidence_artifact", "certificate", "digest"},
        ),
        "GEO_ANCHORED_AT": _relation_spec(
            "GEO_ANCHORED_AT", _ALL_KINDS - {"geo_anchor"}, {"geo_anchor"}, max_outgoing=1
        ),
    }
)

_RUNTIME_RELATIONS = frozenset(
    {
        "INSTANTIATES",
        "PRECEDES",
        "CHOOSES",
        "ACTS_ON",
        "INVOKES",
        "TRANSITIONS_TO",
        "CLEARS",
        "REALIZES",
        "GENERATES",
    }
)
_DISTINCT_SOLUTION_ROLES = frozenset(
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
_CLOSURE_RELATIONS = (
    "GENERATES",
    "INCLUDED_IN",
    "TRAINS",
    "PRODUCES",
    "DEPLOYS",
)
_CLOSURE_KINDS = frozenset(
    {"generated_datum", "dataset", "training_run", "model_version", "parameter_version"}
)
_INSTANTIATION_TARGETS: Mapping[str, str] = MappingProxyType(
    {"action_occurrence": "action", "mechanism_invocation": "mechanism"}
)


def _locator_text(locator: SourceLocator) -> str:
    location = (
        locator.artifact_path
        or locator.code_symbol
        or locator.paper_anchor
        or locator.source_id
    )
    if locator.record_selector:
        return f"{location}#{locator.record_selector}"
    return location


def _source_location(sources: Sequence[SourceLocator]) -> str:
    if not sources:
        return ""
    return min(_locator_text(source) for source in sources)


def _violation(
    invariant: int,
    code: str,
    message: str,
    record_id: str,
    sources: Sequence[SourceLocator] = (),
) -> SchemaViolation:
    return SchemaViolation(
        invariant=invariant,
        code=code,
        message=message,
        record_id=record_id,
        source_location=_source_location(sources),
    )


def _sort_violations(violations: Iterable[SchemaViolation]) -> tuple[SchemaViolation, ...]:
    return tuple(
        sorted(
            violations,
            key=lambda violation: (
                violation.invariant,
                violation.record_id,
                violation.source_location,
                violation.code,
                violation.message,
            ),
        )
    )


def _all_records(
    projection: OntologyProjection,
) -> tuple[OntologyObject | RelationAssertion | Measurement, ...]:
    return (*projection.objects, *projection.relations, *projection.measurements)


def _validate_identity(projection: OntologyProjection) -> list[SchemaViolation]:
    violations: list[SchemaViolation] = []
    records_by_id: dict[str, list[OntologyObject | RelationAssertion | Measurement]] = defaultdict(
        list
    )
    for record in _all_records(projection):
        records_by_id[record.ref.id].append(record)
    for record_id, records in records_by_id.items():
        if len(records) > 1:
            violations.append(
                _violation(
                    1,
                    "duplicate_identity",
                    "stored ontology identities must be unique",
                    record_id,
                    records[0].sources,
                )
            )

    natural_keys: dict[tuple[str, str], list[OntologyObject]] = defaultdict(list)
    for ontology_object in projection.objects:
        if "natural_key" in ontology_object.properties:
            key = canonical_json(ontology_object.properties["natural_key"])
            natural_keys[(ontology_object.ref.kind, key)].append(ontology_object)
    for (kind, _key), objects in natural_keys.items():
        if len(objects) > 1:
            record_id = min(ontology_object.ref.id for ontology_object in objects)
            violations.append(
                _violation(
                    1,
                    "duplicate_natural_identity",
                    f"kind {kind!r} has a duplicate canonical natural key",
                    record_id,
                    min(objects, key=lambda item: item.ref.id).sources,
                )
            )
    return violations


def _reference_index(projection: OntologyProjection) -> Mapping[str, frozenset[OntologyRef]]:
    refs: dict[str, set[OntologyRef]] = defaultdict(set)
    for record in _all_records(projection):
        refs[record.ref.id].add(record.ref)
    return {record_id: frozenset(group) for record_id, group in refs.items()}


def _is_resolved(ref: OntologyRef, index: Mapping[str, frozenset[OntologyRef]]) -> bool:
    return ref in index.get(ref.id, frozenset())


def _validate_references(projection: OntologyProjection) -> list[SchemaViolation]:
    violations: list[SchemaViolation] = []
    index = _reference_index(projection)
    references: list[tuple[OntologyRef, str, Sequence[SourceLocator]]] = [
        (projection.source_run, projection.source_run.id, ())
    ]
    references.extend(
        (relation.source, relation.ref.id, relation.sources)
        for relation in projection.relations
    )
    references.extend(
        (relation.target, relation.ref.id, relation.sources)
        for relation in projection.relations
    )
    references.extend(
        (measurement.subject, measurement.ref.id, measurement.sources)
        for measurement in projection.measurements
    )
    references.extend(
        (target, coverage.field, (coverage.source,))
        for coverage in projection.coverage
        for target in coverage.targets
    )
    for ref, owner_id, sources in references:
        if not _is_resolved(ref, index):
            violations.append(
                _violation(
                    2,
                    "unresolved_reference",
                    f"reference {ref.id!r} of kind {ref.kind!r} does not resolve",
                    owner_id,
                    sources,
                )
            )
    return violations


def _validate_relations(projection: OntologyProjection) -> list[SchemaViolation]:
    violations: list[SchemaViolation] = []
    outgoing: dict[tuple[str, str], list[RelationAssertion]] = defaultdict(list)
    incoming: dict[tuple[str, str], list[RelationAssertion]] = defaultdict(list)
    for relation in projection.relations:
        spec = RELATION_SPECS.get(relation.relation_type)
        if spec is None:
            violations.append(
                _violation(
                    3,
                    "unknown_relation_type",
                    f"relation type {relation.relation_type!r} is not registered",
                    relation.ref.id,
                    relation.sources,
                )
            )
            continue
        if (
            relation.source.kind not in spec.source_kinds
            or relation.target.kind not in spec.target_kinds
        ):
            violations.append(
                _violation(
                    3,
                    "invalid_relation_direction",
                    (
                        f"{relation.relation_type} does not permit "
                        f"{relation.source.kind} -> {relation.target.kind}"
                    ),
                    relation.ref.id,
                    relation.sources,
                )
            )
        outgoing[(relation.relation_type, relation.source.id)].append(relation)
        incoming[(relation.relation_type, relation.target.id)].append(relation)
    for relation_type, spec in RELATION_SPECS.items():
        if spec.max_outgoing is not None:
            for (group_type, source_id), relations in outgoing.items():
                if group_type == relation_type and len(relations) > spec.max_outgoing:
                    violations.append(
                        _violation(
                            3,
                            "relation_cardinality",
                            f"{relation_type} exceeds outgoing cardinality {spec.max_outgoing}",
                            source_id,
                            min(relations, key=lambda item: item.ref.id).sources,
                        )
                    )
        if spec.max_incoming is not None:
            for (group_type, target_id), relations in incoming.items():
                if group_type == relation_type and len(relations) > spec.max_incoming:
                    violations.append(
                        _violation(
                            3,
                            "relation_cardinality",
                            f"{relation_type} exceeds incoming cardinality {spec.max_incoming}",
                            target_id,
                            min(relations, key=lambda item: item.ref.id).sources,
                        )
                    )
    return violations


def _has_verified_source(sources: Sequence[SourceLocator]) -> bool:
    return any(source.source_kind == "verified_run" for source in sources)


def _validate_sources(projection: OntologyProjection) -> list[SchemaViolation]:
    violations: list[SchemaViolation] = []
    for ontology_object in projection.objects:
        if ontology_object.layer == "runtime_occurrence" and not _has_verified_source(
            ontology_object.sources
        ):
            violations.append(
                _violation(
                    4,
                    "runtime_without_verified_source",
                    "runtime objects must trace to a verified run",
                    ontology_object.ref.id,
                    ontology_object.sources,
                )
            )
    for relation in projection.relations:
        runtime_relation = (
            relation.relation_type in _RUNTIME_RELATIONS
            or relation.source.kind in _RUNTIME_KINDS
            or relation.target.kind in _RUNTIME_KINDS
        )
        if runtime_relation and not _has_verified_source(relation.sources):
            violations.append(
                _violation(
                    4,
                    "runtime_without_verified_source",
                    "runtime relations must trace to a verified run",
                    relation.ref.id,
                    relation.sources,
                )
            )
    for measurement in projection.measurements:
        if measurement.subject.kind in _RUNTIME_KINDS and not _has_verified_source(
            measurement.sources
        ):
            violations.append(
                _violation(
                    4,
                    "runtime_without_verified_source",
                    "runtime measurements must trace to a verified run",
                    measurement.ref.id,
                    measurement.sources,
                )
            )
    return violations


def _validate_layers(projection: OntologyProjection) -> list[SchemaViolation]:
    violations: list[SchemaViolation] = []
    for ontology_object in projection.objects:
        spec = OBJECT_SPECS.get(ontology_object.ref.kind)
        if spec is None:
            violations.append(
                _violation(
                    5,
                    "unknown_object_kind",
                    f"object kind {ontology_object.ref.kind!r} is not registered",
                    ontology_object.ref.id,
                    ontology_object.sources,
                )
            )
        elif ontology_object.layer != spec.layer:
            violations.append(
                _violation(
                    5,
                    "kind_layer_mismatch",
                    f"{ontology_object.ref.kind!r} belongs to layer {spec.layer!r}",
                    ontology_object.ref.id,
                    ontology_object.sources,
                )
            )
    for relation in projection.relations:
        if relation.ref.kind != "relation_assertion":
            violations.append(
                _violation(
                    5,
                    "record_kind_mismatch",
                    "relation records must use kind 'relation_assertion'",
                    relation.ref.id,
                    relation.sources,
                )
            )
    for measurement in projection.measurements:
        if measurement.ref.kind != "measurement":
            violations.append(
                _violation(
                    5,
                    "record_kind_mismatch",
                    "measurement records must use kind 'measurement'",
                    measurement.ref.id,
                    measurement.sources,
                )
            )
    return violations


def _validate_instantiations(projection: OntologyProjection) -> list[SchemaViolation]:
    violations: list[SchemaViolation] = []
    for ontology_object in projection.objects:
        target_kind = _INSTANTIATION_TARGETS.get(ontology_object.ref.kind)
        if target_kind is None:
            continue
        linked = any(
            relation.relation_type == "INSTANTIATES"
            and relation.source == ontology_object.ref
            and relation.target.kind == target_kind
            for relation in projection.relations
        )
        if not linked:
            violations.append(
                _violation(
                    6,
                    "missing_instantiation",
                    f"{ontology_object.ref.kind} must instantiate a declared {target_kind}",
                    ontology_object.ref.id,
                    ontology_object.sources,
                )
            )
    return violations


def _validate_sealed_source_boundary(projection: OntologyProjection) -> list[SchemaViolation]:
    violations: list[SchemaViolation] = []
    if projection.source_run.kind != "run":
        violations.append(
            _violation(
                7,
                "invalid_source_run",
                "a projection source must be a distinct sealed run",
                projection.source_run.id,
            )
        )
    for ontology_object in projection.objects:
        if (
            ontology_object.ref.kind == "projection"
            and ontology_object.ref.id == projection.source_run.id
        ):
            violations.append(
                _violation(
                    7,
                    "projection_overwrites_source",
                    "projection identity must remain separate from source-run identity",
                    ontology_object.ref.id,
                    ontology_object.sources,
                )
            )
        if ontology_object.properties.get("sealed_source_mutated") is True:
            violations.append(
                _violation(
                    7,
                    "projection_overwrites_source",
                    "derived ontology records cannot mutate sealed source content",
                    ontology_object.ref.id,
                    ontology_object.sources,
                )
            )
    return violations


def _semantic_roles(ontology_object: OntologyObject) -> frozenset[str]:
    raw_roles = ontology_object.properties.get("semantic_roles", (ontology_object.ref.kind,))
    if isinstance(raw_roles, str):
        return frozenset({raw_roles})
    if isinstance(raw_roles, Iterable):
        return frozenset(str(role) for role in raw_roles)
    return frozenset({ontology_object.ref.kind})


def _validate_solution_roles(projection: OntologyProjection) -> list[SchemaViolation]:
    violations: list[SchemaViolation] = []
    for ontology_object in projection.objects:
        roles = _semantic_roles(ontology_object) & _DISTINCT_SOLUTION_ROLES
        if len(roles) > 1 or (
            ontology_object.ref.kind in _DISTINCT_SOLUTION_ROLES
            and roles
            and ontology_object.ref.kind not in roles
        ):
            violations.append(
                _violation(
                    8,
                    "conflated_solution_roles",
                    (
                        "rollouts, correspondences, candidates, witnesses, numerical "
                        "validations, certificates, and certified results require distinct "
                        "objects"
                    ),
                    ontology_object.ref.id,
                    ontology_object.sources,
                )
            )
    return violations


def _validate_correspondences(projection: OntologyProjection) -> list[SchemaViolation]:
    violations: list[SchemaViolation] = []
    for correspondence in (
        ontology_object
        for ontology_object in projection.objects
        if ontology_object.ref.kind == "inner_equilibrium"
    ):
        declared_count = correspondence.properties.get("candidate_count")
        candidate_relations = tuple(
            relation
            for relation in projection.relations
            if relation.relation_type == "HAS_CANDIDATE"
            and relation.source == correspondence.ref
        )
        selector = correspondence.properties.get("selector")
        correspondence_is_complete = False
        if isinstance(declared_count, int) and not isinstance(declared_count, bool):
            selector_is_valid = declared_count <= 1 or (
                isinstance(selector, str) and bool(selector.strip())
            )
            correspondence_is_complete = (
                declared_count >= 0
                and declared_count == len(candidate_relations)
                and selector_is_valid
            )
        if not correspondence_is_complete:
            violations.append(
                _violation(
                    9,
                    "collapsed_correspondence",
                    "inner correspondences must preserve every candidate and selector metadata",
                    correspondence.ref.id,
                    correspondence.sources,
                )
            )
    return violations


def _gap_is_documented(projection: OntologyProjection, relation_type: str) -> bool:
    expected_field = f"closure.{relation_type.lower()}"
    return any(
        entry.field == expected_field and entry.status in {"omitted", "rejected", "unavailable"}
        for entry in projection.coverage
    )


def _validate_closure(projection: OntologyProjection) -> list[SchemaViolation]:
    if not any(
        ontology_object.ref.kind in _CLOSURE_KINDS
        for ontology_object in projection.objects
    ):
        return []
    present = {relation.relation_type for relation in projection.relations}
    violations: list[SchemaViolation] = []
    for relation_type in _CLOSURE_RELATIONS:
        if relation_type not in present and not _gap_is_documented(projection, relation_type):
            violations.append(
                _violation(
                    10,
                    "undocumented_closure_gap",
                    f"closure stage {relation_type!r} is absent without a coverage entry",
                    projection.source_run.id,
                )
            )
    return violations


def _valid_nonnegative_number(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and float(value) >= 0.0


def _validate_residuals(projection: OntologyProjection) -> list[SchemaViolation]:
    violations: list[SchemaViolation] = []
    required = frozenset(_REQUIRED_PROPERTIES["residual"])
    for residual in (
        ontology_object
        for ontology_object in projection.objects
        if ontology_object.ref.kind == "residual"
    ):
        missing = required - residual.properties.keys()
        invalid_numeric = not _valid_nonnegative_number(residual.properties.get("norm")) or not (
            _valid_nonnegative_number(residual.properties.get("tolerance"))
        )
        invalid_text = any(
            not isinstance(residual.properties.get(name), str)
            or not str(residual.properties[name]).strip()
            for name in ("solver", "stopping_rule", "status")
            if name in residual.properties
        )
        if missing or invalid_numeric or invalid_text:
            detail = ", ".join(sorted(missing)) or "invalid residual metadata"
            violations.append(
                _violation(
                    11,
                    "incomplete_residual",
                    f"residual is missing or invalid: {detail}",
                    residual.ref.id,
                    residual.sources,
                )
            )
    return violations


def _validate_bounds(projection: OntologyProjection) -> list[SchemaViolation]:
    violations: list[SchemaViolation] = []
    for measurement in projection.measurements:
        if measurement.name not in {"distance_bound", "welfare_bound"}:
            continue
        certified = any(
            relation.relation_type == "CERTIFIES"
            and relation.source.kind == "certificate"
            and relation.target in {measurement.ref, measurement.subject}
            for relation in projection.relations
        )
        if not certified:
            violations.append(
                _violation(
                    12,
                    "uncertified_bound",
                    "distance and welfare bounds require an explicitly linked certificate",
                    measurement.ref.id,
                    measurement.sources,
                )
            )
    return violations


def _validate_interventions(projection: OntologyProjection) -> list[SchemaViolation]:
    violations: list[SchemaViolation] = []
    for realized in (
        ontology_object
        for ontology_object in projection.objects
        if ontology_object.ref.kind == "realized_intervention"
    ):
        declared_link = any(
            relation.relation_type == "INSTANTIATES"
            and relation.source == realized.ref
            and relation.target.kind == "intervention"
            for relation in projection.relations
        )
        outcome_link = any(
            relation.relation_type == "REALIZES"
            and relation.source == realized.ref
            and relation.target.kind == "outcome"
            for relation in projection.relations
        )
        if not declared_link or not outcome_link:
            violations.append(
                _violation(
                    13,
                    "incomplete_intervention_chain",
                    "declared intervention, realization, and observed outcome must remain linked",
                    realized.ref.id,
                    realized.sources,
                )
            )
    return violations


def _validate_claims(projection: OntologyProjection) -> list[SchemaViolation]:
    violations: list[SchemaViolation] = []
    objects = {ontology_object.ref: ontology_object for ontology_object in projection.objects}
    for claim in (
        ontology_object
        for ontology_object in projection.objects
        if ontology_object.ref.kind == "claim"
    ):
        classification = claim.properties.get("evidence_classification")
        supports = tuple(
            relation
            for relation in projection.relations
            if relation.relation_type == "SUPPORTS" and relation.target == claim.ref
        )
        matched = False
        if isinstance(classification, str) and classification.strip():
            matched = any(
                (evidence := objects.get(relation.source)) is not None
                and evidence.ref.kind == "evidence_artifact"
                and evidence.properties.get("evidence_classification") == classification
                for relation in supports
            )
        if not matched:
            violations.append(
                _violation(
                    14,
                    "unsupported_claim",
                    "claims require authorizing evidence with the original classification",
                    claim.ref.id,
                    claim.sources,
                )
            )
    return violations


def _validate_readiness(projection: OntologyProjection) -> list[SchemaViolation]:
    violations: list[SchemaViolation] = []
    for assessment in (
        ontology_object
        for ontology_object in projection.objects
        if ontology_object.ref.kind == "readiness_assessment"
    ):
        classification = assessment.properties.get("classification")
        official_awards = assessment.properties.get("official_awards")
        level = assessment.properties.get("level")
        blocked = assessment.properties.get("blocked")
        higher_level = level in {"L3", "L4", "L5", "L6"}
        awards_are_zero = (
            isinstance(official_awards, int)
            and not isinstance(official_awards, bool)
            and official_awards == 0
        )
        truthful = (
            classification == "evidence_readiness_only"
            and awards_are_zero
            and (not higher_level or blocked is True)
        )
        if not truthful:
            violations.append(
                _violation(
                    14,
                    "readiness_award_forbidden",
                    (
                        "ontology readiness records are evidence-only and cannot award "
                        "Han L3-L6 capability"
                    ),
                    assessment.ref.id,
                    assessment.sources,
                )
            )
    return violations


def _geo_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    converted = float(value)
    return converted if isfinite(converted) else None


def _valid_geo_bound(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return bool(value.strip())
    return _geo_number(value) is not None


def _valid_geo_interval(value: object) -> bool:
    if not isinstance(value, Mapping) or frozenset(value) != {"start", "end"}:
        return False
    start = value["start"]
    end = value["end"]
    if not _valid_geo_bound(start) or not _valid_geo_bound(end):
        return False
    bounds = tuple(bound for bound in (start, end) if bound is not None)
    if len(bounds) == 2:
        numeric = all(_geo_number(bound) is not None for bound in bounds)
        textual = all(isinstance(bound, str) for bound in bounds)
        if numeric:
            start_number = _geo_number(bounds[0])
            end_number = _geo_number(bounds[1])
            return (
                start_number is not None
                and end_number is not None
                and start_number <= end_number
            )
        if textual:
            return str(bounds[0]) <= str(bounds[1])
        return False
    return True


def _allowed_geo_text(value: object, allowed: frozenset[str]) -> bool:
    return isinstance(value, str) and value in allowed


def _validate_geography(projection: OntologyProjection) -> list[SchemaViolation]:
    violations: list[SchemaViolation] = []
    for anchor in (
        item for item in projection.objects if item.ref.kind == "geo_anchor"
    ):
        properties = anchor.properties
        checks = (
            (
                _allowed_geo_text(
                    properties.get("crs"), GEO_COORDINATE_REFERENCE_SYSTEMS
                ),
                "invalid_geo_crs",
                "geo anchors must use a supported coordinate reference system",
            ),
            (
                (latitude := _geo_number(properties.get("latitude"))) is not None
                and -90.0 <= latitude <= 90.0,
                "invalid_geo_latitude",
                "geo anchor latitude must be finite and lie in [-90, 90]",
            ),
            (
                (longitude := _geo_number(properties.get("longitude"))) is not None
                and -180.0 <= longitude <= 180.0,
                "invalid_geo_longitude",
                "geo anchor longitude must be finite and lie in [-180, 180]",
            ),
            (
                _allowed_geo_text(properties.get("anchor_basis"), GEO_ANCHOR_BASES),
                "invalid_geo_basis",
                "geo anchor basis must be observed, declared, or externally supplied",
            ),
            (
                _allowed_geo_text(
                    properties.get("evidence_classification"),
                    GEO_EVIDENCE_CLASSIFICATIONS,
                ),
                "invalid_geo_evidence",
                "geo overlay evidence must retain researcher_declared classification",
            ),
            (
                _valid_geo_interval(properties.get("validity")),
                "invalid_geo_validity",
                "geo anchor validity must be an ordered type-consistent interval",
            ),
            (
                (uncertainty := _geo_number(properties.get("uncertainty_km")))
                is not None
                and uncertainty >= 0.0,
                "invalid_geo_uncertainty",
                "geo anchor uncertainty_km must be finite and non-negative",
            ),
        )
        for valid, code, message in checks:
            if not valid:
                violations.append(
                    _violation(5, code, message, anchor.ref.id, anchor.sources)
                )
    return violations


def validate_projection(projection: OntologyProjection) -> tuple[SchemaViolation, ...]:
    """Return every schema violation in deterministic scientific-invariant order."""

    validators = (
        _validate_identity,
        _validate_references,
        _validate_relations,
        _validate_sources,
        _validate_layers,
        _validate_instantiations,
        _validate_sealed_source_boundary,
        _validate_solution_roles,
        _validate_correspondences,
        _validate_closure,
        _validate_residuals,
        _validate_bounds,
        _validate_interventions,
        _validate_claims,
        _validate_readiness,
        _validate_geography,
    )
    violations = (
        violation
        for validator in validators
        for violation in validator(projection)
    )
    return _sort_violations(violations)


def assert_valid_projection(projection: OntologyProjection) -> None:
    """Reject an unusable ontology projection with all structured violations attached."""

    violations = validate_projection(projection)
    if violations:
        raise OntologyValidationError(violations)
