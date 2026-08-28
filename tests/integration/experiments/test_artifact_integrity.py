"""Integration contracts for sealed artifact integrity."""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pytest
from ewm.experiments.artifacts import PAYLOAD_FILENAMES, write_artifacts
from ewm.experiments.identity import build_run_identity, identity_sha256

import ewm
from ewm.core import ExperimentResult
from ewm.experiments import ArtifactVerificationError, verify_run

EXPECTED_FILENAMES = {*PAYLOAD_FILENAMES, "manifest.json"}


def _sample_identity(*, marker: str = "same") -> dict[str, object]:
    return build_run_identity(
        experiment="example.experiment",
        package_version="0.1.0",
        parameters={"marker": marker, "scale": 2.0},
        preset="smoke",
        runtime_environment={"numpy": "test", "python": "test"},
        scenario="example",
        seed=7,
        source_fingerprint="a" * 64,
    )


def _write_sample(
    output_root: Path,
    *,
    identity: dict[str, object] | None = None,
    traces: dict[str, np.ndarray[object] | np.ndarray[np.float64]] | None = None,
) -> Path:
    selected_identity = _sample_identity() if identity is None else identity
    return write_artifacts(
        output_root=output_root,
        run_hash=identity_sha256(selected_identity)[:20],
        experiment="example.experiment",
        scenario="example",
        preset="smoke",
        seed=7,
        parameters={"marker": selected_identity["parameters"]["marker"], "scale": 2.0},  # type: ignore[index]
        result=ExperimentResult(
            scenario="example",
            experiment="example.experiment",
            metrics={"count": 2, "passed": True, "score": 1.25},
            metadata={"purpose": "artifact-integrity-test"},
        ),
        traces=(
            {"values": np.asarray([1.0, 2.0])}
            if traces is None
            else traces
        ),
        events=({"kind": "created"}, {"kind": "measured", "value": 2}),
        package_version="0.1.0",
        runtime_environment={"numpy": "test", "python": "test"},
        source_fingerprint="a" * 64,
        identity=selected_identity,
    )


