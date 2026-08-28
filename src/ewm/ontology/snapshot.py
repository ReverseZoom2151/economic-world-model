"""Canonical, bounded payloads for portable ontology investigations."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any, cast

from ewm._internal.canonical import canonical_json, content_digest

from .graph.identity import (
    coverage_entry_from_data,
    coverage_entry_to_data,
    measurement_from_data,
    measurement_to_data,
    ontology_object_from_data,
    ontology_object_to_data,
    relation_assertion_from_data,
    relation_assertion_to_data,
)
from .graph.model import (
    CoverageEntry,
    Measurement,
    OntologyObject,
    OntologyProjection,
    RelationAssertion,
)

INVESTIGATION_SCHEMA = "ewm.investigation.v1"
DEFAULT_MAX_OBJECTS = 10_000
DEFAULT_MAX_RELATIONS = 30_000
DEFAULT_MAX_EVENTS = 100_000
DEFAULT_MAX_HTML_BYTES = 50 * 1024 * 1024
_LENSES = frozenset(
    {
        "world",
        "runtime",
        "market",
        "learning",
        "ddge",
        "compare",
        "evidence",
        "lineage",
        "scene",
        "globe",
    }
)
_HEX = frozenset("0123456789abcdef")


def _require_digest(value: str, name: str) -> None:
    if len(value) != 64 or any(character not in _HEX for character in value):
        raise ValueError(f"{name} must be 64 lowercase hexadecimal characters")


def _require_text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must not be empty")


def _canonical_data(value: Any) -> Any:
    return json.loads(canonical_json(value))


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise TypeError(f"{name} must be an object with string keys")
    return cast(Mapping[str, Any], value)


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise TypeError(f"{name} must be an array")
    return value


def _strict_fields(data: Mapping[str, Any], expected: frozenset[str], name: str) -> None:
    actual = frozenset(data)
    if actual != expected:
        unknown = sorted(actual - expected)
        missing = sorted(expected - actual)
        raise ValueError(f"{name} fields differ: missing={missing}, unknown={unknown}")


def _text_tuple(value: Any, name: str) -> tuple[str, ...]:
    values = _sequence(value, name)
    if any(not isinstance(item, str) or not item.strip() for item in values):
        raise ValueError(f"{name} must contain non-empty strings")
    return tuple(sorted(set(cast(Sequence[str], values))))


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


@dataclass(frozen=True, slots=True)
class SnapshotLimits:
    """Hard limits for one curated portable investigation."""

    max_objects: int = DEFAULT_MAX_OBJECTS
    max_relations: int = DEFAULT_MAX_RELATIONS
    max_events: int = DEFAULT_MAX_EVENTS
    max_html_bytes: int = DEFAULT_MAX_HTML_BYTES

    def __post_init__(self) -> None:
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 1
            for value in (
                self.max_objects,
                self.max_relations,
                self.max_events,
                self.max_html_bytes,
            )
        ):
            raise ValueError("snapshot limits must be positive integers")

    def as_dict(self) -> dict[str, int]:
        return {
            "objects": self.max_objects,
            "relations": self.max_relations,
            "events": self.max_events,
            "html_bytes": self.max_html_bytes,
        }


class SnapshotSizeError(ValueError):
    """Raised with machine-readable scope reductions when a subset is too large."""

    def __init__(self, counts: Mapping[str, int], limits: SnapshotLimits) -> None:
        self.counts = dict(counts)
        self.limits = limits
        exceeded = [
            name
            for name in ("objects", "relations", "events")
            if self.counts[name] > limits.as_dict()[name]
        ]
        super().__init__(f"snapshot scope exceeds limits for {', '.join(exceeded)}")

    def as_dict(self) -> dict[str, Any]:
        reductions = [
            f"select fewer {name} "
            f"(requested {self.counts[name]}, limit {self.limits.as_dict()[name]})"
            for name in ("objects", "relations", "events")
            if self.counts[name] > self.limits.as_dict()[name]
        ]
        return {
            "code": "snapshot_scope_exceeded",
            "message": str(self),
            "counts": dict(self.counts),
            "limits": self.limits.as_dict(),
            "reductions": reductions,
        }


@dataclass(frozen=True, slots=True)
class SnapshotSource:
    """Portable source and adapter identities retained in a snapshot."""

    run_id: str
    source_run_hash: str
    source_identity_sha256: str
    source_bundle_sha256: str
    profile_identity: str
    profile_digest: str
    integrity_level: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.run_id, "run ID"),
            (self.profile_identity, "profile identity"),
            (self.integrity_level, "integrity level"),
        ):
            _require_text(value, name)
        if (
            len(self.source_run_hash) != 20
            or any(character not in _HEX for character in self.source_run_hash)
        ):
            raise ValueError("source run hash must be 20 lowercase hexadecimal characters")
        _require_digest(self.source_identity_sha256, "source identity SHA-256")
        _require_digest(self.source_bundle_sha256, "source bundle SHA-256")
        _require_digest(self.profile_digest, "profile digest")


@dataclass(frozen=True, slots=True)
class SnapshotSelection:
    """Canonical subset and serialized 2D/3D investigation state."""

    object_ids: tuple[str, ...] = ()
    relation_ids: tuple[str, ...] = ()
    event_ids: tuple[str, ...] = ()
    lens: str = "world"
    filters: Mapping[str, Any] = None  # type: ignore[assignment]
    time_window: tuple[float, float] | None = None
    camera: Mapping[str, Any] | None = None
    layout: Mapping[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.lens not in _LENSES:
            raise ValueError(f"unknown investigation lens {self.lens!r}")
        filters = self.filters or {"kinds": [], "layers": [], "query": ""}
        layout = self.layout or {}
        object.__setattr__(self, "filters", _canonical_data(filters))
        object.__setattr__(self, "layout", _canonical_data(layout))
        if self.camera is not None:
            object.__setattr__(self, "camera", _canonical_data(self.camera))

    @classmethod
    def from_data(cls, value: Mapping[str, Any]) -> SnapshotSelection:
        data = _mapping(value, "snapshot selection")
        allowed = frozenset(
            {
                "object_ids",
                "relation_ids",
                "event_ids",
                "lens",
                "filters",
                "time_window",
                "camera",
                "layout",
            }
        )
        unknown = frozenset(data) - allowed
        if unknown:
            raise ValueError(f"snapshot selection contains unknown fields: {sorted(unknown)}")
        filters_data = _mapping(
            data.get("filters", {"kinds": [], "layers": [], "query": ""}),
            "snapshot filters",
        )
        filter_allowed = frozenset({"kinds", "layers", "query"})
        if frozenset(filters_data) - filter_allowed:
            raise ValueError("snapshot filters contain unknown fields")
        query = filters_data.get("query", "")
        if not isinstance(query, str):
            raise TypeError("snapshot filter query must be text")
        filters = {
            "kinds": list(_text_tuple(filters_data.get("kinds", []), "filter kinds")),
            "layers": list(_text_tuple(filters_data.get("layers", []), "filter layers")),
            "query": query,
        }
        window_value = data.get("time_window")
        window: tuple[float, float] | None = None
        if window_value is not None:
            window_data = _mapping(window_value, "time window")
            _strict_fields(window_data, frozenset({"start", "end"}), "time window")
            start = _finite_number(window_data["start"], "time-window start")
            end = _finite_number(window_data["end"], "time-window end")
            window = (min(start, end), max(start, end))
        camera_value = data.get("camera")
        camera: Mapping[str, Any] | None = None
        if camera_value is not None:
            camera_data = _mapping(camera_value, "camera")
            _strict_fields(
                camera_data,
                frozenset({"projection", "position", "target"}),
                "camera",
            )
            projection = camera_data["projection"]
            if projection not in {"perspective", "orthographic"}:
                raise ValueError("camera projection must be perspective or orthographic")
            position = tuple(
                _finite_number(item, "camera position")
                for item in _sequence(camera_data["position"], "camera position")
            )
            target = tuple(
                _finite_number(item, "camera target")
                for item in _sequence(camera_data["target"], "camera target")
            )
            if len(position) != 3 or len(target) != 3:
                raise ValueError("camera position and target require three coordinates")
            camera = {
                "projection": projection,
                "position": list(position),
                "target": list(target),
            }
        layout = _mapping(data.get("layout", {}), "snapshot layout")
        return cls(
            object_ids=_text_tuple(data.get("object_ids", []), "object IDs"),
            relation_ids=_text_tuple(data.get("relation_ids", []), "relation IDs"),
            event_ids=_text_tuple(data.get("event_ids", []), "event IDs"),
            lens=str(data.get("lens", "world")),
            filters=filters,
            time_window=window,
            camera=camera,
            layout=layout,
        )

    def to_data(self) -> dict[str, Any]:
        return {
            "object_ids": list(self.object_ids),
            "relation_ids": list(self.relation_ids),
            "event_ids": list(self.event_ids),
            "lens": self.lens,
            "filters": _canonical_data(self.filters),
            "time_window": (
                None
                if self.time_window is None
                else {"start": self.time_window[0], "end": self.time_window[1]}
            ),
            "camera": None if self.camera is None else _canonical_data(self.camera),
            "layout": _canonical_data(self.layout),
        }


@dataclass(frozen=True, slots=True)
class InvestigationSnapshot:
    """One immutable curated ontology subset consumed by the offline data source."""

    schema: str
    source: SnapshotSource
    projection_digest: str
    subset_digest: str
    selection: SnapshotSelection
    objects: tuple[OntologyObject, ...]
    relations: tuple[RelationAssertion, ...]
    measurements: tuple[Measurement, ...]
    coverage: tuple[CoverageEntry, ...]
    comparisons: tuple[Mapping[str, Any], ...]
    globe_geometry: Mapping[str, Any] | None

    @property
    def source_bundle_sha256(self) -> str:
        return self.source.source_bundle_sha256

    def semantic_data(self) -> dict[str, Any]:
        run = {
            "run_id": self.source.run_id,
            "source_run_hash": self.source.source_run_hash,
            "profile_identity": self.source.profile_identity,
            "integrity_level": self.source.integrity_level,
            "projection_digest": self.projection_digest,
            "ontology_schema": "ewm.ontology.v1",
            "coverage": [coverage_entry_to_data(item) for item in self.coverage],
        }
        return {
            "schema": self.schema,
            "source_run_hash": self.source.source_run_hash,
            "source_identity_sha256": self.source.source_identity_sha256,
            "source_bundle_sha256": self.source.source_bundle_sha256,
            "profile_identity": self.source.profile_identity,
            "profile_digest": self.source.profile_digest,
            "integrity_level": self.source.integrity_level,
            "projection_digest": self.projection_digest,
            "selection": self.selection.to_data(),
            "runs": [run],
            "objects": [ontology_object_to_data(item) for item in self.objects],
            "relations": [relation_assertion_to_data(item) for item in self.relations],
            "measurements": [measurement_to_data(item) for item in self.measurements],
            "coverage": [coverage_entry_to_data(item) for item in self.coverage],
            "comparisons": [_canonical_data(item) for item in self.comparisons],
            "globe_geometry": (
                None if self.globe_geometry is None else _canonical_data(self.globe_geometry)
            ),
        }

    def to_data(self) -> dict[str, Any]:
        return {**self.semantic_data(), "subset_digest": self.subset_digest}


def _selected_records(
    projection: OntologyProjection,
    selection: SnapshotSelection,
) -> tuple[
    tuple[OntologyObject, ...],
    tuple[RelationAssertion, ...],
    tuple[Measurement, ...],
    tuple[CoverageEntry, ...],
]:
    object_by_id = {item.ref.id: item for item in projection.objects}
    relation_by_id = {item.ref.id: item for item in projection.relations}
    requested_objects = set(selection.object_ids) | set(selection.event_ids)
    missing_objects = requested_objects - object_by_id.keys()
    missing_relations = set(selection.relation_ids) - relation_by_id.keys()
    if missing_objects or missing_relations:
        raise ValueError(
            f"snapshot selection contains unknown IDs: objects={sorted(missing_objects)}, "
            f"relations={sorted(missing_relations)}"
        )
    selected_ids = requested_objects if requested_objects else set(object_by_id)
    explicit_relations = (
        tuple(relation_by_id[item] for item in selection.relation_ids)
        if selection.relation_ids
        else tuple(
            item
            for item in projection.relations
            if item.source.id in selected_ids and item.target.id in selected_ids
        )
    )
    for relation in explicit_relations:
        selected_ids.update((relation.source.id, relation.target.id))
    objects = tuple(
        sorted(
            (object_by_id[item] for item in selected_ids),
            key=lambda item: item.ref.id,
        )
    )
    relations = tuple(sorted(explicit_relations, key=lambda item: item.ref.id))
    measurements = tuple(
        sorted(
            (item for item in projection.measurements if item.subject.id in selected_ids),
            key=lambda item: item.ref.id,
        )
    )
    coverage = tuple(
        sorted(
            (
                item
                for item in projection.coverage
                if not item.targets or any(target.id in selected_ids for target in item.targets)
            ),
            key=lambda item: item.field,
        )
    )
    return objects, relations, measurements, coverage


def compile_investigation(
    projection: OntologyProjection,
    source: SnapshotSource,
    selection: SnapshotSelection,
    *,
    limits: SnapshotLimits | None = None,
    globe_geometry: Mapping[str, Any] | None = None,
    comparisons: Sequence[Mapping[str, Any]] = (),
) -> InvestigationSnapshot:
    """Compile a deterministic, bounded investigation subset from one verified projection."""

    selected_limits = limits or SnapshotLimits()
    objects, relations, measurements, coverage = _selected_records(projection, selection)
    counts = {
        "objects": len(objects),
        "relations": len(relations),
        "events": sum(item.layer == "runtime_occurrence" for item in objects),
    }
    if (
        counts["objects"] > selected_limits.max_objects
        or counts["relations"] > selected_limits.max_relations
        or counts["events"] > selected_limits.max_events
    ):
        raise SnapshotSizeError(counts, selected_limits)
    geometry = None
    if selection.lens == "globe" and globe_geometry is not None:
        geometry = cast(Mapping[str, Any], _canonical_data(globe_geometry))
    provisional = InvestigationSnapshot(
        schema=INVESTIGATION_SCHEMA,
        source=source,
        projection_digest=projection.projection_digest,
        subset_digest="0" * 64,
        selection=selection,
        objects=objects,
        relations=relations,
        measurements=measurements,
        coverage=coverage,
        comparisons=tuple(
            cast(Mapping[str, Any], _canonical_data(item)) for item in comparisons
        ),
        globe_geometry=geometry,
    )
    return replace(provisional, subset_digest=content_digest(provisional.semantic_data()))


def investigation_to_bytes(snapshot: InvestigationSnapshot) -> bytes:
    """Serialize one investigation into canonical UTF-8 bytes."""

    if snapshot.subset_digest != content_digest(snapshot.semantic_data()):
        raise ValueError("snapshot subset digest is not self-consistent")
    return canonical_json(snapshot.to_data()).encode("utf-8")


def investigation_from_bytes(value: bytes) -> InvestigationSnapshot:
    """Parse canonical snapshot bytes and reject schema drift or corruption."""

    try:
        decoded = json.loads(value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("snapshot payload is not valid UTF-8 JSON") from error
    data = _mapping(decoded, "investigation snapshot")
    expected = frozenset(
        {
            "schema",
            "source_run_hash",
            "source_identity_sha256",
            "source_bundle_sha256",
            "profile_identity",
            "profile_digest",
            "integrity_level",
            "projection_digest",
            "subset_digest",
            "selection",
            "runs",
            "objects",
            "relations",
            "measurements",
            "coverage",
            "comparisons",
            "globe_geometry",
        }
    )
    _strict_fields(data, expected, "investigation snapshot")
    if data["schema"] != INVESTIGATION_SCHEMA:
        raise ValueError(f"snapshot schema must be {INVESTIGATION_SCHEMA}")
    runs = _sequence(data["runs"], "snapshot runs")
    if len(runs) != 1:
        raise ValueError("ewm.investigation.v1 requires exactly one source run")
    run = _mapping(runs[0], "snapshot run")
    source = SnapshotSource(
        run_id=str(run.get("run_id", "")),
        source_run_hash=str(data["source_run_hash"]),
        source_identity_sha256=str(data["source_identity_sha256"]),
        source_bundle_sha256=str(data["source_bundle_sha256"]),
        profile_identity=str(data["profile_identity"]),
        profile_digest=str(data["profile_digest"]),
        integrity_level=str(data["integrity_level"]),
    )
    projection_digest = str(data["projection_digest"])
    subset_digest = str(data["subset_digest"])
    _require_digest(projection_digest, "projection digest")
    _require_digest(subset_digest, "subset digest")
    geometry_value = data["globe_geometry"]
    geometry = None if geometry_value is None else _mapping(geometry_value, "globe geometry")
    snapshot = InvestigationSnapshot(
        schema=INVESTIGATION_SCHEMA,
        source=source,
        projection_digest=projection_digest,
        subset_digest=subset_digest,
        selection=SnapshotSelection.from_data(_mapping(data["selection"], "selection")),
        objects=tuple(
            ontology_object_from_data(item)
            for item in _sequence(data["objects"], "snapshot objects")
        ),
        relations=tuple(
            relation_assertion_from_data(item)
            for item in _sequence(data["relations"], "snapshot relations")
        ),
        measurements=tuple(
            measurement_from_data(item)
            for item in _sequence(data["measurements"], "snapshot measurements")
        ),
        coverage=tuple(
            coverage_entry_from_data(item)
            for item in _sequence(data["coverage"], "snapshot coverage")
        ),
        comparisons=tuple(
            _mapping(item, "snapshot comparison")
            for item in _sequence(data["comparisons"], "snapshot comparisons")
        ),
        globe_geometry=geometry,
    )
    if snapshot.subset_digest != content_digest(snapshot.semantic_data()):
        raise ValueError("snapshot subset digest does not match its semantic content")
    if investigation_to_bytes(snapshot) != value:
        raise ValueError("snapshot payload is not canonical JSON")
    return snapshot


__all__ = [
    "DEFAULT_MAX_EVENTS",
    "DEFAULT_MAX_HTML_BYTES",
    "DEFAULT_MAX_OBJECTS",
    "DEFAULT_MAX_RELATIONS",
    "INVESTIGATION_SCHEMA",
    "InvestigationSnapshot",
    "SnapshotLimits",
    "SnapshotSelection",
    "SnapshotSizeError",
    "SnapshotSource",
    "compile_investigation",
    "investigation_from_bytes",
    "investigation_to_bytes",
]
