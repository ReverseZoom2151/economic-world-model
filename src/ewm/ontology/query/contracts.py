"""Immutable request, response, cursor, and cost contracts for ontology reads."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Generic, Literal, TypeAlias, TypeVar

from ..graph.model import (
    Measurement,
    OntologyObject,
    OntologyRef,
    RelationAssertion,
    SourceLocator,
)

TimeBound: TypeAlias = int | float | str
Direction: TypeAlias = Literal["outgoing", "incoming", "both"]
_T = TypeVar("_T")


def _text_tuple(values: tuple[str, ...], name: str) -> tuple[str, ...]:
    frozen = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in frozen):
        raise ValueError(f"{name} must contain only non-empty text")
    return tuple(sorted(set(frozen)))


def _source_tuple(values: tuple[SourceLocator, ...]) -> tuple[SourceLocator, ...]:
    frozen = tuple(values)
    if not all(isinstance(value, SourceLocator) for value in frozen):
        raise TypeError("sources must contain only SourceLocator values")
    return tuple(sorted(set(frozen), key=repr))


def _validate_direction(direction: Direction) -> None:
    if direction not in {"outgoing", "incoming", "both"}:
        raise ValueError("direction must be 'outgoing', 'incoming', or 'both'")


def _bound_family(value: TimeBound) -> str:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise TypeError("time bounds must be finite numbers or text")
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("time bounds must be finite")
    if isinstance(value, str):
        if not value.strip():
            raise ValueError("time bounds must not be empty")
        return "text"
    return "numeric"


@dataclass(frozen=True, slots=True)
class SequenceWindow:
    """Inclusive event-sequence interval."""

    start: int | None = None
    end: int | None = None

    def __post_init__(self) -> None:
        for value in (self.start, self.end):
            if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value < 0
            ):
                raise ValueError("event sequence bounds must be non-negative integers")
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValueError("event sequence start must not exceed end")

    def contains(self, value: int) -> bool:
        """Return whether a sequence lies inside the inclusive interval."""

        return (self.start is None or value >= self.start) and (
            self.end is None or value <= self.end
        )


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """Inclusive, type-consistent numeric or textual time interval."""

    start: TimeBound | None = None
    end: TimeBound | None = None

    def __post_init__(self) -> None:
        families = tuple(
            _bound_family(value) for value in (self.start, self.end) if value is not None
        )
        if len(set(families)) > 1:
            raise TypeError("time window bounds must use the same type family")
        if self.start is not None and self.end is not None and self.start > self.end:  # type: ignore[operator]
            raise ValueError("time window start must not exceed end")

    def contains(self, value: TimeBound) -> bool:
        """Return whether a compatible time value lies in the inclusive interval."""

        family = _bound_family(value)
        bounds = tuple(bound for bound in (self.start, self.end) if bound is not None)
        if bounds and family != _bound_family(bounds[0]):
            return False
        return (self.start is None or value >= self.start) and (  # type: ignore[operator]
            self.end is None or value <= self.end  # type: ignore[operator]
        )


@dataclass(frozen=True, slots=True)
class ObjectQuery:
    """Typed filters over ontology objects."""

    ids: tuple[str, ...] = ()
    kinds: tuple[str, ...] = ()
    layers: tuple[str, ...] = ()
    run_ids: tuple[str, ...] = ()
    episode_ids: tuple[str, ...] = ()
    sources: tuple[SourceLocator, ...] = ()
    event_sequence: SequenceWindow | None = None
    time: TimeWindow | None = None

    def __post_init__(self) -> None:
        for field_name in ("ids", "kinds", "layers", "run_ids", "episode_ids"):
            object.__setattr__(self, field_name, _text_tuple(getattr(self, field_name), field_name))
        object.__setattr__(self, "sources", _source_tuple(self.sources))


@dataclass(frozen=True, slots=True)
class RelationQuery:
    """Typed filters over directed relation assertions."""

    ids: tuple[str, ...] = ()
    relation_types: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    target_ids: tuple[str, ...] = ()
    incident_ids: tuple[str, ...] = ()
    direction: Direction = "both"
    sources: tuple[SourceLocator, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "ids",
            "relation_types",
            "source_ids",
            "target_ids",
            "incident_ids",
        ):
            object.__setattr__(self, field_name, _text_tuple(getattr(self, field_name), field_name))
        object.__setattr__(self, "sources", _source_tuple(self.sources))
        _validate_direction(self.direction)


@dataclass(frozen=True, slots=True)
class MeasurementQuery:
    """Typed filters over numerical measurement records."""

    ids: tuple[str, ...] = ()
    names: tuple[str, ...] = ()
    statuses: tuple[str, ...] = ()
    units: tuple[str, ...] = ()
    subject_ids: tuple[str, ...] = ()
    sources: tuple[SourceLocator, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("ids", "names", "statuses", "units", "subject_ids"):
            object.__setattr__(self, field_name, _text_tuple(getattr(self, field_name), field_name))
        object.__setattr__(self, "sources", _source_tuple(self.sources))


@dataclass(frozen=True, slots=True)
class ClaimQuery:
    """Typed filters over claim objects without changing evidence status."""

    ids: tuple[str, ...] = ()
    classifications: tuple[str, ...] = ()
    sources: tuple[SourceLocator, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "ids", _text_tuple(self.ids, "ids"))
        object.__setattr__(
            self,
            "classifications",
            _text_tuple(self.classifications, "classifications"),
        )
        object.__setattr__(self, "sources", _source_tuple(self.sources))


@dataclass(frozen=True, slots=True)
class EvidenceQuery:
    """Typed filters over evidence artifacts and their original classifications."""

    ids: tuple[str, ...] = ()
    classifications: tuple[str, ...] = ()
    sources: tuple[SourceLocator, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "ids", _text_tuple(self.ids, "ids"))
        object.__setattr__(
            self,
            "classifications",
            _text_tuple(self.classifications, "classifications"),
        )
        object.__setattr__(self, "sources", _source_tuple(self.sources))


@dataclass(frozen=True, slots=True)
class GeoAnchorQuery:
    """Typed filters over explicit geographic anchors."""

    ids: tuple[str, ...] = ()
    bases: tuple[str, ...] = ()
    valid_at: TimeBound | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "ids", _text_tuple(self.ids, "ids"))
        object.__setattr__(self, "bases", _text_tuple(self.bases, "bases"))
        if self.valid_at is not None:
            _bound_family(self.valid_at)


@dataclass(frozen=True, slots=True)
class PathFilter:
    """Typed edge direction and node constraints for graph traversal."""

    relation_types: tuple[str, ...] = ()
    object_kinds: tuple[str, ...] = ()
    object_layers: tuple[str, ...] = ()
    direction: Direction = "outgoing"

    def __post_init__(self) -> None:
        for field_name in ("relation_types", "object_kinds", "object_layers"):
            object.__setattr__(self, field_name, _text_tuple(getattr(self, field_name), field_name))
        _validate_direction(self.direction)


@dataclass(frozen=True, slots=True)
class PathQuery:
    """One explicitly bounded graph path request."""

    start_id: str
    target_id: str
    max_depth: int = 1
    limit: int | None = None
    filter: PathFilter = PathFilter()

    def __post_init__(self) -> None:
        if not self.start_id.strip() or not self.target_id.strip():
            raise ValueError("path endpoints must not be empty")
        if not isinstance(self.max_depth, int) or isinstance(self.max_depth, bool):
            raise TypeError("path max_depth must be an integer")
        if self.max_depth < 0:
            raise ValueError("path max_depth must be non-negative")
        if self.limit is not None and (
            not isinstance(self.limit, int) or isinstance(self.limit, bool) or self.limit <= 0
        ):
            raise ValueError("path limit must be a positive integer")


@dataclass(frozen=True, slots=True)
class QueryLimits:
    """Global caps applied to every ontology read operation."""

    default_page_size: int = 50
    max_page_size: int = 200
    max_filter_values: int = 20
    max_traversal_depth: int = 4
    max_visited_records: int = 1_000
    default_path_limit: int = 25
    max_paths: int = 200

    def __post_init__(self) -> None:
        values = (
            self.default_page_size,
            self.max_page_size,
            self.max_filter_values,
            self.max_traversal_depth,
            self.max_visited_records,
            self.default_path_limit,
            self.max_paths,
        )
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value <= 0
            for value in values
        ):
            raise ValueError("query limits must be positive integers")
        if self.default_page_size > self.max_page_size:
            raise ValueError("default page size cannot exceed maximum page size")
        if self.default_path_limit > self.max_paths:
            raise ValueError("default path limit cannot exceed maximum paths")


class QueryCostError(ValueError):
    """A machine-readable rejection of a query above a declared cost cap."""

    def __init__(
        self,
        *,
        code: str,
        operation: str,
        limit: int,
        observed: int,
    ) -> None:
        self.code = code
        self.operation = operation
        self.limit = limit
        self.observed = observed
        super().__init__(f"{operation} rejected: {code} ({observed} > {limit})")

    def as_dict(self) -> dict[str, str | int]:
        """Return the stable transport form of this rejection."""

        return {
            "code": self.code,
            "operation": self.operation,
            "limit": self.limit,
            "observed": self.observed,
        }


class CursorError(ValueError):
    """Raised when an opaque cursor is malformed, stale, or query-incompatible."""


@dataclass(frozen=True, slots=True)
class Page(Generic[_T]):
    """One immutable bounded result page."""

    items: tuple[_T, ...]
    next_cursor: str | None
    projection_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))


@dataclass(frozen=True, slots=True)
class OntologyPath:
    """One immutable node-and-edge path through an ontology projection."""

    nodes: tuple[OntologyRef, ...]
    relations: tuple[RelationAssertion, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "relations", tuple(self.relations))


@dataclass(frozen=True, slots=True)
class PathResult:
    """Bounded deterministic paths plus traversal-cost evidence."""

    paths: tuple[OntologyPath, ...]
    visited_records: int
    truncated: bool
    projection_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "paths", tuple(self.paths))


ObjectPage: TypeAlias = Page[OntologyObject]
RelationPage: TypeAlias = Page[RelationAssertion]
MeasurementPage: TypeAlias = Page[Measurement]
