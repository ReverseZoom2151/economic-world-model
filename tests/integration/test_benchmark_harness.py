from __future__ import annotations

import json
import subprocess
import sys


def test_benchmark_harness_reports_latency_percentiles() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_experiments.py",
            "--experiments",
            "fx.rollout",
            "--smoke-repeats",
            "2",
            "--research-repeats",
            "0",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)
    result = report["benchmarks"]["fx.rollout.smoke"]

    assert report["schema"] == "ewm.benchmark.v1"
    assert result["sample_size"] == 2
    assert result["elapsed_seconds"]["p50"] > 0.0
    assert result["elapsed_seconds"]["p50"] <= result["elapsed_seconds"]["p99"]
    assert result["peak_rss_kib"]["max"] > 0
