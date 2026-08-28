"""Shared canonical JSON identity primitives for package layers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from math import isfinite
from typing import Any

import numpy as np

_TYPE = "__ewm_type__"


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("canonical serialization requires finite floats")
        return value
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return _json_value(float(value))
    if isinstance(value, np.ndarray):
        return {
            _TYPE: "ndarray",
            "data": _json_value(value.tolist()),
            "dtype": str(value.dtype),
            "shape": list(value.shape),
        }
    if isinstance(value, Mapping):
        return {
            str(key): _json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, tuple | list):
        return [_json_value(item) for item in value]
    if isinstance(value, set | frozenset):
        encoded = [_json_value(item) for item in value]
        return sorted(encoded, key=canonical_json)
    raise TypeError(f"value of type {type(value).__name__!r} is not canonically serializable")


def canonical_json(value: Any) -> str:
    """Return a stable JSON representation for immutable package values."""

    return json.dumps(
        _json_value(value),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def content_digest(value: Any) -> str:
    """Return a full SHA-256 digest of a canonically serialized value."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
