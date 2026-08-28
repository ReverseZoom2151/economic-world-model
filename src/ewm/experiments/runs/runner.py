"""Run identity, timing, execution, and artifact creation."""

from __future__ import annotations

import hashlib
import platform
from dataclasses import dataclass
from functools import cache
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

from ewm._version import __version__
from ewm.core import ExperimentResult

from ..registry import experiment_spec
from .artifacts import write_artifacts
from .identity import build_run_identity, identity_sha256


@dataclass(frozen=True, slots=True)
class ExperimentRun:
    """In-memory result and location of its deterministic local artifacts."""

    result: ExperimentResult
    run_dir: Path
    run_hash: str
    elapsed_seconds: float


def _run_hash(value: object) -> str:
    return identity_sha256(value)[:20]


@cache
def _source_fingerprint() -> str:
    """Hash the executed EWM Python source tree for alpha provenance."""

    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


@cache
def _runtime_environment() -> dict[str, str]:
    """Return numerical runtime versions that can affect generated artifacts."""

    return {
        "numpy": version("numpy"),
        "pandas": version("pandas"),
        "python": platform.python_version(),
        "scikit-learn": version("scikit-learn"),
        "scipy": version("scipy"),
    }


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
    source_fingerprint = _source_fingerprint()
    runtime_environment = _runtime_environment()
    identity = build_run_identity(
        experiment=spec.name,
        package_version=__version__,
        parameters=payload.parameters,
        preset=preset,
        runtime_environment=runtime_environment,
        scenario=spec.scenario,
        seed=seed,
        source_fingerprint=source_fingerprint,
    )
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
        runtime_environment=runtime_environment,
        source_fingerprint=source_fingerprint,
        identity=identity,
    )
    return ExperimentRun(
        result=payload.result,
        run_dir=run_dir,
        run_hash=run_hash,
        elapsed_seconds=perf_counter() - started,
    )
