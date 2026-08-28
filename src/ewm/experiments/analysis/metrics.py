"""Conversion and validation of experiment measurements."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np


def jsonable(value: Any) -> Any:
    """Convert package values into deterministic JSON-compatible primitives."""

    if is_dataclass(value) and not isinstance(value, type):
        return jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in sorted(value.items())}
    if isinstance(value, tuple | list):
        return [jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    return value


def scalar_metrics(metrics: Mapping[str, Any]) -> dict[str, float | int | bool]:
    """Require a flat scalar metric mapping suitable for JSON and CSV summaries."""

    result: dict[str, float | int | bool] = {}
    for name, value in sorted(metrics.items()):
        converted = jsonable(value)
        if not isinstance(converted, bool | int | float):
            raise TypeError(f"metric {name!r} is not a scalar")
        if isinstance(converted, float) and not np.isfinite(converted):
            raise ValueError(f"metric {name!r} must be finite")
        result[name] = converted
    return result
