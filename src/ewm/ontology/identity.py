"""Deterministic ontology identities and explicit canonical record serializers."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any, TypeAlias, cast

from ewm.core import serialization

from .model import (
    CoverageEntry,
    Measurement,
    OntologyObject,
    OntologyProjection,
    OntologyRef,
    RelationAssertion,
    SourceLocator,
)

OntologyRecord: TypeAlias = (
    OntologyRef
    | SourceLocator
    | OntologyObject
    | RelationAssertion
    | Measurement
    | CoverageEntry
    | OntologyProjection
)

_IDENTITY_TOKEN = re.compile(r"[a-z0-9][a-z0-9_-]*")


class IdentityCollisionError(ValueError):
    """Raised when one ontology identity is reused for different semantic content."""


class OntologyIdentityRegistry:
    """Fail-closed registry for identities emitted during one projection."""

    def __init__(self) -> None:
        self._payloads: dict[str, bytes] = {}

    def reserve(self, ref: OntologyRef, semantic_payload: Any) -> None:
        """Reserve ``ref`` for exactly one canonical semantic payload."""

        encoded = canonical_bytes(semantic_payload)
        existing = self._payloads.get(ref.id)
        if existing is not None and existing != encoded:
            raise IdentityCollisionError(
                f"ontology identity collision for {ref.id!r}: canonical payloads differ"
            )
        self._payloads[ref.id] = encoded


def _identity_token(value: str, name: str) -> str:
    if _IDENTITY_TOKEN.fullmatch(value) is None:
        raise ValueError(
            f"{name} must start with an alphanumeric character and contain only "
            "lowercase letters, digits, underscores, or hyphens"
        )
    return value


def make_ontology_ref(
    *,
    namespace: str,
    kind: str,
    source_identity: Any,
    semantic_keys: Any,
    display_label: str | None = None,
) -> OntologyRef:
    """Build ``ewm:{namespace}:{kind}:{digest}`` from semantic identity only.

    ``display_label`` is accepted to make its non-authoritative status explicit. It is deliberately
    absent from both the digest payload and the emitted identity.
    """

    namespace = _identity_token(namespace, "identity namespace")
    kind = _identity_token(kind, "identity kind")
    if display_label is not None and not isinstance(display_label, str):
        raise TypeError("display label must be a string or null")
    digest = serialization.content_digest(
        {
            "namespace": namespace,
            "kind": kind,
            "source_identity": source_identity,
            "semantic_keys": semantic_keys,
        }
    )
    return OntologyRef(id=f"ewm:{namespace}:{kind}:{digest}", kind=kind)


def canonical_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 bytes using the core serializer."""

    return serialization.canonical_json(value).encode("utf-8")


def _canonical_data(value: Any) -> Any:
    return json.loads(serialization.canonical_json(value))


