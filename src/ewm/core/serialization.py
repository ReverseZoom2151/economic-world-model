"""Canonical serialization and state codecs for provenance and replay."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from math import isfinite
from typing import Any, Protocol, cast, runtime_checkable

import numpy as np

from .records import Action, ConstraintViolation, freeze_value

CANONICAL_STATE_CODEC_ID = "ewm.state.canonical.v1"
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
    """Return a stable JSON representation for core immutable values."""

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


@runtime_checkable
class StateCodec(Protocol):
    """Encode runtime state into canonical data and reconstruct it for replay."""

    @property
    def codec_id(self) -> str: ...

    def encode(self, state: Any) -> Any: ...

    def decode(self, payload: Any) -> Any: ...


def _encode_state(value: Any) -> Any:
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("canonical state codec requires finite floats")
        return value
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return _encode_state(float(value))
    if isinstance(value, np.ndarray):
        return {
            _TYPE: "ndarray",
            "data": _encode_state(value.tolist()),
            "dtype": str(value.dtype),
            "shape": tuple(value.shape),
        }
    if isinstance(value, Mapping):
        return {
            _TYPE: "mapping",
            "items": tuple(
                (str(key), _encode_state(item))
                for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            ),
        }
    if isinstance(value, tuple):
        return {_TYPE: "tuple", "items": tuple(_encode_state(item) for item in value)}
    if isinstance(value, list):
        return {_TYPE: "list", "items": tuple(_encode_state(item) for item in value)}
    if isinstance(value, set | frozenset):
        items = tuple(_encode_state(item) for item in value)
        return {
            _TYPE: "frozenset",
            "items": tuple(sorted(items, key=canonical_json)),
        }
    raise TypeError(f"state value of type {type(value).__name__!r} is not supported")


def _decode_state(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    kind = value.get(_TYPE)
    if kind == "mapping":
        return {
            str(key): _decode_state(item)
            for key, item in value["items"]
        }
    if kind == "tuple":
        return tuple(_decode_state(item) for item in value["items"])
    if kind == "list":
        return [_decode_state(item) for item in value["items"]]
    if kind == "frozenset":
        return frozenset(_decode_state(item) for item in value["items"])
    if kind == "ndarray":
        decoded = _decode_state(value["data"])
        array = np.asarray(decoded, dtype=str(value["dtype"]))
        return array.reshape(tuple(int(item) for item in value["shape"]))
    raise ValueError(f"unsupported canonical state record {kind!r}")


class CanonicalStateCodec:
    """Lossless codec for mappings, containers, scalars, and NumPy arrays."""

    @property
    def codec_id(self) -> str:
        return CANONICAL_STATE_CODEC_ID

    def encode(self, state: Any) -> Any:
        return freeze_value(_encode_state(state))

    def decode(self, payload: Any) -> Any:
        return _decode_state(payload)


def state_digest(codec: StateCodec, state: Any) -> str:
    """Return the content identity of a state under its declared codec."""

    return content_digest({"codec_id": codec.codec_id, "state": codec.encode(state)})


def action_to_data(action: Action) -> Mapping[str, Any]:
    """Return complete canonical action provenance."""

    return cast(
        Mapping[str, Any],
        freeze_value(
            {
                "agent_id": action.agent_id,
                "kind": action.kind,
                "values": action.values,
            }
        ),
    )


def action_from_data(data: Mapping[str, Any]) -> Action:
    """Reconstruct a typed action from replay provenance."""

    return Action(
        agent_id=str(data["agent_id"]),
        kind=str(data["kind"]),
        values=data["values"],
    )


def violation_to_data(violation: ConstraintViolation) -> Mapping[str, Any]:
    """Return complete canonical constraint-violation provenance."""

    return cast(
        Mapping[str, Any],
        freeze_value(
            {
                "agent_id": violation.agent_id,
                "constraint": violation.constraint,
                "reason": violation.reason,
            }
        ),
    )
