"""Deterministic immutable indexes over validated ontology projections."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Hashable, Mapping
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Any, TypeAlias, TypeVar

from ..graph.model import (
    Measurement,
    OntologyObject,
    OntologyProjection,
    RelationAssertion,
    SourceLocator,
)
from ..graph.schema import assert_valid_projection

OntologyRecord: TypeAlias = OntologyObject | RelationAssertion | Measurement
IndexTime: TypeAlias = int | float | str

_K = TypeVar("_K", bound=Hashable)


def _freeze_buckets(values: Mapping[_K, set[str]]) -> Mapping[_K, tuple[str, ...]]:
    return MappingProxyType(
        {
            key: tuple(sorted(record_ids))
            for key, record_ids in sorted(values.items(), key=lambda item: repr(item[0]))
        }
    )


def _record_context(record: OntologyRecord) -> Mapping[str, Any]:
    if isinstance(record, Measurement):
        return record.sample
    return record.properties


def _optional_text(context: Mapping[str, Any], key: str) -> str | None:
    value = context.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"ontology index field {key!r} must be non-empty text")
    return value


def _event_sequence(context: Mapping[str, Any]) -> int | None:
    value = context.get("event_sequence", context.get("sequence"))
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("ontology event sequence must be a non-negative integer")
    return value


def _time_value(context: Mapping[str, Any]) -> IndexTime | None:
    value = context.get("time", context.get("timestamp"))
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise ValueError("ontology time must be finite numeric data or non-empty text")
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("ontology time must be finite numeric data or non-empty text")
    if isinstance(value, str) and not value.strip():
        raise ValueError("ontology time must be finite numeric data or non-empty text")
    return value


@dataclass(frozen=True, slots=True)
class OntologyIndexes:
    """Read-only lookup tables derived once from a validated projection."""

    projection: OntologyProjection
    records_by_id: Mapping[str, OntologyRecord]
    object_ids_by_kind: Mapping[str, tuple[str, ...]]
    object_ids_by_layer: Mapping[str, tuple[str, ...]]
    relation_ids_by_type: Mapping[str, tuple[str, ...]]
    outgoing_relation_ids: Mapping[str, tuple[str, ...]]
    incoming_relation_ids: Mapping[str, tuple[str, ...]]
    record_ids_by_run: Mapping[str, tuple[str, ...]]
    record_ids_by_episode: Mapping[str, tuple[str, ...]]
    record_ids_by_event_sequence: Mapping[int, tuple[str, ...]]
    record_ids_by_time: Mapping[IndexTime, tuple[str, ...]]
    record_ids_by_source: Mapping[SourceLocator, tuple[str, ...]]
    measurement_ids_by_name: Mapping[str, tuple[str, ...]]
    measurement_ids_by_status: Mapping[str, tuple[str, ...]]
    measurement_ids_by_unit: Mapping[str, tuple[str, ...]]
    measurement_ids_by_subject: Mapping[str, tuple[str, ...]]
    claim_ids_by_classification: Mapping[str, tuple[str, ...]]
    evidence_ids_by_classification: Mapping[str, tuple[str, ...]]

    @property
    def projection_digest(self) -> str:
        """Return the identity to which every index entry belongs."""

        return self.projection.projection_digest


def build_indexes(projection: OntologyProjection) -> OntologyIndexes:
    """Validate a projection and derive every query index in stable ID order."""

    assert_valid_projection(projection)
    records: tuple[OntologyRecord, ...] = (
        *projection.objects,
        *projection.relations,
        *projection.measurements,
    )
    records_by_id: Mapping[str, OntologyRecord] = MappingProxyType(
        {record.ref.id: record for record in records}
    )
    object_kinds: defaultdict[str, set[str]] = defaultdict(set)
    object_layers: defaultdict[str, set[str]] = defaultdict(set)
    relation_types: defaultdict[str, set[str]] = defaultdict(set)
    outgoing: defaultdict[str, set[str]] = defaultdict(set)
    incoming: defaultdict[str, set[str]] = defaultdict(set)
    runs: defaultdict[str, set[str]] = defaultdict(set)
    episodes: defaultdict[str, set[str]] = defaultdict(set)
    event_sequences: defaultdict[int, set[str]] = defaultdict(set)
    times: defaultdict[IndexTime, set[str]] = defaultdict(set)
    sources: defaultdict[SourceLocator, set[str]] = defaultdict(set)
    measurement_names: defaultdict[str, set[str]] = defaultdict(set)
    measurement_statuses: defaultdict[str, set[str]] = defaultdict(set)
    measurement_units: defaultdict[str, set[str]] = defaultdict(set)
    measurement_subjects: defaultdict[str, set[str]] = defaultdict(set)
    claim_classifications: defaultdict[str, set[str]] = defaultdict(set)
    evidence_classifications: defaultdict[str, set[str]] = defaultdict(set)

    for ontology_object in projection.objects:
        object_kinds[ontology_object.ref.kind].add(ontology_object.ref.id)
        object_layers[ontology_object.layer].add(ontology_object.ref.id)
        classification = ontology_object.properties.get("evidence_classification")
        if classification is not None:
            if not isinstance(classification, str) or not classification.strip():
                raise ValueError("evidence classification must be non-empty text")
            if ontology_object.ref.kind == "claim":
                claim_classifications[classification].add(ontology_object.ref.id)
            elif ontology_object.ref.kind == "evidence_artifact":
                evidence_classifications[classification].add(ontology_object.ref.id)

    for relation in projection.relations:
        relation_types[relation.relation_type].add(relation.ref.id)
        outgoing[relation.source.id].add(relation.ref.id)
        incoming[relation.target.id].add(relation.ref.id)

    for measurement in projection.measurements:
        measurement_names[measurement.name].add(measurement.ref.id)
        measurement_statuses[measurement.status].add(measurement.ref.id)
        measurement_units[measurement.unit].add(measurement.ref.id)
        measurement_subjects[measurement.subject.id].add(measurement.ref.id)

    source_run_id = projection.source_run.id
    for record in records:
        record_id = record.ref.id
        runs[source_run_id].add(record_id)
        context = _record_context(record)
        explicit_run = _optional_text(context, "run_id")
        if explicit_run is not None:
            runs[explicit_run].add(record_id)
        episode = _optional_text(context, "episode_id")
        if episode is not None:
            episodes[episode].add(record_id)
        sequence = _event_sequence(context)
        if sequence is not None:
            event_sequences[sequence].add(record_id)
        time = _time_value(context)
        if time is not None:
            times[time].add(record_id)
        for source in record.sources:
            sources[source].add(record_id)

    return OntologyIndexes(
        projection=projection,
        records_by_id=records_by_id,
        object_ids_by_kind=_freeze_buckets(object_kinds),
        object_ids_by_layer=_freeze_buckets(object_layers),
        relation_ids_by_type=_freeze_buckets(relation_types),
        outgoing_relation_ids=_freeze_buckets(outgoing),
        incoming_relation_ids=_freeze_buckets(incoming),
        record_ids_by_run=_freeze_buckets(runs),
        record_ids_by_episode=_freeze_buckets(episodes),
        record_ids_by_event_sequence=_freeze_buckets(event_sequences),
        record_ids_by_time=_freeze_buckets(times),
        record_ids_by_source=_freeze_buckets(sources),
        measurement_ids_by_name=_freeze_buckets(measurement_names),
        measurement_ids_by_status=_freeze_buckets(measurement_statuses),
        measurement_ids_by_unit=_freeze_buckets(measurement_units),
        measurement_ids_by_subject=_freeze_buckets(measurement_subjects),
        claim_ids_by_classification=_freeze_buckets(claim_classifications),
        evidence_ids_by_classification=_freeze_buckets(evidence_classifications),
    )