def _rewrite_manifest(run_dir: Path, manifest: dict[str, object]) -> None:
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _reseal(run_dir: Path) -> None:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    payloads = {
        name: {
            "sha256": hashlib.sha256((run_dir / name).read_bytes()).hexdigest(),
            "size": (run_dir / name).stat().st_size,
        }
        for name in PAYLOAD_FILENAMES
    }
    manifest["payloads"] = payloads
    bundle = {"identity_sha256": manifest["identity_sha256"], "payloads": payloads}
    manifest["bundle_sha256"] = hashlib.sha256(
        json.dumps(bundle, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    _rewrite_manifest(run_dir, manifest)


def test_v2_manifest_seals_every_non_manifest_payload(tmp_path: Path) -> None:
    run_dir = _write_sample(tmp_path)

    report = verify_run(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))

    assert set(path.name for path in run_dir.iterdir()) == EXPECTED_FILENAMES
    assert manifest["artifact_schema"] == "ewm.run.v2"
    assert manifest["identity"] == _sample_identity()
    assert manifest["identity_sha256"] == identity_sha256(manifest["identity"])
    assert manifest["run_hash"] == manifest["identity_sha256"][:20]
    assert manifest["integrity_level"] == "checksummed"
    assert set(manifest["payloads"]) == set(PAYLOAD_FILENAMES)
    for name, payload in manifest["payloads"].items():
        content = (run_dir / name).read_bytes()
        assert payload == {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
    bundle = {
        "identity_sha256": manifest["identity_sha256"],
        "payloads": manifest["payloads"],
    }
    assert manifest["bundle_sha256"] == hashlib.sha256(
        json.dumps(bundle, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    assert report.run_dir == run_dir
    assert report.integrity_level == "checksummed"
    assert report.run_hash == manifest["run_hash"]


@pytest.mark.parametrize("payload_name", PAYLOAD_FILENAMES)
def test_verifier_rejects_tampered_payload(tmp_path: Path, payload_name: str) -> None:
    run_dir = _write_sample(tmp_path)
    with (run_dir / payload_name).open("ab") as handle:
        handle.write(b"tampered")

    with pytest.raises(ArtifactVerificationError, match=payload_name):
        verify_run(run_dir)


@pytest.mark.parametrize("mutation", ["missing", "extra", "symlink"])
def test_verifier_rejects_non_exact_or_linked_bundle(
    tmp_path: Path, mutation: str
) -> None:
    run_dir = _write_sample(tmp_path)
    if mutation == "missing":
        (run_dir / "summary.csv").unlink()
    elif mutation == "extra":
        (run_dir / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    else:
        (run_dir / "summary.csv").unlink()
        (run_dir / "summary.csv").symlink_to(run_dir / "metrics.json")

    with pytest.raises(ArtifactVerificationError):
        verify_run(run_dir)


@pytest.mark.parametrize(
    "contents",
    [
        b'{"sequence":0,"kind":"ok"}\nnot-json\n',
        b'{"sequence":0,"kind":"ok"}\n{"sequence":2,"kind":"gap"}\n',
        b'{"sequence":0,"kind":"no-final-newline"}',
    ],
)
def test_verifier_rejects_malformed_or_noncontiguous_events(
    tmp_path: Path, contents: bytes
) -> None:
    run_dir = _write_sample(tmp_path)
    (run_dir / "events.jsonl").write_bytes(contents)
    _reseal(run_dir)

    with pytest.raises(ArtifactVerificationError, match=r"events\.jsonl"):
        verify_run(run_dir)


def test_verifier_rejects_object_array_even_when_bundle_is_resealed(tmp_path: Path) -> None:
    run_dir = _write_sample(tmp_path)
    np.savez_compressed(run_dir / "trace.npz", unsafe=np.asarray([object()]))
    _reseal(run_dir)

    with pytest.raises(ArtifactVerificationError, match=r"trace\.npz"):
        verify_run(run_dir)


def test_writer_rejects_object_array_and_cleans_staging_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="object"):
        _write_sample(tmp_path, traces={"unsafe": np.asarray([object()])})

    assert list(tmp_path.iterdir()) == []


def test_identical_concurrent_publications_converge(tmp_path: Path) -> None:
    with ThreadPoolExecutor(max_workers=4) as executor:
        run_dirs = tuple(executor.map(lambda _: _write_sample(tmp_path), range(8)))

    assert len(set(run_dirs)) == 1
    assert verify_run(run_dirs[0]).integrity_level == "checksummed"
    assert set(tmp_path.iterdir()) == {run_dirs[0]}


def test_existing_invalid_collision_is_rejected_without_replacement(tmp_path: Path) -> None:
    run_dir = _write_sample(tmp_path)
    original_config = (run_dir / "config.json").read_bytes()
    (run_dir / "manifest.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ArtifactVerificationError, match="collision"):
        _write_sample(tmp_path)

    assert (run_dir / "config.json").read_bytes() == original_config
    assert (run_dir / "manifest.json").read_text(encoding="utf-8") == "{}\n"
    assert set(tmp_path.iterdir()) == {run_dir}


def test_existing_different_payload_collision_is_rejected(tmp_path: Path) -> None:
    run_dir = _write_sample(tmp_path)
    (run_dir / "metrics.json").write_text(
        json.dumps({"count": 99, "passed": True, "score": 1.25}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "summary.csv").write_text(
        "metric,value\ncount,99\npassed,True\nscore,1.25\n",
        encoding="utf-8",
    )
    _reseal(run_dir)
    assert verify_run(run_dir).integrity_level == "checksummed"

    with pytest.raises(ArtifactVerificationError, match="different"):
        _write_sample(tmp_path)

    assert json.loads((run_dir / "metrics.json").read_text())["count"] == 99
    assert set(tmp_path.iterdir()) == {run_dir}


def test_v1_bundle_is_structurally_verified_without_being_modified(tmp_path: Path) -> None:
    run_dir = _write_sample(tmp_path)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    legacy_manifest = {
        name: manifest[name]
        for name in (
            "artifact_schema",
            "experiment",
            "package_version",
            "preset",
            "runtime_environment",
            "run_hash",
            "scenario",
            "seed",
            "source_fingerprint",
        )
    }
    legacy_manifest["artifact_schema"] = "ewm.run.v1"
    _rewrite_manifest(run_dir, legacy_manifest)
    before = {path.name: path.read_bytes() for path in run_dir.iterdir()}

    report = verify_run(run_dir)

    assert report.artifact_schema == "ewm.run.v1"
    assert report.integrity_level == "legacy-unsealed"
    assert report.identity_sha256 is None
    assert before == {path.name: path.read_bytes() for path in run_dir.iterdir()}


def test_verify_run_is_public_only_from_experiments_namespace(tmp_path: Path) -> None:
    run_dir = _write_sample(tmp_path)

    from ewm import experiments

    assert experiments.verify_run(run_dir).run_dir == run_dir
    assert not hasattr(ewm, "verify_run")
