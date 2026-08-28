"""Immutable records for canonical ontology projections."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from string import hexdigits
from typing import Any, TypeVar, cast

import numpy as np

from ewm.core.domain.records import freeze_value
from ewm.core.provenance.serialization import canonical_json

ONTOLOGY_LAYERS = frozenset(
    {
        "schema",
        "economic_declaration",
        "runtime_occurrence",
        "learning_equilibrium",
        "research_evidence",
        "provenance",
    }
)
COVERAGE_STATUSES = frozenset({"projected", "omitted", "rejected", "unavailable"})

_T = TypeVar("_T")


def _require_text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must not be empty")


def _optional_text(value: str | None, name: str) -> None:
    if value is not None:
        _require_text(value, name)


def _require_digest(value: str, name: str) -> None:
    _require_text(value, name)
    if len(value) != 64 or any(character not in hexdigits for character in value):
        raise ValueError(f"{name} must be a 64-character hexadecimal digest")
    if value != value.lower():
        raise ValueError(f"{name} must use lowercase hexadecimal")


def _freeze_mapping(value: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    try:
        canonical_json(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must contain only finite canonical values") from error
    return cast(Mapping[str, Any], freeze_value(value))


def _freeze_sources(sources: tuple[SourceLocator, ...]) -> tuple[SourceLocator, ...]:
    frozen = tuple(sources)
    if not frozen:
        raise ValueError("ontology assertions require at least one source locator")
    if not all(isinstance(source, SourceLocator) for source in frozen):
        raise TypeError("sources must contain only SourceLocator values")
    return frozen


def _freeze_typed_tuple(values: tuple[_T, ...], expected: type[_T], name: str) -> tuple[_T, ...]:
    frozen = tuple(values)
    if not all(isinstance(value, expected) for value in frozen):
        raise TypeError(f"{name} must contain only {expected.__name__} values")
    return frozen


def _contains_boolean(value: Any) -> bool:
    if isinstance(value, bool | np.bool_):
        return True
    if isinstance(value, np.ndarray):
        return bool(value.dtype.kind == "b")
    if isinstance(value, Mapping):
        return any(_contains_boolean(item) for item in value.values())
    if isinstance(value, tuple | list | set | frozenset):
        return any(_contains_boolean(item) for item in value)
    return False


def _freeze_measurement_value(value: Any) -> Any:
    if _contains_boolean(value):
        raise ValueError("measurement value must be numeric or null, not boolean")
    try:
        canonical_json(value)
    except (TypeError, ValueError) as error:
        raise ValueError("measurement value must contain only finite canonical values") from error
    return freeze_value(value)


@dataclass(frozen=True, order=True, slots=True)
class OntologyRef:
    """Stable identity and kind of one ontology record."""

    id: str
    kind: str

    def __post_init__(self) -> None:
        _require_text(self.id, "ontology id")
        _require_text(self.kind, "ontology kind")


@dataclass(frozen=True, slots=True)
class SourceLocator:
    """Portable evidence locator for an ontology assertion."""

    source_kind: str
    source_id: str
    artifact_path: str | None = None
    record_selector: str | None = None
    code_symbol: str | None = None
    paper_anchor: str | None = None
    payload_digest: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.source_kind, "source kind")
        _require_text(self.source_id, "source id")
        _optional_text(self.record_selector, "record selector")
        _optional_text(self.code_symbol, "code symbol")
        _optional_text(self.paper_anchor, "paper anchor")
        if self.payload_digest is not None:
            _require_digest(self.payload_digest, "payload digest")
        if self.artifact_path is None:
            return
        _require_text(self.artifact_path, "artifact path")
        portable = self.artifact_path.replace("\\", "/")
        path = PurePosixPath(portable)
        if path.is_absolute() or PureWindowsPath(self.artifact_path).is_absolute():
            raise ValueError("artifact path must be relative")
        if ".." in path.parts:
            raise ValueError("artifact path must be relative without parent traversal")
        object.__setattr__(self, "artifact_path", path.as_posix())


@dataclass(frozen=True, slots=True)
class OntologyObject:
    """One canonical object in exactly one ontology layer."""

    ref: OntologyRef
    layer: str
    properties: Mapping[str, Any]
    sources: tuple[SourceLocator, ...]

    def __post_init__(self) -> None:
        if self.layer not in ONTOLOGY_LAYERS:
            raise ValueError(f"invalid ontology layer {self.layer!r}")
        object.__setattr__(self, "properties", _freeze_mapping(self.properties, "properties"))
        object.__setattr__(self, "sources", _freeze_sources(self.sources))


@dataclass(frozen=True, slots=True)
class RelationAssertion:
    """One directed, sourced relation between ontology records."""

    ref: OntologyRef
    relation_type: str
    source: OntologyRef
    target: OntologyRef
    properties: Mapping[str, Any]
    sources: tuple[SourceLocator, ...]

    def __post_init__(self) -> None:
        _require_text(self.relation_type, "relation type")
        object.__setattr__(self, "properties", _freeze_mapping(self.properties, "properties"))
        object.__setattr__(self, "sources", _freeze_sources(self.sources))


@dataclass(frozen=True, slots=True)
class Measurement:
    """A sourced scalar or structured numerical observation."""

    ref: OntologyRef
    subject: OntologyRef
    name: str
    value: Any
    unit: str
    status: str
    sample: Mapping[str, Any]
    uncertainty: Mapping[str, Any]
    sources: tuple[SourceLocator, ...]

    def __post_init__(self) -> None:
        _require_text(self.name, "measurement name")
        _require_text(self.unit, "measurement unit")
        _require_text(self.status, "measurement status")
        object.__setattr__(self, "value", _freeze_measurement_value(self.value))
        object.__setattr__(self, "sample", _freeze_mapping(self.sample, "measurement sample"))
        object.__setattr__(
            self,
            "uncertainty",
            _freeze_mapping(self.uncertainty, "measurement uncertainty"),
        )
        object.__setattr__(self, "sources", _freeze_sources(self.sources))


@dataclass(frozen=True, slots=True)
class CoverageEntry:
    """Disposition of one supported source field during projection."""

    source: SourceLocator
    field: str
    status: str
    targets: tuple[OntologyRef, ...]
    reason: str | None

    def __post_init__(self) -> None:
        _require_text(self.field, "coverage field")
        if self.status not in COVERAGE_STATUSES:
            raise ValueError(f"invalid coverage status {self.status!r}")
        _optional_text(self.reason, "coverage reason")
        targets = _freeze_typed_tuple(self.targets, OntologyRef, "coverage targets")
        if self.status == "projected" and not targets:
            raise ValueError("projected coverage requires at least one target")
        if self.status != "projected" and self.reason is None:
            raise ValueError(f"{self.status} coverage requires a reason")
        object.__setattr__(self, "targets", targets)


@dataclass(frozen=True, slots=True)
class OntologyProjection:
    """Complete immutable projection derived from one verified run."""

    schema: str
    source_run: OntologyRef
    objects: tuple[OntologyObject, ...]
    relations: tuple[RelationAssertion, ...]
    measurements: tuple[Measurement, ...]
    coverage: tuple[CoverageEntry, ...]
    projection_digest: str

    def __post_init__(self) -> None:
        _require_text(self.schema, "projection schema")
        _require_digest(self.projection_digest, "projection digest")
        object.__setattr__(
            self,
            "objects",
            _freeze_typed_tuple(self.objects, OntologyObject, "projection objects"),
        )
        object.__setattr__(
            self,
            "relations",
            _freeze_typed_tuple(
                self.relations,
                RelationAssertion,
                "projection relations",
            ),
        )
        object.__setattr__(
            self,
            "measurements",
            _freeze_typed_tuple(
                self.measurements,
                Measurement,
                "projection measurements",
            ),
        )
        object.__setattr__(
            self,
            "coverage",
            _freeze_typed_tuple(self.coverage, CoverageEntry, "projection coverage"),
        )
