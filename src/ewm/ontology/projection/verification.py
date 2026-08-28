"""Fail-closed verification of sealed ontology projection bundles."""

from __future__ import annotations

import json
import math
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast

from ewm.core.provenance.serialization import content_digest

from ..graph.identity import canonical_bytes, projection_from_data
from ..graph.model import OntologyProjection
from ..graph.schema import OntologyValidationError, assert_valid_projection
from .bundles.digest import compute_projection_digest

ONTOLOGY_ARTIFACT_SCHEMA = "ewm.ontology.v1"
PROJECTION_PAYLOADS = ("projection.json", "coverage.json")
EXPECTED_PROJECTION_FILES = frozenset((*PROJECTION_PAYLOADS, "manifest.json"))

_MANIFEST_FIELDS = frozenset(
    {
        "artifact_schema",
        "integrity_level",
        "source_run",
        "adapter",
        "payloads",
        "projection_digest",
        "bundle_sha256",
    }
)
_SOURCE_FIELDS = frozenset(
    {
        "run_hash",
        "identity_sha256",
        "manifest_sha256",
        "bundle_sha256",
        "source_fingerprint",
    }
)
_ADAPTER_FIELDS = frozenset({"identity", "digest"})
_PAYLOAD_METADATA_FIELDS = frozenset({"sha256", "size"})
_PROJECTION_FIELDS = frozenset(
    {
        "record_type",
        "artifact_schema",
        "source_run",
        "objects",
        "relations",
        "measurements",
        "projection_digest",
    }
)
_COVERAGE_FIELDS = frozenset(
    {
        "record_type",
        "artifact_schema",
        "source_run",
        "entries",
        "projection_digest",
    }
)
_HEX_DIGITS = frozenset("0123456789abcdef")


class ProjectionVerificationError(ValueError):
    """Raised when a derived ontology bundle is invalid or internally inconsistent."""


@dataclass(frozen=True, slots=True)
class ProjectionVerificationReport:
    """Verified identity and provenance of one ontology projection bundle."""

    bundle_dir: Path
    artifact_schema: str
    integrity_level: str
    projection_digest: str
    bundle_sha256: str
    source_run_hash: str
    source_identity_sha256: str
    source_manifest_sha256: str
    source_bundle_sha256: str
    source_fingerprint: str
    adapter_identity: str
    adapter_digest: str
    payloads: Mapping[str, Mapping[str, int | str]]


def _fail(message: str) -> ProjectionVerificationError:
    return ProjectionVerificationError(message)


def _object_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _fail(f"JSON object contains duplicate key {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise _fail(f"JSON contains non-finite number {value}")


def _assert_finite(value: Any, location: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise _fail(f"{location} contains a non-finite number")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _assert_finite(item, f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_finite(item, f"{location}[{index}]")


def _load_canonical_json(path: Path) -> tuple[Mapping[str, Any], bytes]:
    try:
        content = path.read_bytes()
        parsed = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_object_from_pairs,
            parse_constant=_reject_constant,
        )
    except ProjectionVerificationError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _fail(f"{path.name} is not valid UTF-8 JSON: {error}") from error
    _assert_finite(parsed, path.name)
    if not isinstance(parsed, Mapping):
        raise _fail(f"{path.name} must contain a JSON object")
    data = cast(Mapping[str, Any], parsed)
    if content != canonical_bytes(data):
        raise _fail(f"{path.name} is not in canonical byte form")
    return data, content


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], location: str) -> None:
    actual = frozenset(value)
    if actual != expected:
        raise _fail(
            f"{location} fields differ: "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )


