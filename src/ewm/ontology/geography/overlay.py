"""Strict parser and projector for canonical external geographic sidecars."""

from __future__ import annotations

import json
import stat
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from ewm.core.provenance.serialization import content_digest

from ..graph.identity import make_ontology_ref
from ..graph.model import (
    CoverageEntry,
    OntologyObject,
    OntologyProjection,
    RelationAssertion,
    SourceLocator,
)
from ..graph.schema import OntologyValidationError, assert_valid_projection
from ..projection.service import seal_projection
from .contracts import GeoOverlayApplication, GeoOverlayError

GEO_OVERLAY_SCHEMA = "ewm.geo-overlay.v1"
_MAX_OVERLAY_BYTES = 10 * 1024 * 1024
_TOP_LEVEL_FIELDS = frozenset({"schema", "anchors"})
_ANCHOR_FIELDS = frozenset(
    {
        "target_id",
        "crs",
        "latitude",
        "longitude",
        "anchor_basis",
        "validity",
        "uncertainty_km",
        "source",
    }
)
_SOURCE_FIELDS = frozenset(
    {
        "source_kind",
        "source_id",
        "artifact_path",
        "record_selector",
        "code_symbol",
        "paper_anchor",
        "payload_digest",
    }
)
_REQUIRED_SOURCE_FIELDS = frozenset({"source_kind", "source_id", "payload_digest"})


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GeoOverlayError(f"geo overlay contains duplicate field {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise GeoOverlayError(f"geo overlay contains non-finite number {value}")


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise GeoOverlayError(f"{name} must be an object")
    return cast(Mapping[str, Any], value)


def _fields(value: Mapping[str, Any], expected: frozenset[str], name: str) -> None:
    observed = frozenset(value)
    if observed != expected:
        raise GeoOverlayError(
            f"{name} fields differ: missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GeoOverlayError(f"{name} must be non-empty text")
    return value


def _optional_text(value: object, name: str) -> str | None:
    return None if value is None else _text(value, name)


def _source(value: object) -> SourceLocator:
    data = _mapping(value, "anchor source")
    observed = frozenset(data)
    if not observed.issuperset(_REQUIRED_SOURCE_FIELDS) or not observed.issubset(
        _SOURCE_FIELDS
    ):
        raise GeoOverlayError(
            "anchor source fields differ: "
            f"missing={sorted(_REQUIRED_SOURCE_FIELDS - observed)}, "
            f"unknown={sorted(observed - _SOURCE_FIELDS)}"
        )
    digest = _text(data["payload_digest"], "anchor source payload_digest")
    try:
        return SourceLocator(
            source_kind=_text(data["source_kind"], "anchor source source_kind"),
            source_id=_text(data["source_id"], "anchor source source_id"),
            artifact_path=_optional_text(
                data.get("artifact_path"), "anchor source artifact_path"
            ),
            record_selector=_optional_text(
                data.get("record_selector"), "anchor source record_selector"
            ),
            code_symbol=_optional_text(
                data.get("code_symbol"), "anchor source code_symbol"
            ),
            paper_anchor=_optional_text(
                data.get("paper_anchor"), "anchor source paper_anchor"
            ),
            payload_digest=digest,
        )
    except (TypeError, ValueError) as error:
        raise GeoOverlayError(f"invalid anchor source: {error}") from error


def _read(path: Path) -> Mapping[str, Any]:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise GeoOverlayError(f"cannot inspect geo overlay: {error}") from error
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise GeoOverlayError("geo overlay must be a regular non-symlink file")
    if metadata.st_size > _MAX_OVERLAY_BYTES:
        raise GeoOverlayError("geo overlay exceeds the 10 MiB input limit")
    try:
        text = path.read_text(encoding="utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_object_pairs,
            parse_constant=_reject_constant,
        )
    except GeoOverlayError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise GeoOverlayError(f"cannot decode geo overlay: {error}") from error
    return _mapping(value, "geo overlay")


def _normalized_anchor(value: object) -> dict[str, Any]:
    data = _mapping(value, "geo overlay anchor")
    _fields(data, _ANCHOR_FIELDS, "geo overlay anchor")
    validity = _mapping(data["validity"], "anchor validity")
    _fields(validity, frozenset({"start", "end"}), "anchor validity")
    source = _source(data["source"])
    return {
        "target_id": _text(data["target_id"], "anchor target_id"),
        "crs": _text(data["crs"], "anchor crs"),
        "latitude": data["latitude"],
        "longitude": data["longitude"],
        "anchor_basis": _text(data["anchor_basis"], "anchor basis"),
        "validity": {"start": validity["start"], "end": validity["end"]},
        "uncertainty_km": data["uncertainty_km"],
        "source": source,
    }


def apply_geo_overlay(
    projection: OntologyProjection,
    overlay_path: Path,
) -> GeoOverlayApplication:
    """Apply one CLI-approved overlay and reseal the projection identity."""

    raw = _read(Path(overlay_path))
    _fields(raw, _TOP_LEVEL_FIELDS, "geo overlay")
    if raw["schema"] != GEO_OVERLAY_SCHEMA:
        raise GeoOverlayError(f"geo overlay schema must be {GEO_OVERLAY_SCHEMA!r}")
    anchors_value = raw["anchors"]
    if not isinstance(anchors_value, Sequence) or isinstance(anchors_value, str | bytes):
        raise GeoOverlayError("geo overlay anchors must be an array")
    normalized = tuple(
        sorted(
            (_normalized_anchor(value) for value in anchors_value),
            key=lambda value: value["target_id"],
        )
    )
    if not normalized:
        raise GeoOverlayError("geo overlay must contain at least one anchor")
    target_ids = tuple(str(value["target_id"]) for value in normalized)
    if len(set(target_ids)) != len(target_ids):
        raise GeoOverlayError("geo overlay contains duplicate target identities")
    objects = {item.ref.id: item for item in projection.objects}
    unknown = sorted(set(target_ids) - objects.keys())
    if unknown:
        raise GeoOverlayError(f"geo overlay targets unknown ontology identities: {unknown}")
    existing = {
        relation.source.id
        for relation in projection.relations
        if relation.relation_type == "GEO_ANCHORED_AT"
    }
    duplicates = sorted(existing & set(target_ids))
    if duplicates:
        raise GeoOverlayError(f"ontology identities already have geo anchors: {duplicates}")
    normalized_data = {
        "schema": GEO_OVERLAY_SCHEMA,
        "anchors": [
            {
                **{key: value for key, value in item.items() if key != "source"},
                "source": {
                    "source_kind": item["source"].source_kind,
                    "source_id": item["source"].source_id,
                    "artifact_path": item["source"].artifact_path,
                    "record_selector": item["source"].record_selector,
                    "code_symbol": item["source"].code_symbol,
                    "paper_anchor": item["source"].paper_anchor,
                    "payload_digest": item["source"].payload_digest,
                },
            }
            for item in normalized
        ],
    }
    overlay_digest = content_digest(normalized_data)
    overlay_source = SourceLocator(
        source_kind="geo_overlay",
        source_id=f"sha256:{overlay_digest}",
        artifact_path=Path(overlay_path).name,
        payload_digest=overlay_digest,
    )
    geo_objects: list[OntologyObject] = []
    geo_relations: list[RelationAssertion] = []
    geo_coverage: list[CoverageEntry] = []
    for item in normalized:
        target_id = str(item["target_id"])
        target = objects[target_id]
        properties = {
            "crs": item["crs"],
            "latitude": item["latitude"],
            "longitude": item["longitude"],
            "anchor_basis": item["anchor_basis"],
            "evidence_classification": "researcher_declared",
            "validity": item["validity"],
            "uncertainty_km": item["uncertainty_km"],
            "overlay_digest": overlay_digest,
        }
        anchor_ref = make_ontology_ref(
            namespace="geo",
            kind="geo_anchor",
            source_identity=overlay_digest,
            semantic_keys={"target_id": target_id, "anchor": properties},
        )
        relation_ref = make_ontology_ref(
            namespace="geo",
            kind="relation_assertion",
            source_identity=overlay_digest,
            semantic_keys={"type": "GEO_ANCHORED_AT", "target_id": target_id},
        )
        entry_source = cast(SourceLocator, item["source"])
        sources = (entry_source, overlay_source)
        anchor = OntologyObject(
            ref=anchor_ref,
            layer="provenance",
            properties=properties,
            sources=sources,
        )
        relation = RelationAssertion(
            ref=relation_ref,
            relation_type="GEO_ANCHORED_AT",
            source=target.ref,
            target=anchor_ref,
            properties={"evidence_classification": "researcher_declared"},
            sources=sources,
        )
        geo_objects.append(anchor)
        geo_relations.append(relation)
        geo_coverage.append(
            CoverageEntry(
                source=overlay_source,
                field=f"geo_overlay.{target_id}",
                status="projected",
                targets=(target.ref, anchor_ref, relation_ref),
                reason=None,
            )
        )
    result = seal_projection(
        schema=projection.schema,
        source_run=projection.source_run,
        objects=(*projection.objects, *geo_objects),
        relations=(*projection.relations, *geo_relations),
        measurements=projection.measurements,
        coverage=tuple(sorted((*projection.coverage, *geo_coverage), key=lambda item: item.field)),
    )
    try:
        assert_valid_projection(result)
    except OntologyValidationError as error:
        raise GeoOverlayError(f"geo overlay produces an invalid projection: {error}") from error
    return GeoOverlayApplication(result, overlay_digest, len(geo_objects))
