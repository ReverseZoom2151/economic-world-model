"""Atomic deterministic artifact serialization for research runs."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import stat
import tempfile
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ewm.core import ExperimentResult

from .identity import (
    ARTIFACT_SCHEMA,
    JsonValue,
    build_run_identity,
    canonical_identity,
    canonical_json_bytes,
    identity_sha256,
)
from .metrics import jsonable, scalar_metrics
from .verification import (
    PAYLOAD_FILENAMES,
    ArtifactVerificationError,
    VerificationReport,
    verify_run,
)


def _json_text(value: Any) -> str:
    return (
        json.dumps(
            jsonable(value),
            allow_nan=False,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )


def _json_line(value: Any) -> str:
    return json.dumps(
        jsonable(value),
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
    )


def _validate_trace_name(name: object) -> str:
    if (
        not isinstance(name, str)
        or not name
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
        or "\0" in name
    ):
        raise ValueError(f"trace array name {name!r} is unsafe")
    return name


def _write_deterministic_trace(
    path: Path, traces: Mapping[str, NDArray[Any]]
) -> None:
    with zipfile.ZipFile(
        path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for raw_name, raw_value in sorted(traces.items()):
            name = _validate_trace_name(raw_name)
            value = np.asarray(raw_value)
            if value.dtype.hasobject:
                raise ValueError(f"trace array {name!r} must not have object dtype")
            buffer = io.BytesIO()
            np.save(buffer, value, allow_pickle=False)
            member = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            member.compress_type = zipfile.ZIP_DEFLATED
            member.create_system = 3
            member.external_attr = (stat.S_IFREG | 0o600) << 16
            archive.writestr(member, buffer.getvalue(), compresslevel=9)


def _payload_checksums(run_dir: Path) -> dict[str, dict[str, int | str]]:
    result: dict[str, dict[str, int | str]] = {}
    for name in PAYLOAD_FILENAMES:
        content = (run_dir / name).read_bytes()
        result[name] = {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
    return result


def _build_manifest(
    *,
    identity: Mapping[str, JsonValue],
    run_hash: str,
    payloads: Mapping[str, Mapping[str, int | str]],
) -> dict[str, Any]:
    full_digest = identity_sha256(identity)
    bundle_sha256 = hashlib.sha256(
        canonical_json_bytes({"identity_sha256": full_digest, "payloads": payloads})
    ).hexdigest()
    return {
        "artifact_schema": ARTIFACT_SCHEMA,
        "bundle_sha256": bundle_sha256,
        "experiment": identity["experiment"],
        "identity": identity,
        "identity_sha256": full_digest,
        "integrity_level": "checksummed",
        "package_version": identity["package_version"],
        "payloads": payloads,
        "preset": identity["preset"],
        "runtime_environment": identity["runtime_environment"],
        "run_hash": run_hash,
        "scenario": identity["scenario"],
        "seed": identity["seed"],
        "source_fingerprint": identity["source_fingerprint"],
    }


def _write_staged_bundle(
    *,
    stage_dir: Path,
    identity: Mapping[str, JsonValue],
    run_hash: str,
    result: ExperimentResult,
    traces: Mapping[str, NDArray[Any]],
    events: Sequence[Mapping[str, Any]],
) -> VerificationReport:
    configuration = {
        "experiment": identity["experiment"],
        "metadata": result.metadata,
        "parameters": identity["parameters"],
        "preset": identity["preset"],
        "scenario": identity["scenario"],
        "seed": identity["seed"],
    }
    metrics = scalar_metrics(result.metrics)
    (stage_dir / "config.json").write_text(_json_text(configuration), encoding="utf-8")
    (stage_dir / "metrics.json").write_text(_json_text(metrics), encoding="utf-8")
    with (stage_dir / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("metric", "value"))
        writer.writeheader()
        writer.writerows(
            {"metric": name, "value": value} for name, value in metrics.items()
        )
    _write_deterministic_trace(stage_dir / "trace.npz", traces)
    event_lines = tuple(
        _json_line({**event, "sequence": sequence})
        for sequence, event in enumerate(events)
    )
    (stage_dir / "events.jsonl").write_text(
        "\n".join(event_lines) + ("\n" if event_lines else ""),
        encoding="utf-8",
    )

    payloads = _payload_checksums(stage_dir)
    manifest = _build_manifest(identity=identity, run_hash=run_hash, payloads=payloads)
    # The manifest is the publication seal and is deliberately the final file written.
    (stage_dir / "manifest.json").write_text(_json_text(manifest), encoding="utf-8")
    return verify_run(stage_dir)


def _remove_stage(stage_dir: Path) -> None:
    if stage_dir.is_symlink():
        stage_dir.unlink()
    elif stage_dir.exists():
        shutil.rmtree(stage_dir)


def _existing_collision(
    *, target: Path, staged_report: VerificationReport
) -> Path:
    try:
        existing_report = verify_run(target)
    except ArtifactVerificationError as error:
        raise ArtifactVerificationError(
            f"artifact collision at {target}: existing run is invalid: {error}"
        ) from error
    if (
        existing_report.artifact_schema != ARTIFACT_SCHEMA
        or existing_report.identity_sha256 != staged_report.identity_sha256
        or existing_report.bundle_sha256 != staged_report.bundle_sha256
    ):
        raise ArtifactVerificationError(
            f"artifact collision at {target}: existing run has different identity or payloads"
        )
    return target


def _prepare_output_root(output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    mode = output_root.lstat().st_mode
    if output_root.is_symlink() or not stat.S_ISDIR(mode):
        raise ArtifactVerificationError("artifact output root must be a real directory")


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
    runtime_environment: Mapping[str, str],
    source_fingerprint: str,
    identity: Mapping[str, Any] | None = None,
) -> Path:
    """Stage, verify, and atomically publish the complete artifact contract."""

    expected_identity = build_run_identity(
        experiment=experiment,
        package_version=package_version,
        parameters=parameters,
        preset=preset,
        runtime_environment=runtime_environment,
        scenario=scenario,
        seed=seed,
        source_fingerprint=source_fingerprint,
    )
    selected_identity = (
        expected_identity if identity is None else canonical_identity(identity)
    )
    if canonical_json_bytes(selected_identity) != canonical_json_bytes(expected_identity):
        raise ValueError("provided identity does not match the artifact inputs")
    full_digest = identity_sha256(selected_identity)
    if run_hash != full_digest[:20]:
        raise ValueError("run_hash must be the first 20 characters of identity_sha256")

    _prepare_output_root(output_root)
    target = output_root / run_hash
    stage_dir = Path(
        tempfile.mkdtemp(
            prefix=f".{run_hash}.",
            suffix=".staging",
            dir=output_root,
        )
    )
    try:
        staged_report = _write_staged_bundle(
            stage_dir=stage_dir,
            identity=selected_identity,
            run_hash=run_hash,
            result=result,
            traces=traces,
            events=events,
        )
        try:
            os.rename(stage_dir, target)
        except OSError:
            if not target.exists() and not target.is_symlink():
                raise
            return _existing_collision(target=target, staged_report=staged_report)
        return target
    finally:
        _remove_stage(stage_dir)
