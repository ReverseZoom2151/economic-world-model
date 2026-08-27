"""Canonical, collision-resistant identities for experiment runs."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any, TypeAlias

import numpy as np

ARTIFACT_SCHEMA = "ewm.run.v2"

JsonScalar: TypeAlias = bool | int | float | str | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


def _canonical_value(value: object, *, location: str) -> JsonValue:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise ValueError(f"identity string at {location} contains an invalid surrogate")
        return value
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, int | np.integer):
        return int(value)
    if isinstance(value, float | np.floating):
        converted = float(value)
        if not math.isfinite(converted):
            raise ValueError(f"identity value at {location} must be finite")
        if converted == 0.0 and math.copysign(1.0, converted) < 0.0:
            raise ValueError(f"identity value at {location} is ambiguous negative zero")
        return converted
    if isinstance(value, np.ndarray):
        if value.dtype.hasobject:
            raise ValueError(f"identity array at {location} must not have object dtype")
        return _canonical_value(value.tolist(), location=location)
    if isinstance(value, Mapping):
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    f"identity mapping key at {location} must be a string, got {type(key).__name__}"
                )
            result[key] = _canonical_value(item, location=f"{location}.{key}")
        return dict(sorted(result.items()))
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [
            _canonical_value(item, location=f"{location}[{index}]")
            for index, item in enumerate(value)
        ]
    raise TypeError(
        f"identity value at {location} has unsupported type {type(value).__name__}"
    )


def canonical_identity(value: object) -> dict[str, JsonValue]:
    """Return a strict JSON identity with stable ordering and unambiguous values."""

    converted = _canonical_value(value, location="identity")
    if not isinstance(converted, dict):
        raise TypeError("identity must be a mapping with string keys")
    return converted


def canonical_json_bytes(value: object) -> bytes:
    """Serialize supported JSON data using the run identity canonical form."""

    converted = _canonical_value(value, location="identity")
    return json.dumps(
        converted,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def identity_sha256(identity: object) -> str:
    """Return the full SHA-256 digest of a canonical run identity."""

    canonical = canonical_identity(identity)
    return hashlib.sha256(canonical_json_bytes(canonical)).hexdigest()


def build_run_identity(
    *,
    experiment: str,
    package_version: str,
    parameters: Mapping[str, Any],
    preset: str,
    runtime_environment: Mapping[str, str],
    scenario: str,
    seed: int,
    source_fingerprint: str,
) -> dict[str, JsonValue]:
    """Build the complete v2 identity used for naming and collision checks."""

    return canonical_identity(
        {
            "artifact_schema": ARTIFACT_SCHEMA,
            "experiment": experiment,
            "package_version": package_version,
            "parameters": parameters,
            "preset": preset,
            "runtime_environment": runtime_environment,
            "scenario": scenario,
            "seed": seed,
            "source_fingerprint": source_fingerprint,
        }
    )
