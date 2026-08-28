"""Release-schema contract for bounded workbench benchmarks."""

from __future__ import annotations

import json
import subprocess
import sys


def test_small_workbench_benchmark_reports_percentiles_memory_and_targets() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_workbench.py",
            "--tier",
            "small",
            "--repeats",
            "1",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)

    assert report["schema"] == "ewm.workbench-benchmark.v1"
    assert report["tier"] == "small"
    assert report["fixture"]["objects"] > 0
    assert report["release_targets"]["classification"] == (
        "targets-not-current-performance-claims"
    )
    for result in report["measurements"].values():
        assert result["sample_size"] == 1
        assert result["elapsed_seconds"]["p95"] >= 0.0
        assert result["peak_memory_bytes"]["max"] > 0