def _mapping(value: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _fail(f"{location} must be a JSON object")
    return cast(Mapping[str, Any], value)


def _string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise _fail(f"{location} must be a non-empty string")
    return value


def _integer(value: Any, location: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _fail(f"{location} must be an integer")
    return value


def _hex(value: Any, length: int, location: str) -> str:
    text = _string(value, location)
    if len(text) != length or any(character not in _HEX_DIGITS for character in text):
        raise _fail(f"{location} must be {length} lowercase hexadecimal characters")
    return text


def _validate_directory(bundle_dir: Path) -> None:
    try:
        if bundle_dir.is_symlink() or not bundle_dir.is_dir():
            raise _fail("projection bundle must be a real directory")
        entries = tuple(bundle_dir.iterdir())
    except OSError as error:
        raise _fail(f"could not inspect projection bundle: {error}") from error
    names = frozenset(path.name for path in entries)
    if names != EXPECTED_PROJECTION_FILES:
        raise _fail(
            "projection bundle files differ: "
            f"missing={sorted(EXPECTED_PROJECTION_FILES - names)}, "
            f"extra={sorted(names - EXPECTED_PROJECTION_FILES)}"
        )
    for path in entries:
        try:
            mode = path.lstat().st_mode
        except OSError as error:
            raise _fail(f"could not inspect {path.name}: {error}") from error
        if path.is_symlink() or not stat.S_ISREG(mode):
            raise _fail(f"projection bundle entry {path.name!r} must be a regular file")


def _validate_payload_metadata(
    bundle_dir: Path,
    manifest: Mapping[str, Any],
    payload_data: Mapping[str, Mapping[str, Any]],
    payload_bytes: Mapping[str, bytes],
) -> Mapping[str, Mapping[str, int | str]]:
    raw_payloads = _mapping(manifest["payloads"], "manifest.json.payloads")
    if frozenset(raw_payloads) != frozenset(PROJECTION_PAYLOADS):
        raise _fail("manifest.json.payloads must name exactly projection.json and coverage.json")
    verified: dict[str, Mapping[str, int | str]] = {}
    for name in PROJECTION_PAYLOADS:
        metadata = _mapping(raw_payloads[name], f"manifest.json.payloads.{name}")
        _exact_keys(metadata, _PAYLOAD_METADATA_FIELDS, f"manifest.json.payloads.{name}")
        declared_size = _integer(metadata["size"], f"manifest.json.payloads.{name}.size")
        declared_sha = _hex(metadata["sha256"], 64, f"manifest.json.payloads.{name}.sha256")
        if declared_size != len(payload_bytes[name]):
            raise _fail(f"{name} size does not match manifest.json")
        if declared_sha != content_digest(payload_data[name]):
            raise _fail(f"{name} SHA-256 does not match manifest.json")
        verified[name] = MappingProxyType({"sha256": declared_sha, "size": declared_size})
    return MappingProxyType(verified)


def _projection_from_payloads(
    graph: Mapping[str, Any], coverage: Mapping[str, Any]
) -> OntologyProjection:
    _exact_keys(graph, _PROJECTION_FIELDS, "projection.json")
    _exact_keys(coverage, _COVERAGE_FIELDS, "coverage.json")
    if graph["record_type"] != "ontology_projection_graph":
        raise _fail("projection.json has an invalid record_type")
    if coverage["record_type"] != "ontology_coverage":
        raise _fail("coverage.json has an invalid record_type")
    if graph["artifact_schema"] != ONTOLOGY_ARTIFACT_SCHEMA:
        raise _fail("projection.json declares an unsupported artifact schema")
    if coverage["artifact_schema"] != graph["artifact_schema"]:
        raise _fail("coverage.json artifact schema does not match projection.json")
    if coverage["source_run"] != graph["source_run"]:
        raise _fail("coverage.json source run does not match projection.json")
    if coverage["projection_digest"] != graph["projection_digest"]:
        raise _fail("coverage.json projection digest does not match projection.json")
    combined = {
        "record_type": "ontology_projection",
        "schema": graph["artifact_schema"],
        "source_run": graph["source_run"],
        "objects": graph["objects"],
        "relations": graph["relations"],
        "measurements": graph["measurements"],
        "coverage": coverage["entries"],
        "projection_digest": graph["projection_digest"],
    }
    try:
        return projection_from_data(combined)
    except (TypeError, ValueError) as error:
        raise _fail(f"projection payload records are invalid: {error}") from error


def _verify_projection_bundle(
    bundle_dir: Path,
) -> tuple[ProjectionVerificationReport, OntologyProjection]:
    path = Path(bundle_dir)
    _validate_directory(path)
    manifest, _manifest_bytes = _load_canonical_json(path / "manifest.json")
    graph, graph_bytes = _load_canonical_json(path / "projection.json")
    coverage, coverage_bytes = _load_canonical_json(path / "coverage.json")
    _exact_keys(manifest, _MANIFEST_FIELDS, "manifest.json")
    if manifest["artifact_schema"] != ONTOLOGY_ARTIFACT_SCHEMA:
        raise _fail("manifest.json declares an unsupported artifact schema")
    if manifest["integrity_level"] != "checksummed":
        raise _fail("manifest.json.integrity_level must be 'checksummed'")

    source = _mapping(manifest["source_run"], "manifest.json.source_run")
    adapter = _mapping(manifest["adapter"], "manifest.json.adapter")
    _exact_keys(source, _SOURCE_FIELDS, "manifest.json.source_run")
    _exact_keys(adapter, _ADAPTER_FIELDS, "manifest.json.adapter")
    source_run_hash = _hex(source["run_hash"], 20, "manifest.json.source_run.run_hash")
    source_identity = _hex(
        source["identity_sha256"], 64, "manifest.json.source_run.identity_sha256"
    )
    if source_run_hash != source_identity[:20]:
        raise _fail("manifest source run hash is not the identity digest prefix")
    source_manifest = _hex(
        source["manifest_sha256"], 64, "manifest.json.source_run.manifest_sha256"
    )
    source_bundle = _hex(
        source["bundle_sha256"], 64, "manifest.json.source_run.bundle_sha256"
    )
    source_fingerprint = _hex(
        source["source_fingerprint"], 64, "manifest.json.source_run.source_fingerprint"
    )
    adapter_identity = _string(adapter["identity"], "manifest.json.adapter.identity")
    adapter_digest = _hex(adapter["digest"], 64, "manifest.json.adapter.digest")

    payload_data = {"projection.json": graph, "coverage.json": coverage}
    payload_bytes = {"projection.json": graph_bytes, "coverage.json": coverage_bytes}
    payloads = _validate_payload_metadata(path, manifest, payload_data, payload_bytes)
    projection_digest = _hex(
        manifest["projection_digest"], 64, "manifest.json.projection_digest"
    )
    declared_bundle = _hex(manifest["bundle_sha256"], 64, "manifest.json.bundle_sha256")
    bundle_payload = {
        "artifact_schema": manifest["artifact_schema"],
        "source_run": source,
        "adapter": adapter,
        "projection_digest": projection_digest,
        "payloads": manifest["payloads"],
    }
    if declared_bundle != content_digest(bundle_payload):
        raise _fail("manifest.json.bundle_sha256 does not match provenance and payloads")

    projection = _projection_from_payloads(graph, coverage)
    if projection.projection_digest != projection_digest:
        raise _fail("manifest projection digest does not match payloads")
    if compute_projection_digest(projection) != projection_digest:
        raise _fail("projection digest does not match canonical graph and coverage semantics")
    try:
        assert_valid_projection(projection)
    except OntologyValidationError as error:
        raise _fail(f"projection violates ontology schema: {error}") from error

    report = ProjectionVerificationReport(
        bundle_dir=path,
        artifact_schema=ONTOLOGY_ARTIFACT_SCHEMA,
        integrity_level="checksummed",
        projection_digest=projection_digest,
        bundle_sha256=declared_bundle,
        source_run_hash=source_run_hash,
        source_identity_sha256=source_identity,
        source_manifest_sha256=source_manifest,
        source_bundle_sha256=source_bundle,
        source_fingerprint=source_fingerprint,
        adapter_identity=adapter_identity,
        adapter_digest=adapter_digest,
        payloads=payloads,
    )
    return report, projection


def verify_projection_bundle(bundle_dir: Path) -> ProjectionVerificationReport:
    """Verify a sealed ontology bundle without modifying it."""

    report, _projection = _verify_projection_bundle(bundle_dir)
    return report


def load_projection_bundle(bundle_dir: Path) -> OntologyProjection:
    """Return a projection only after its complete bundle verifies."""

    _report, projection = _verify_projection_bundle(bundle_dir)
    return projection
