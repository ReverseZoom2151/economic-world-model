"""Measure isolated experiment latency and peak resident memory."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

import ewm

try:
    import resource
except ImportError:  # pragma: no cover - only exercised on Windows
    resource = None  # type: ignore[assignment]


def _peak_rss_kib() -> float | None:
    if resource is None:
        return None
    value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value / 1024.0 if platform.system() == "Darwin" else value


def _worker(experiment: str, preset: str) -> int:
    with tempfile.TemporaryDirectory(prefix="ewm-benchmark-") as temporary:
        started = time.perf_counter()
        run = ewm.run_experiment(
            experiment,
            preset=preset,
            seed=42,
            output_root=Path(temporary),
        )
        elapsed = time.perf_counter() - started
    print(
        json.dumps(
            {
                "elapsed_seconds": elapsed,
                "peak_rss_kib": _peak_rss_kib(),
                "run_hash": run.run_hash,
            },
            sort_keys=True,
        )
    )
    return 0


def _percentiles(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    return {
        "min": float(np.min(array)),
        "p50": float(np.percentile(array, 50)),
        "p95": float(np.percentile(array, 95)),
        "p99": float(np.percentile(array, 99)),
        "max": float(np.max(array)),
    }


def _measure(experiment: str, preset: str, repeats: int) -> dict[str, Any]:
    measurements: list[dict[str, Any]] = []
    script = str(Path(__file__).resolve())
    for _ in range(repeats):
        completed = subprocess.run(
            [
                sys.executable,
                script,
                "--worker-experiment",
                experiment,
                "--worker-preset",
                preset,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        measurements.append(json.loads(completed.stdout))
    hashes = {measurement["run_hash"] for measurement in measurements}
    if len(hashes) != 1:
        raise RuntimeError("identical benchmark inputs produced different run hashes")
    return {
        "sample_size": repeats,
        "elapsed_seconds": _percentiles(
            [float(measurement["elapsed_seconds"]) for measurement in measurements]
        ),
        "peak_rss_kib": (
            _percentiles(
                [
                    float(measurement["peak_rss_kib"])
                    for measurement in measurements
                    if measurement["peak_rss_kib"] is not None
                ]
            )
            if any(measurement["peak_rss_kib"] is not None for measurement in measurements)
            else None
        ),
        "run_hash": hashes.pop(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--experiments",
        nargs="+",
        choices=ewm.list_experiments(),
        default=list(ewm.list_experiments()),
    )
    parser.add_argument("--smoke-repeats", type=int, default=10)
    parser.add_argument("--research-repeats", type=int, default=3)
    parser.add_argument("--worker-experiment", choices=ewm.list_experiments())
    parser.add_argument("--worker-preset", choices=("smoke", "research"))
    args = parser.parse_args()

    if args.worker_experiment is not None:
        if args.worker_preset is None:
            parser.error("--worker-preset is required for worker mode")
        return _worker(args.worker_experiment, args.worker_preset)
    if args.worker_preset is not None:
        parser.error("--worker-experiment is required for worker mode")
    if args.smoke_repeats < 0 or args.research_repeats < 0:
        parser.error("repeat counts must be non-negative")

    benchmarks: dict[str, Any] = {}
    for experiment in args.experiments:
        for preset, repeats in (
            ("smoke", args.smoke_repeats),
            ("research", args.research_repeats),
        ):
            if repeats:
                benchmarks[f"{experiment}.{preset}"] = _measure(
                    experiment,
                    preset,
                    repeats,
                )

    report = {
        "schema": "ewm.benchmark.v1",
        "environment": {
            "cpu_count": os.cpu_count(),
            "machine": platform.machine(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "benchmarks": benchmarks,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
