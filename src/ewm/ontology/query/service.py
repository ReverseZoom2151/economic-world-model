"""Bounded read service over immutable ontology indexes."""

from __future__ import annotations

import base64
import binascii
import json
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any, TypeVar, cast

from ewm.core.provenance.serialization import canonical_json, content_digest

from ..graph.model import (
    Measurement,
    OntologyObject,
    OntologyProjection,
    OntologyRef,
    RelationAssertion,
    SourceLocator,
)
from .contracts import (
    ClaimQuery,
    CursorError,
    EvidenceQuery,
    GeoAnchorQuery,
    MeasurementPage,
    MeasurementQuery,
    ObjectPage,
    ObjectQuery,
    OntologyPath,
    Page,
    PathFilter,
    PathQuery,
    PathResult,
    QueryCostError,
    QueryLimits,
    RelationPage,
    RelationQuery,
)
from .indexes import OntologyIndexes, OntologyRecord, build_indexes

_T = TypeVar("_T")
_CURSOR_VERSION = 1


def _query_data(query: Any) -> Mapping[str, Any]:
    return cast(Mapping[str, Any], asdict(query))


def _query_fingerprint(operation: str, query: object) -> str:
    return content_digest({"operation": operation, "query": _query_data(query)})


def _encode_bytes(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _encode_cursor(projection_digest: str, fingerprint: str, offset: int) -> str:
    payload = {
        "version": _CURSOR_VERSION,
        "projection_digest": projection_digest,
        "query_fingerprint": fingerprint,
        "offset": offset,
    }
    envelope = {"payload": payload, "checksum": content_digest(payload)}
    return _encode_bytes(canonical_json(envelope).encode("utf-8"))


def _decode_cursor(
    cursor: str,
    *,
    projection_digest: str,
    fingerprint: str,
) -> int:
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.b64decode(cursor + padding, altchars=b"-_", validate=True)
        if _encode_bytes(raw) != cursor:
            raise ValueError("cursor is not canonically encoded")
        envelope = json.loads(raw.decode("utf-8"))
        if not isinstance(envelope, dict):
            raise TypeError("cursor envelope must be an object")
        payload = envelope["payload"]
        checksum = envelope["checksum"]
        if not isinstance(payload, dict) or not isinstance(checksum, str):
            raise TypeError("cursor fields are malformed")
        if content_digest(payload) != checksum:
            raise ValueError("cursor checksum does not match")
        version = payload["version"]
        bound_projection = payload["projection_digest"]
        bound_query = payload["query_fingerprint"]
        offset = payload["offset"]
    except (
        KeyError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        binascii.Error,
    ) as error:
        raise CursorError("invalid ontology query cursor") from error
    if version != _CURSOR_VERSION:
        raise CursorError("cursor version is not supported")
    if bound_projection != projection_digest:
        raise CursorError("cursor projection does not match")
    if bound_query != fingerprint:
        raise CursorError("cursor query does not match")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise CursorError("invalid ontology query cursor offset")
    return offset


def _union_buckets(
    index: Mapping[_T, tuple[str, ...]],
    keys: Sequence[_T],
) -> set[str]:
    return {
        record_id
        for key in keys
        for record_id in index.get(key, ())
    }


def _source_ids(
    index: Mapping[SourceLocator, tuple[str, ...]],
    sources: Sequence[SourceLocator],
) -> set[str]:
    return _union_buckets(index, sources)


def _record_layer(record: OntologyRecord) -> str | None:
    if isinstance(record, OntologyObject):
        return record.layer
    if isinstance(record, Measurement):
        return "research_evidence"
    return None


def _geo_valid_at(value: object, point: int | float | str) -> bool:
    if not isinstance(value, Mapping):
        return False
    start = value.get("start")
    end = value.get("end")
    if isinstance(point, str):
        if (start is not None and not isinstance(start, str)) or (
            end is not None and not isinstance(end, str)
        ):
            return False
        return (start is None or point >= start) and (end is None or point <= end)
    if isinstance(point, bool):
        return False
    numeric_types = (int, float)
    invalid_start = start is not None and (
        isinstance(start, bool) or not isinstance(start, numeric_types)
    )
    invalid_end = end is not None and (
        isinstance(end, bool) or not isinstance(end, numeric_types)
    )
    if invalid_start or invalid_end:
        return False
    return (start is None or point >= start) and (end is None or point <= end)


class OntologyQueryService:
    """Read-only, cost-bounded access to one validated ontology projection."""

    def __init__(
        self,
        indexes: OntologyIndexes,
        *,
        limits: QueryLimits | None = None,
    ) -> None:
        self._indexes = indexes
        self._limits = limits or QueryLimits()

    @classmethod
    def from_projection(
        cls,
        projection: OntologyProjection,
        *,
        limits: QueryLimits | None = None,
    ) -> OntologyQueryService:
        """Validate, index, and bind a query service to one projection."""

        return cls(build_indexes(projection), limits=limits)

    @property
    def projection_digest(self) -> str:
        """Return the immutable projection identity served by this instance."""

        return self._indexes.projection_digest

    @property
    def limits(self) -> QueryLimits:
        """Return the immutable limits applied to this instance."""

        return self._limits

    def record(self, record_id: str) -> OntologyRecord:
        """Return one record by exact ID without exposing an internal mapping."""

        try:
            return self._indexes.records_by_id[record_id]
        except KeyError as error:
            raise KeyError(f"unknown ontology record {record_id!r}") from error

    def _validate_filter_cost(self, operation: str, *groups: Sequence[object]) -> None:
        observed = sum(len(group) for group in groups)
        if observed > self._limits.max_filter_values:
            raise QueryCostError(
                code="filter_limit_exceeded",
                operation=operation,
                limit=self._limits.max_filter_values,
                observed=observed,
            )

    def _page_size(self, operation: str, limit: int | None) -> int:
        if limit is None:
            return self._limits.default_page_size
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise QueryCostError(
                code="invalid_page_limit",
                operation=operation,
                limit=self._limits.max_page_size,
                observed=0 if not isinstance(limit, int | bool) else int(limit),
            )
        if limit > self._limits.max_page_size:
            raise QueryCostError(
                code="page_limit_exceeded",
                operation=operation,
                limit=self._limits.max_page_size,
                observed=limit,
            )
        return limit

    def _page(
        self,
        operation: str,
        query: object,
        items: Sequence[_T],
        *,
        limit: int | None,
        cursor: str | None,
    ) -> Page[_T]:
        page_size = self._page_size(operation, limit)
        fingerprint = _query_fingerprint(operation, query)
        offset = (
            0
            if cursor is None
            else _decode_cursor(
                cursor,
                projection_digest=self.projection_digest,
                fingerprint=fingerprint,
            )
        )
        if offset > len(items):
            raise CursorError("cursor offset exceeds the current result set")
        end = min(offset + page_size, len(items))
        next_cursor = (
            _encode_cursor(self.projection_digest, fingerprint, end)
            if end < len(items)
            else None
        )
        return Page(tuple(items[offset:end]), next_cursor, self.projection_digest)

    def objects(
        self,
        query: ObjectQuery | None = None,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> ObjectPage:
        """Return one stable page of ontology objects matching typed filters."""

        request = query or ObjectQuery()
        self._validate_filter_cost(
            "objects",
            request.ids,
            request.kinds,
            request.layers,
            request.run_ids,
            request.episode_ids,
            request.sources,
        )
        candidates = {item.ref.id for item in self._indexes.projection.objects}
        if request.ids:
            candidates &= set(request.ids)
        if request.kinds:
            candidates &= _union_buckets(self._indexes.object_ids_by_kind, request.kinds)
        if request.layers:
            candidates &= _union_buckets(self._indexes.object_ids_by_layer, request.layers)
        if request.run_ids:
            candidates &= _union_buckets(self._indexes.record_ids_by_run, request.run_ids)
        if request.episode_ids:
            candidates &= _union_buckets(
                self._indexes.record_ids_by_episode,
                request.episode_ids,
            )
        if request.sources:
            candidates &= _source_ids(self._indexes.record_ids_by_source, request.sources)
        if request.event_sequence is not None:
            candidates &= {
                record_id
                for sequence, record_ids in self._indexes.record_ids_by_event_sequence.items()
                if request.event_sequence.contains(sequence)
                for record_id in record_ids
            }
        if request.time is not None:
            candidates &= {
                record_id
                for time, record_ids in self._indexes.record_ids_by_time.items()
                if request.time.contains(time)
                for record_id in record_ids
            }
        items = tuple(
            cast(OntologyObject, self._indexes.records_by_id[record_id])
            for record_id in sorted(candidates)
        )
        return self._page("objects", request, items, limit=limit, cursor=cursor)

    def relations(
        self,
        query: RelationQuery | None = None,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> RelationPage:
        """Return one stable page of directed relation assertions."""

        request = query or RelationQuery()
        self._validate_filter_cost(
            "relations",
            request.ids,
            request.relation_types,
            request.source_ids,
            request.target_ids,
            request.incident_ids,
            request.sources,
        )
        candidates = {item.ref.id for item in self._indexes.projection.relations}
        if request.ids:
            candidates &= set(request.ids)
        if request.relation_types:
            candidates &= _union_buckets(
                self._indexes.relation_ids_by_type,
                request.relation_types,
            )
        if request.source_ids:
            candidates &= _union_buckets(
                self._indexes.outgoing_relation_ids,
                request.source_ids,
            )
        if request.target_ids:
            candidates &= _union_buckets(
                self._indexes.incoming_relation_ids,
                request.target_ids,
            )
        if request.incident_ids:
            incident: set[str] = set()
            if request.direction in {"outgoing", "both"}:
                incident |= _union_buckets(
                    self._indexes.outgoing_relation_ids,
                    request.incident_ids,
                )
            if request.direction in {"incoming", "both"}:
                incident |= _union_buckets(
                    self._indexes.incoming_relation_ids,
                    request.incident_ids,
                )
            candidates &= incident
        if request.sources:
            candidates &= _source_ids(self._indexes.record_ids_by_source, request.sources)
        items = tuple(
            cast(RelationAssertion, self._indexes.records_by_id[record_id])
            for record_id in sorted(candidates)
        )
        return self._page("relations", request, items, limit=limit, cursor=cursor)

    def measurements(
        self,
        query: MeasurementQuery | None = None,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> MeasurementPage:
        """Return one stable page of measurement records."""

        request = query or MeasurementQuery()
        self._validate_filter_cost(
            "measurements",
            request.ids,
            request.names,
            request.statuses,
            request.units,
            request.subject_ids,
            request.sources,
        )
        candidates = {item.ref.id for item in self._indexes.projection.measurements}
        if request.ids:
            candidates &= set(request.ids)
        for values, index in (
            (request.names, self._indexes.measurement_ids_by_name),
            (request.statuses, self._indexes.measurement_ids_by_status),
            (request.units, self._indexes.measurement_ids_by_unit),
            (request.subject_ids, self._indexes.measurement_ids_by_subject),
        ):
            if values:
                candidates &= _union_buckets(index, values)
        if request.sources:
            candidates &= _source_ids(self._indexes.record_ids_by_source, request.sources)
        items = tuple(
            cast(Measurement, self._indexes.records_by_id[record_id])
            for record_id in sorted(candidates)
        )
        return self._page("measurements", request, items, limit=limit, cursor=cursor)

    def claims(
        self,
        query: ClaimQuery | None = None,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> ObjectPage:
        """Return claims with their source classification unchanged."""

        request = query or ClaimQuery()
        self._validate_filter_cost(
            "claims",
            request.ids,
            request.classifications,
            request.sources,
        )
        candidates = set(self._indexes.object_ids_by_kind.get("claim", ()))
        if request.ids:
            candidates &= set(request.ids)
        if request.classifications:
            candidates &= _union_buckets(
                self._indexes.claim_ids_by_classification,
                request.classifications,
            )
        if request.sources:
            candidates &= _source_ids(self._indexes.record_ids_by_source, request.sources)
        items = tuple(
            cast(OntologyObject, self._indexes.records_by_id[record_id])
            for record_id in sorted(candidates)
        )
        return self._page("claims", request, items, limit=limit, cursor=cursor)

    def evidence(
        self,
        query: EvidenceQuery | None = None,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> ObjectPage:
        """Return evidence artifacts without promoting their classification."""

        request = query or EvidenceQuery()
        self._validate_filter_cost(
            "evidence",
            request.ids,
            request.classifications,
            request.sources,
        )
        candidates = set(self._indexes.object_ids_by_kind.get("evidence_artifact", ()))
        if request.ids:
            candidates &= set(request.ids)
        if request.classifications:
            candidates &= _union_buckets(
                self._indexes.evidence_ids_by_classification,
                request.classifications,
            )
        if request.sources:
            candidates &= _source_ids(self._indexes.record_ids_by_source, request.sources)
        items = tuple(
            cast(OntologyObject, self._indexes.records_by_id[record_id])
            for record_id in sorted(candidates)
        )
        return self._page("evidence", request, items, limit=limit, cursor=cursor)

    def geo_anchors(
        self,
        query: GeoAnchorQuery | None = None,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> ObjectPage:
        """Return explicit geographic anchors active at an optional declared time."""

        request = query or GeoAnchorQuery()
        self._validate_filter_cost("geo_anchors", request.ids, request.bases)
        candidates = set(self._indexes.object_ids_by_kind.get("geo_anchor", ()))
        if request.ids:
            candidates &= set(request.ids)
        if request.bases:
            candidates &= _union_buckets(
                self._indexes.geo_anchor_ids_by_basis,
                request.bases,
            )
        items = tuple(
            cast(OntologyObject, self._indexes.records_by_id[record_id])
            for record_id in sorted(candidates)
        )
        if request.valid_at is not None:
            items = tuple(
                item
                for item in items
                if _geo_valid_at(item.properties.get("validity"), request.valid_at)
            )
        return self._page("geo_anchors", request, items, limit=limit, cursor=cursor)

    def _path_filter_cost(self, path_filter: PathFilter) -> None:
        self._validate_filter_cost(
            "paths",
            path_filter.relation_types,
            path_filter.object_kinds,
            path_filter.object_layers,
        )

    def _adjacent(
        self,
        record_id: str,
        path_filter: PathFilter,
    ) -> tuple[tuple[RelationAssertion, OntologyRef], ...]:
        relation_ids: set[str] = set()
        if path_filter.direction in {"outgoing", "both"}:
            relation_ids.update(self._indexes.outgoing_relation_ids.get(record_id, ()))
        if path_filter.direction in {"incoming", "both"}:
            relation_ids.update(self._indexes.incoming_relation_ids.get(record_id, ()))
        adjacent: list[tuple[RelationAssertion, OntologyRef]] = []
        for relation_id in sorted(relation_ids):
            relation = cast(RelationAssertion, self._indexes.records_by_id[relation_id])
            if (
                path_filter.relation_types
                and relation.relation_type not in path_filter.relation_types
            ):
                continue
            neighbor = relation.target if relation.source.id == record_id else relation.source
            neighbor_record = self._indexes.records_by_id.get(neighbor.id)
            if neighbor_record is None or isinstance(neighbor_record, RelationAssertion):
                continue
            if path_filter.object_kinds and neighbor.kind not in path_filter.object_kinds:
                continue
            layer = _record_layer(neighbor_record)
            if path_filter.object_layers and layer not in path_filter.object_layers:
                continue
            adjacent.append((relation, neighbor))
        return tuple(adjacent)

    def paths(self, query: PathQuery) -> PathResult:
        """Return deterministic simple paths within explicit depth and visit caps."""

        self._path_filter_cost(query.filter)
        if query.max_depth > self._limits.max_traversal_depth:
            raise QueryCostError(
                code="traversal_depth_exceeded",
                operation="paths",
                limit=self._limits.max_traversal_depth,
                observed=query.max_depth,
            )
        path_limit = query.limit or self._limits.default_path_limit
        if path_limit > self._limits.max_paths:
            raise QueryCostError(
                code="path_limit_exceeded",
                operation="paths",
                limit=self._limits.max_paths,
                observed=path_limit,
            )
        start_record = self.record(query.start_id)
        target_record = self.record(query.target_id)
        if isinstance(start_record, RelationAssertion) or isinstance(
            target_record,
            RelationAssertion,
        ):
            raise ValueError("path endpoints must be ontology objects or measurements")
        start_ref = start_record.ref
        if query.start_id == query.target_id:
            return PathResult(
                paths=(OntologyPath((start_ref,), ()),),
                visited_records=1,
                truncated=False,
                projection_digest=self.projection_digest,
            )

        queue: deque[tuple[tuple[OntologyRef, ...], tuple[RelationAssertion, ...]]] = deque(
            [((start_ref,), ())]
        )
        discovered = {query.start_id}
        results: list[OntologyPath] = []
        truncated = False
        while queue:
            nodes, relations = queue.popleft()
            if len(relations) >= query.max_depth:
                continue
            node_ids = {node.id for node in nodes}
            for relation, neighbor in self._adjacent(nodes[-1].id, query.filter):
                if neighbor.id in node_ids:
                    continue
                discovered.add(neighbor.id)
                if len(discovered) > self._limits.max_visited_records:
                    raise QueryCostError(
                        code="visited_record_limit_exceeded",
                        operation="paths",
                        limit=self._limits.max_visited_records,
                        observed=len(discovered),
                    )
                next_nodes = (*nodes, neighbor)
                next_relations = (*relations, relation)
                if neighbor.id == query.target_id:
                    if len(results) < path_limit:
                        results.append(OntologyPath(next_nodes, next_relations))
                    else:
                        truncated = True
                    continue
                queue.append((next_nodes, next_relations))

        ordered = tuple(
            sorted(
                results,
                key=lambda path: (
                    tuple(relation.ref.id for relation in path.relations),
                    tuple(node.id for node in path.nodes),
                ),
            )
        )
        return PathResult(
            paths=ordered,
            visited_records=len(discovered),
            truncated=truncated,
            projection_digest=self.projection_digest,
        )
