"""Fail-closed verification for sealed and legacy experiment bundles."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import stat
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np

from .identity import ARTIFACT_SCHEMA, canonical_identity, canonical_json_bytes, identity_sha256

LEGACY_ARTIFACT_SCHEMA = "ewm.run.v1"
PAYLOAD_FILENAMES = (
    "config.json",
    "events.jsonl",
    "metrics.json",
    "summary.csv",
    "trace.npz",
)
EXPECTED_FILENAMES = frozenset((*PAYLOAD_FILENAMES, "manifest.json"))
_IDENTITY_FIELDS = frozenset(
    {
        "artifact_schema",
        "experiment",
        "package_version",
        "parameters",
        "preset",
        "runtime_environment",
        "scenario",
        "seed",
        "source_fingerprint",
    }
)
_LEGACY_MANIFEST_FIELDS = frozenset(
    {
        "artifact_schema",
        "experiment",
        "package_version",
        "preset",
        "runtime_environment",
        "run_hash",
        "scenario",
        "seed",
        "source_fingerprint",
    }
)
_V2_MANIFEST_FIELDS = _LEGACY_MANIFEST_FIELDS | frozenset(
    {"bundle_sha256", "identity", "identity_sha256", "integrity_level", "payloads"}
)
_CONFIG_FIELDS = frozenset(
    {"experiment", "metadata", "parameters", "preset", "scenario", "seed"}
)
_HEX_DIGITS = frozenset("0123456789abcdef")


class ArtifactVerificationError(ValueError):
    """Raised when an artifact directory does not satisfy its declared contract."""


@dataclass(frozen=True, slots=True)
class VerificationReport:
    """Verified identity and integrity status for one artifact directory."""

    run_dir: Path
    artifact_schema: str
    run_hash: str
    identity_sha256: str | None
    integrity_level: str
    payloads: Mapping[str, Mapping[str, int | str]]
    bundle_sha256: str | None


def _fail(message: str) -> ArtifactVerificationError:
    return ArtifactVerificationError(message)


def _object_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _fail(f"JSON object contains duplicate key {key!r}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise _fail(f"JSON contains non-finite number {value}")


def _assert_finite_json(value: object, *, location: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise _fail(f"{location} contains a non-finite number")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _assert_finite_json(item, location=f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_finite_json(item, location=f"{location}[{index}]")


def _load_json_bytes(content: bytes, *, filename: str) -> Any:
    try:
        parsed = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_object_from_pairs,
            parse_constant=_reject_json_constant,
        )
    except ArtifactVerificationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _fail(f"{filename} is not valid UTF-8 JSON: {error}") from error
    _assert_finite_json(parsed, location=filename)
    return parsed


def _load_json_file(path: Path) -> Any:
    try:
        return _load_json_bytes(path.read_bytes(), filename=path.name)
    except OSError as error:
        raise _fail(f"could not read {path.name}: {error}") from error


def _require_mapping(value: object, *, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _fail(f"{location} must be a JSON object")
    return value


def _require_exact_keys(
    value: Mapping[str, Any], expected: frozenset[str], *, location: str
) -> None:
    actual = frozenset(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise _fail(f"{location} fields differ: missing={missing}, extra={extra}")


def _require_string(value: object, *, location: str) -> str:
    if not isinstance(value, str):
        raise _fail(f"{location} must be a string")
    return value


def _require_int(value: object, *, location: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _fail(f"{location} must be an integer")
    return value


def _require_hex(value: object, *, length: int, location: str) -> str:
    text = _require_string(value, location=location)
    if len(text) != length or any(character not in _HEX_DIGITS for character in text):
        raise _fail(f"{location} must be {length} lowercase hexadecimal characters")
    return text


def _validate_runtime_environment(value: object, *, location: str) -> Mapping[str, Any]:
    environment = _require_mapping(value, location=location)
    if not all(isinstance(key, str) and isinstance(item, str) for key, item in environment.items()):
        raise _fail(f"{location} must map strings to strings")
    return environment


def _validate_common_manifest(manifest: Mapping[str, Any]) -> None:
    for field in ("experiment", "package_version", "preset", "scenario"):
        _require_string(manifest[field], location=f"manifest.json.{field}")
    _require_int(manifest["seed"], location="manifest.json.seed")
    _require_hex(manifest["run_hash"], length=20, location="manifest.json.run_hash")
    _require_hex(
        manifest["source_fingerprint"],
        length=64,
        location="manifest.json.source_fingerprint",
    )
    _validate_runtime_environment(
        manifest["runtime_environment"], location="manifest.json.runtime_environment"
    )


def _validate_config(run_dir: Path, manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    config = _require_mapping(
        _load_json_file(run_dir / "config.json"), location="config.json"
    )
    _require_exact_keys(config, _CONFIG_FIELDS, location="config.json")
    _require_mapping(config["metadata"], location="config.json.metadata")
    _require_mapping(config["parameters"], location="config.json.parameters")
    for field in ("experiment", "preset", "scenario"):
        _require_string(config[field], location=f"config.json.{field}")
        if config[field] != manifest[field]:
            raise _fail(f"config.json.{field} does not match manifest.json")
    _require_int(config["seed"], location="config.json.seed")
    if config["seed"] != manifest["seed"]:
        raise _fail("config.json.seed does not match manifest.json")
    return config


def _validate_metrics_and_summary(run_dir: Path) -> None:
    metrics = _require_mapping(
        _load_json_file(run_dir / "metrics.json"), location="metrics.json"
    )
    for name, value in metrics.items():
        if not isinstance(name, str):
            raise _fail("metrics.json names must be strings")
        if isinstance(value, bool):
            continue
        if not isinstance(value, int | float):
            raise _fail(f"metrics.json metric {name!r} must be scalar")
        if isinstance(value, float) and not math.isfinite(value):
            raise _fail(f"metrics.json metric {name!r} must be finite")

    try:
        summary_text = (run_dir / "summary.csv").read_text(encoding="utf-8")
        rows = list(csv.reader(io.StringIO(summary_text, newline=""), strict=True))
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise _fail(f"summary.csv is malformed: {error}") from error
    expected_rows = [["metric", "value"], *[[name, str(metrics[name])] for name in sorted(metrics)]]
    if rows != expected_rows:
        raise _fail("summary.csv does not exactly represent metrics.json")


def _validate_trace(run_dir: Path) -> None:
    path = run_dir / "trace.npz"
    try:
        with zipfile.ZipFile(path) as archive:
            names = [info.filename for info in archive.infolist()]
            if len(names) != len(set(names)):
                raise _fail("trace.npz contains duplicate array entries")
            if any(
                info.is_dir()
                or not info.filename.endswith(".npy")
                or "/" in info.filename
                or "\\" in info.filename
                or stat.S_ISLNK(info.external_attr >> 16)
                for info in archive.infolist()
            ):
                raise _fail("trace.npz contains an unsafe array entry")
        with np.load(path, allow_pickle=False) as arrays:
            for name in arrays.files:
                value = arrays[name]
                if value.dtype.hasobject:
                    raise _fail(f"trace.npz array {name!r} has unsafe object dtype")
    except ArtifactVerificationError:
        raise
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise _fail(f"trace.npz is malformed or unsafe: {error}") from error


def _validate_events(run_dir: Path) -> None:
    path = run_dir / "events.jsonl"
    try:
        content = path.read_bytes()
    except OSError as error:
        raise _fail(f"could not read events.jsonl: {error}") from error
    if content and not content.endswith(b"\n"):
        raise _fail("events.jsonl must end with a newline")
    lines = content.split(b"\n")[:-1] if content else []
    for expected_sequence, line in enumerate(lines):
        if not line:
            raise _fail("events.jsonl contains a blank line")
        event = _require_mapping(
            _load_json_bytes(line, filename="events.jsonl"), location="events.jsonl event"
        )
        sequence = event.get("sequence")
        if (
            isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or sequence != expected_sequence
        ):
            raise _fail(
                "events.jsonl sequences must be contiguous integers starting at zero"
            )


def _validate_payload_structure(run_dir: Path, manifest: Mapping[str, Any]) -> None:
    config = _validate_config(run_dir, manifest)
    if manifest["artifact_schema"] == ARTIFACT_SCHEMA:
        identity = _require_mapping(manifest["identity"], location="manifest.json.identity")
        try:
            parameters_match = canonical_json_bytes(config["parameters"]) == canonical_json_bytes(
                identity["parameters"]
            )
        except (TypeError, ValueError) as error:
            raise _fail(
                f"config.json.parameters is not canonical identity data: {error}"
            ) from error
        if not parameters_match:
            raise _fail("config.json.parameters does not match manifest.json.identity")
    _validate_metrics_and_summary(run_dir)
    _validate_trace(run_dir)
    _validate_events(run_dir)


def _validate_directory(run_dir: Path) -> None:
    try:
        if run_dir.is_symlink():
            raise _fail("artifact directory must not be a symbolic link")
        if not run_dir.is_dir():
            raise _fail("artifact path must be an existing directory")
        entries = tuple(run_dir.iterdir())
    except OSError as error:
        raise _fail(f"could not inspect artifact directory: {error}") from error
    names = frozenset(path.name for path in entries)
    if names != EXPECTED_FILENAMES:
        missing = sorted(EXPECTED_FILENAMES - names)
        extra = sorted(names - EXPECTED_FILENAMES)
        raise _fail(f"artifact files differ: missing={missing}, extra={extra}")
    for path in entries:
        try:
            mode = path.lstat().st_mode
        except OSError as error:
            raise _fail(f"could not inspect artifact file {path.name}: {error}") from error
        if not stat.S_ISREG(mode):
            raise _fail(f"artifact file {path.name} must be a regular file, not a link")


def _immutable_payloads(
    payloads: Mapping[str, Mapping[str, int | str]],
) -> Mapping[str, Mapping[str, int | str]]:
    return MappingProxyType(
        {
            name: MappingProxyType(dict(checksum))
            for name, checksum in sorted(payloads.items())
        }
    )


def _verify_v1(run_dir: Path, manifest: Mapping[str, Any]) -> VerificationReport:
    _require_exact_keys(manifest, _LEGACY_MANIFEST_FIELDS, location="manifest.json")
    _validate_common_manifest(manifest)
    _validate_payload_structure(run_dir, manifest)
    return VerificationReport(
        run_dir=run_dir,
        artifact_schema=LEGACY_ARTIFACT_SCHEMA,
        run_hash=str(manifest["run_hash"]),
        identity_sha256=None,
        integrity_level="legacy-unsealed",
        payloads=MappingProxyType({}),
        bundle_sha256=None,
    )


def _verify_v2(run_dir: Path, manifest: Mapping[str, Any]) -> VerificationReport:
    _require_exact_keys(manifest, _V2_MANIFEST_FIELDS, location="manifest.json")
    _validate_common_manifest(manifest)
    if manifest["integrity_level"] != "checksummed":
        raise _fail("manifest.json.integrity_level must be 'checksummed'")

    identity = _require_mapping(manifest["identity"], location="manifest.json.identity")
    _require_exact_keys(identity, _IDENTITY_FIELDS, location="manifest.json.identity")
    try:
        canonical = canonical_identity(identity)
    except (TypeError, ValueError) as error:
        raise _fail(f"manifest.json.identity is not canonical: {error}") from error
    if canonical_json_bytes(canonical) != canonical_json_bytes(identity):
        raise _fail("manifest.json.identity is not in canonical form")
    if canonical["artifact_schema"] != ARTIFACT_SCHEMA:
        raise _fail("manifest.json.identity has the wrong artifact schema")
    for field in (
        "artifact_schema",
        "experiment",
        "package_version",
        "preset",
        "runtime_environment",
        "scenario",
        "seed",
        "source_fingerprint",
    ):
        if canonical[field] != manifest[field]:
            raise _fail(f"manifest.json.identity.{field} does not match top-level metadata")

    declared_identity_sha = _require_hex(
        manifest["identity_sha256"], length=64, location="manifest.json.identity_sha256"
    )
    actual_identity_sha = identity_sha256(canonical)
    if declared_identity_sha != actual_identity_sha:
        raise _fail("manifest.json.identity_sha256 does not match the canonical identity")
    declared_run_hash = _require_hex(
        manifest["run_hash"], length=20, location="manifest.json.run_hash"
    )
    if declared_run_hash != declared_identity_sha[:20]:
        raise _fail("manifest.json.run_hash is not the identity digest prefix")

    raw_payloads = _require_mapping(manifest["payloads"], location="manifest.json.payloads")
    if frozenset(raw_payloads) != frozenset(PAYLOAD_FILENAMES):
        raise _fail("manifest.json.payloads must name exactly the five non-manifest payloads")
    payloads: dict[str, Mapping[str, int | str]] = {}
    for name in PAYLOAD_FILENAMES:
        raw_checksum = _require_mapping(
            raw_payloads[name], location=f"manifest.json.payloads.{name}"
        )
        _require_exact_keys(
            raw_checksum, frozenset({"sha256", "size"}), location=f"payload {name}"
        )
        declared_size = _require_int(
            raw_checksum["size"], location=f"manifest.json.payloads.{name}.size"
        )
        if declared_size < 0:
            raise _fail(f"manifest.json.payloads.{name}.size must be non-negative")
        declared_sha = _require_hex(
            raw_checksum["sha256"],
            length=64,
            location=f"manifest.json.payloads.{name}.sha256",
        )
        try:
            content = (run_dir / name).read_bytes()
        except OSError as error:
            raise _fail(f"could not read payload {name}: {error}") from error
        if len(content) != declared_size:
            raise _fail(f"payload {name} size does not match manifest.json")
        if hashlib.sha256(content).hexdigest() != declared_sha:
            raise _fail(f"payload {name} SHA-256 does not match manifest.json")
        payloads[name] = {"sha256": declared_sha, "size": declared_size}

    declared_bundle_sha = _require_hex(
        manifest["bundle_sha256"], length=64, location="manifest.json.bundle_sha256"
    )
    actual_bundle_sha = hashlib.sha256(
        canonical_json_bytes(
            {"identity_sha256": declared_identity_sha, "payloads": payloads}
        )
    ).hexdigest()
    if declared_bundle_sha != actual_bundle_sha:
        raise _fail("manifest.json.bundle_sha256 does not match identity and payloads")

    _validate_payload_structure(run_dir, manifest)
    return VerificationReport(
        run_dir=run_dir,
        artifact_schema=ARTIFACT_SCHEMA,
        run_hash=declared_run_hash,
        identity_sha256=declared_identity_sha,
        integrity_level="checksummed",
        payloads=_immutable_payloads(payloads),
        bundle_sha256=declared_bundle_sha,
    )


def verify_run(run_dir: str | Path) -> VerificationReport:
    """Verify a v2 sealed run, or strictly inspect an unmodified v1 run."""

    path = Path(run_dir)
    _validate_directory(path)
    manifest = _require_mapping(
        _load_json_file(path / "manifest.json"), location="manifest.json"
    )
    schema = manifest.get("artifact_schema")
    if schema == ARTIFACT_SCHEMA:
        return _verify_v2(path, manifest)
    if schema == LEGACY_ARTIFACT_SCHEMA:
        return _verify_v1(path, manifest)
    raise _fail(f"manifest.json declares unsupported artifact schema {schema!r}")