def _check_fields(data: Mapping[str, Any], expected: frozenset[str], name: str) -> None:
    actual = frozenset(data)
    unknown = actual - expected
    missing = expected - actual
    if unknown:
        raise ValueError(f"{name} contains unknown fields: {', '.join(sorted(unknown))}")
    if missing:
        raise ValueError(f"{name} is missing fields: {', '.join(sorted(missing))}")


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise TypeError(f"{name} keys must be strings")
    return cast(Mapping[str, Any], value)


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise TypeError(f"{name} must be a sequence")
    return value


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _optional_string(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _string(value, name)


def ontology_ref_to_data(ref: OntologyRef) -> dict[str, Any]:
    """Serialize an ontology reference."""

    return {"record_type": "ontology_ref", "id": ref.id, "kind": ref.kind}


def ontology_ref_from_data(value: Any) -> OntologyRef:
    """Parse an ontology reference and reject schema drift."""

    data = _mapping(value, "ontology reference")
    _check_fields(data, frozenset({"record_type", "id", "kind"}), "ontology reference")
    if data["record_type"] != "ontology_ref":
        raise ValueError("ontology reference has an invalid record_type")
    return OntologyRef(id=_string(data["id"], "ontology id"), kind=_string(data["kind"], "kind"))


def source_locator_to_data(locator: SourceLocator) -> dict[str, Any]:
    """Serialize a portable source locator."""

    return {
        "record_type": "source_locator",
        "source_kind": locator.source_kind,
        "source_id": locator.source_id,
        "artifact_path": locator.artifact_path,
        "record_selector": locator.record_selector,
        "code_symbol": locator.code_symbol,
        "paper_anchor": locator.paper_anchor,
        "payload_digest": locator.payload_digest,
    }


def source_locator_from_data(value: Any) -> SourceLocator:
    """Parse a portable source locator."""

    data = _mapping(value, "source locator")
    expected = frozenset(
        {
            "record_type",
            "source_kind",
            "source_id",
            "artifact_path",
            "record_selector",
            "code_symbol",
            "paper_anchor",
            "payload_digest",
        }
    )
    _check_fields(data, expected, "source locator")
    if data["record_type"] != "source_locator":
        raise ValueError("source locator has an invalid record_type")
    return SourceLocator(
        source_kind=_string(data["source_kind"], "source kind"),
        source_id=_string(data["source_id"], "source id"),
        artifact_path=_optional_string(data["artifact_path"], "artifact path"),
        record_selector=_optional_string(data["record_selector"], "record selector"),
        code_symbol=_optional_string(data["code_symbol"], "code symbol"),
        paper_anchor=_optional_string(data["paper_anchor"], "paper anchor"),
        payload_digest=_optional_string(data["payload_digest"], "payload digest"),
    )


def ontology_object_to_data(ontology_object: OntologyObject) -> dict[str, Any]:
    """Serialize one ontology object."""

    return {
        "record_type": "ontology_object",
        "ref": ontology_ref_to_data(ontology_object.ref),
        "layer": ontology_object.layer,
        "properties": _canonical_data(ontology_object.properties),
        "sources": [source_locator_to_data(source) for source in ontology_object.sources],
    }


def ontology_object_from_data(value: Any) -> OntologyObject:
    """Parse one ontology object."""

    data = _mapping(value, "ontology object")
    _check_fields(
        data,
        frozenset({"record_type", "ref", "layer", "properties", "sources"}),
        "ontology object",
    )
    if data["record_type"] != "ontology_object":
        raise ValueError("ontology object has an invalid record_type")
    return OntologyObject(
        ref=ontology_ref_from_data(data["ref"]),
        layer=_string(data["layer"], "ontology layer"),
        properties=_mapping(data["properties"], "object properties"),
        sources=tuple(
            source_locator_from_data(source)
            for source in _sequence(data["sources"], "object sources")
        ),
    )


def relation_assertion_to_data(relation: RelationAssertion) -> dict[str, Any]:
    """Serialize one directed relation assertion."""

    return {
        "record_type": "relation_assertion",
        "ref": ontology_ref_to_data(relation.ref),
        "relation_type": relation.relation_type,
        "source": ontology_ref_to_data(relation.source),
        "target": ontology_ref_to_data(relation.target),
        "properties": _canonical_data(relation.properties),
        "sources": [source_locator_to_data(source) for source in relation.sources],
    }


def relation_assertion_from_data(value: Any) -> RelationAssertion:
    """Parse one directed relation assertion."""

    data = _mapping(value, "relation assertion")
    _check_fields(
        data,
        frozenset(
            {"record_type", "ref", "relation_type", "source", "target", "properties", "sources"}
        ),
        "relation assertion",
    )
    if data["record_type"] != "relation_assertion":
        raise ValueError("relation assertion has an invalid record_type")
    return RelationAssertion(
        ref=ontology_ref_from_data(data["ref"]),
        relation_type=_string(data["relation_type"], "relation type"),
        source=ontology_ref_from_data(data["source"]),
        target=ontology_ref_from_data(data["target"]),
        properties=_mapping(data["properties"], "relation properties"),
        sources=tuple(
            source_locator_from_data(source)
            for source in _sequence(data["sources"], "relation sources")
        ),
    )


def measurement_to_data(measurement: Measurement) -> dict[str, Any]:
    """Serialize one measurement."""

    return {
        "record_type": "measurement",
        "ref": ontology_ref_to_data(measurement.ref),
        "subject": ontology_ref_to_data(measurement.subject),
        "name": measurement.name,
        "value": _canonical_data(measurement.value),
        "unit": measurement.unit,
        "status": measurement.status,
        "sample": _canonical_data(measurement.sample),
        "uncertainty": _canonical_data(measurement.uncertainty),
        "sources": [source_locator_to_data(source) for source in measurement.sources],
    }


def measurement_from_data(value: Any) -> Measurement:
    """Parse one measurement."""

    data = _mapping(value, "measurement")
    _check_fields(
        data,
        frozenset(
            {
                "record_type",
                "ref",
                "subject",
                "name",
                "value",
                "unit",
                "status",
                "sample",
                "uncertainty",
                "sources",
            }
        ),
        "measurement",
    )
    if data["record_type"] != "measurement":
        raise ValueError("measurement has an invalid record_type")
    return Measurement(
        ref=ontology_ref_from_data(data["ref"]),
        subject=ontology_ref_from_data(data["subject"]),
        name=_string(data["name"], "measurement name"),
        value=data["value"],
        unit=_string(data["unit"], "measurement unit"),
        status=_string(data["status"], "measurement status"),
        sample=_mapping(data["sample"], "measurement sample"),
        uncertainty=_mapping(data["uncertainty"], "measurement uncertainty"),
        sources=tuple(
            source_locator_from_data(source)
            for source in _sequence(data["sources"], "measurement sources")
        ),
    )


def coverage_entry_to_data(entry: CoverageEntry) -> dict[str, Any]:
    """Serialize one projection coverage disposition."""

    return {
        "record_type": "coverage_entry",
        "source": source_locator_to_data(entry.source),
        "field": entry.field,
        "status": entry.status,
        "targets": [ontology_ref_to_data(target) for target in entry.targets],
        "reason": entry.reason,
    }


def coverage_entry_from_data(value: Any) -> CoverageEntry:
    """Parse one projection coverage disposition."""

    data = _mapping(value, "coverage entry")
    _check_fields(
        data,
        frozenset({"record_type", "source", "field", "status", "targets", "reason"}),
        "coverage entry",
    )
    if data["record_type"] != "coverage_entry":
        raise ValueError("coverage entry has an invalid record_type")
    return CoverageEntry(
        source=source_locator_from_data(data["source"]),
        field=_string(data["field"], "coverage field"),
        status=_string(data["status"], "coverage status"),
        targets=tuple(
            ontology_ref_from_data(target)
            for target in _sequence(data["targets"], "coverage targets")
        ),
        reason=_optional_string(data["reason"], "coverage reason"),
    )


def projection_to_data(projection: OntologyProjection) -> dict[str, Any]:
    """Serialize one complete ontology projection including its coverage ledger."""

    return {
        "record_type": "ontology_projection",
        "schema": projection.schema,
        "source_run": ontology_ref_to_data(projection.source_run),
        "objects": [ontology_object_to_data(item) for item in projection.objects],
        "relations": [relation_assertion_to_data(item) for item in projection.relations],
        "measurements": [measurement_to_data(item) for item in projection.measurements],
        "coverage": [coverage_entry_to_data(item) for item in projection.coverage],
        "projection_digest": projection.projection_digest,
    }


def projection_from_data(value: Any) -> OntologyProjection:
    """Parse one complete ontology projection."""

    data = _mapping(value, "ontology projection")
    _check_fields(
        data,
        frozenset(
            {
                "record_type",
                "schema",
                "source_run",
                "objects",
                "relations",
                "measurements",
                "coverage",
                "projection_digest",
            }
        ),
        "ontology projection",
    )
    if data["record_type"] != "ontology_projection":
        raise ValueError("ontology projection has an invalid record_type")
    return OntologyProjection(
        schema=_string(data["schema"], "projection schema"),
        source_run=ontology_ref_from_data(data["source_run"]),
        objects=tuple(
            ontology_object_from_data(item)
            for item in _sequence(data["objects"], "projection objects")
        ),
        relations=tuple(
            relation_assertion_from_data(item)
            for item in _sequence(data["relations"], "projection relations")
        ),
        measurements=tuple(
            measurement_from_data(item)
            for item in _sequence(data["measurements"], "projection measurements")
        ),
        coverage=tuple(
            coverage_entry_from_data(item)
            for item in _sequence(data["coverage"], "projection coverage")
        ),
        projection_digest=_string(data["projection_digest"], "projection digest"),
    )


def ontology_record_to_data(record: OntologyRecord) -> dict[str, Any]:
    """Serialize a known ontology record and reject unregistered values."""

    if isinstance(record, OntologyRef):
        return ontology_ref_to_data(record)
    if isinstance(record, SourceLocator):
        return source_locator_to_data(record)
    if isinstance(record, OntologyObject):
        return ontology_object_to_data(record)
    if isinstance(record, RelationAssertion):
        return relation_assertion_to_data(record)
    if isinstance(record, Measurement):
        return measurement_to_data(record)
    if isinstance(record, CoverageEntry):
        return coverage_entry_to_data(record)
    if isinstance(record, OntologyProjection):
        return projection_to_data(record)
    raise TypeError(f"value of type {type(record).__name__!r} is not a known ontology record")


def ontology_record_from_data(value: Any) -> OntologyRecord:
    """Parse a known ontology record and reject unknown record types."""

    data = _mapping(value, "ontology record")
    record_type = _string(data.get("record_type"), "ontology record_type")
    parsers: dict[str, Callable[[Any], OntologyRecord]] = {
        "ontology_ref": ontology_ref_from_data,
        "source_locator": source_locator_from_data,
        "ontology_object": ontology_object_from_data,
        "relation_assertion": relation_assertion_from_data,
        "measurement": measurement_from_data,
        "coverage_entry": coverage_entry_from_data,
        "ontology_projection": projection_from_data,
    }
    parser = parsers.get(record_type)
    if parser is None:
        raise ValueError(f"unknown ontology record_type {record_type!r}")
    return parser(data)
