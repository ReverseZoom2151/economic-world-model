"""Seed ownership, run hashing, timing, execution, and artifact creation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from ewm import __version__
from ewm.core import ExperimentResult

from .artifacts import ARTIFACT_SCHEMA, write_artifacts
from .metrics import jsonable
from .registry import experiment_spec


@dataclass(frozen=True, slots=True)
class ExperimentRun:
    """In-memory result and location of its deterministic local artifacts."""

    result: ExperimentResult
    run_dir: Path
    run_hash: str
    elapsed_seconds: float


def _run_hash(value: object) -> str:
    encoded = json.dumps(
        jsonable(value), separators=(",", ":"), sort_keys=True, ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()[:20]


def run_experiment(
    name: str,
    *,
    preset: str = "smoke",
    seed: int = 42,
    output_root: str | Path = "runs",
) -> ExperimentRun:
    """Execute one registered experiment and write its reproducibility bundle."""

    spec = experiment_spec(name)
    started = perf_counter()
    payload = spec.execute(preset, seed)
    identity = {
        "artifact_schema": ARTIFACT_SCHEMA,
        "experiment": spec.name,
        "package_version": __version__,
        "parameters": payload.parameters,
        "preset": preset,
        "scenario": spec.scenario,
        "seed": seed,
    }
    run_hash = _run_hash(identity)
    run_dir = write_artifacts(
        output_root=Path(output_root),
        run_hash=run_hash,
        experiment=spec.name,
        scenario=spec.scenario,
        preset=preset,
        seed=seed,
        parameters=payload.parameters,
        result=payload.result,
        traces=payload.traces,
        events=payload.events,
        package_version=__version__,
    )
    return ExperimentRun(
        result=payload.result,
        run_dir=run_dir,
        run_hash=run_hash,
        elapsed_seconds=perf_counter() - started,
    )
