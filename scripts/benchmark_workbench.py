#!/usr/bin/env python3
"""Measure bounded ontology projection, query, and snapshot operations."""

from __future__ import annotations

import argparse
import json
import os
import platform
import tempfile
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

import ewm
from ewm.ontology import DEFAULT_PROFILES, compile_run_projection
from ewm.ontology.query import ObjectQuery, OntologyQueryService
from ewm.ontology.snapshots import SnapshotSelection, SnapshotSource, compile_investigation
from ewm.workbench.snapshots import SnapshotAssets, export_snapshot_html

TIERS = {
    "small": {"experiment": "fx.rollout", "preset": "smoke"},
    "medium": {"experiment": "production.rollout", "preset": "smoke"},
    "large": {"experiment": "fx.rollout", "preset": "research"},
}


def _percentiles(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    return {
        "min": float(np.min(array)),
        "p50": float(np.percentile(array, 50)),
        "p95": float(np.percentile(array, 95)),
        "max": float(np.max(array)),
    }


def _measure(operation: Callable[[], Any], repeats: int) -> dict[str, Any]:
    elapsed: list[float] = []
    peaks: list[float] = []
    for _ in range(repeats):
        tracemalloc.start()
        started = time.perf_counter()
        operation()
        elapsed.append(time.perf_counter() - started)
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peaks.append(float(peak))
    return {
        "sample_size": repeats,
        "elapsed_seconds": _percentiles(elapsed),
        "peak_memory_bytes": _percentiles(peaks),
    }


def benchmark(tier: str, repeats: int) -> dict[str, Any]:
    """Return a deterministic-schema report while keeping timings observational."""

    fixture = TIERS[tier]
    with tempfile.TemporaryDirectory(prefix="ewm-workbench-benchmark-") as temporary:
        root = Path(temporary)
        run = ewm.run_experiment(
            fixture["experiment"],
            preset=fixture["preset"],
            seed=73,
            output_root=root / "runs",
        )
        latest = compile_run_projection(run.run_dir, adapters=DEFAULT_PROFILES)
        projection_result = _measure(
            lambda: compile_run_projection(run.run_dir, adapters=DEFAULT_PROFILES),
            repeats,
        )
        service = OntologyQueryService.from_projection(latest.projection)
        query_result = _measure(
            lambda: service.objects(ObjectQuery(), limit=200),
            repeats,
        )
        provenance = latest.provenance
        snapshot = compile_investigation(
            latest.projection,
            SnapshotSource(
                run_id=provenance.source_run_hash,
                source_run_hash=provenance.source_run_hash,
                source_identity_sha256=provenance.source_identity_sha256,
                source_bundle_sha256=provenance.source_bundle_sha256,
                profile_identity=provenance.adapter_identity,
                profile_digest=provenance.adapter_digest,
                integrity_level="checksummed",
            ),
            SnapshotSelection.from_data({"lens": "world"}),
        )
        snapshot_result = _measure(
            lambda: export_snapshot_html(
                snapshot,
                root / "benchmark.html",
                assets=SnapshotAssets(script="void 0;", style="body{}"),
            ),
            repeats,
        )
    return {
        "schema": "ewm.workbench-benchmark.v1",
        "tier": tier,
        "fixture": {
            **fixture,
            "seed": 73,
            "objects": len(latest.projection.objects),
            "relations": len(latest.projection.relations),
            "measurements": len(latest.projection.measurements),
        },
        "environment": {
            "cpu_count": os.cpu_count(),
            "machine": platform.machine(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "measurements": {
            "projection": projection_result,
            "bounded_object_query": query_result,
            "snapshot_export": snapshot_result,
        },
        "release_targets": {
            "classification": "targets-not-current-performance-claims",
            "query_p95_seconds": 1.0,
            "snapshot_export_p95_seconds": 10.0,
            "snapshot_open_interactive_p95_seconds": 3.0,
            "three_dimensional_frame_p95_seconds": 0.05,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=tuple(TIERS), default="small")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.repeats < 1:
        parser.error("--repeats must be positive")
    report = benchmark(arguments.tier, arguments.repeats)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
