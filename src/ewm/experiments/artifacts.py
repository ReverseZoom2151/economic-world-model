"""Deterministic local artifact serialization for research runs."""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ewm.core import ExperimentResult

from .metrics import jsonable, scalar_metrics

ARTIFACT_SCHEMA = "ewm.run.v1"


def _json_text(value: Any) -> str:
    return json.dumps(jsonable(value), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _json_line(value: Any) -> str:
    return json.dumps(
        jsonable(value), separators=(",", ":"), sort_keys=True, ensure_ascii=False
    )


def write_artifacts(
    *,
    output_root: Path,
    run_hash: str,
    experiment: str,
    scenario: str,
    preset: str,
    seed: int,
    parameters: Mapping[str, Any],
    result: ExperimentResult,
    traces: Mapping[str, NDArray[Any]],
    events: Sequence[Mapping[str, Any]],
    package_version: str,
) -> Path:
    """Write the complete deterministic artifact contract and return its directory."""

    run_dir = output_root / run_hash
    run_dir.mkdir(parents=True, exist_ok=True)
    configuration = {
        "experiment": experiment,
        "parameters": parameters,
        "preset": preset,
        "scenario": scenario,
        "seed": seed,
    }
    manifest = {
        "artifact_schema": ARTIFACT_SCHEMA,
        "experiment": experiment,
        "package_version": package_version,
        "preset": preset,
        "run_hash": run_hash,
        "scenario": scenario,
        "seed": seed,
    }
    metrics = scalar_metrics(result.metrics)
    (run_dir / "manifest.json").write_text(_json_text(manifest), encoding="utf-8")
    (run_dir / "config.json").write_text(_json_text(configuration), encoding="utf-8")
    (run_dir / "metrics.json").write_text(_json_text(metrics), encoding="utf-8")
    with (run_dir / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("metric", "value"))
        writer.writeheader()
        writer.writerows(
            {"metric": name, "value": value} for name, value in metrics.items()
        )
    trace_values: dict[str, Any] = {
        name: np.asarray(value) for name, value in sorted(traces.items())
    }
    np.savez_compressed(run_dir / "trace.npz", **trace_values)
    event_lines = tuple(
        _json_line({"sequence": sequence, **event})
        for sequence, event in enumerate(events)
    )
    (run_dir / "events.jsonl").write_text(
        "\n".join(event_lines) + ("\n" if event_lines else ""),
        encoding="utf-8",
    )
    return run_dir
