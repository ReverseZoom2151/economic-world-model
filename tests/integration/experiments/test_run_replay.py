"""Integration contracts for sealed run replay."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import ewm.experiments.replay as replay_module
import pytest
from ewm.experiments.artifacts import PAYLOAD_FILENAMES

import ewm
from ewm.core import EVENT_GENESIS_HASH, Event, ReplayReport
from ewm.experiments import (
    ArtifactVerificationError,
    RunReplayError,
    verify_and_replay_run,
)


def _bundle_contents(run_dir: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in run_dir.iterdir()}


def _rewrite_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
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
    manifest["bundle_sha256"] = hashlib.sha256(
        json.dumps(
            {
                "identity_sha256": manifest["identity_sha256"],
                "payloads": payloads,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
    ).hexdigest()
    _rewrite_manifest(run_dir, manifest)


def _rewrite_valid_event_chain(
    run_dir: Path,
    mutate_reset: Callable[[dict[str, Any]], None],
) -> None:
    records = tuple(
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    )
    previous_hash = EVENT_GENESIS_HASH
    rebuilt: list[dict[str, Any]] = []
    for record in records:
        payload = dict(record["payload"])
        if record["sequence"] == 0:
            mutate_reset(payload)
        event = Event(
            sequence=record["sequence"],
            kind=record["kind"],
            payload=payload,
            schema_version=record["schema_version"],
            state_version=record["state_version"],
            previous_hash=previous_hash,
        )
        rebuilt.append(
            {
                "event_hash": event.event_hash,
                "kind": event.kind,
                "payload": payload,
                "previous_hash": event.previous_hash,
                "schema_version": event.schema_version,
                "sequence": event.sequence,
                "state_version": event.state_version,
            }
        )
        previous_hash = event.event_hash
    (run_dir / "events.jsonl").write_text(
        "".join(
            json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n"
            for record in rebuilt
        ),
        encoding="utf-8",
    )
    _reseal(run_dir)


def _fx_run(tmp_path: Path, *, seed: int = 42) -> Path:
    return ewm.run_experiment(
        "fx.rollout",
        preset="smoke",
        seed=seed,
        output_root=tmp_path,
    ).run_dir


def test_verified_fx_bundle_replays_deterministically_without_mutation(tmp_path: Path) -> None:
    run_dir = _fx_run(tmp_path)
    before = _bundle_contents(run_dir)

    first = verify_and_replay_run(run_dir)
    second = verify_and_replay_run(run_dir)

    assert isinstance(first, ReplayReport)
    assert first == second
    assert first.matched
    assert first.replayed_event_count == 49
    assert first.replayed_step_count == 24
    assert first.event_chain_hash == json.loads(
        (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()[-1]
    )["event_hash"]
    assert before == _bundle_contents(run_dir)


def test_replay_first_rejects_a_tampered_sealed_payload(tmp_path: Path) -> None:
    run_dir = _fx_run(tmp_path)
    with (run_dir / "events.jsonl").open("ab") as handle:
        handle.write(b"tampered")

    with pytest.raises(ArtifactVerificationError, match=r"events\.jsonl"):
        verify_and_replay_run(run_dir)


@pytest.mark.parametrize("filename", ["manifest.json", "config.json", "events.jsonl"])
def test_replay_owns_the_exact_verified_bytes_before_parsing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
) -> None:
    run_dir = _fx_run(tmp_path)
    verified = replay_module.verify_run

    def verify_then_replace(path: str | Path) -> object:
        report = verified(path)
        artifact = report.run_dir / filename
        content = artifact.read_bytes()
        artifact.write_bytes(bytes([content[0] ^ 1]) + content[1:])
        return report

    monkeypatch.setattr(replay_module, "verify_run", verify_then_replace)

    with pytest.raises(RunReplayError, match="changed content before replay"):
        replay_module.verify_and_replay_run(run_dir)


def test_replay_rechecks_verified_file_size_before_parsing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = _fx_run(tmp_path)
    verified = replay_module.verify_run

    def verify_then_extend(path: str | Path) -> object:
        report = verified(path)
        with (report.run_dir / "events.jsonl").open("ab") as handle:
            handle.write(b"\n")
        return report

    monkeypatch.setattr(replay_module, "verify_run", verify_then_extend)

    with pytest.raises(RunReplayError, match="changed size before replay"):
        replay_module.verify_and_replay_run(run_dir)


def test_replay_rejects_resealed_event_hash_tampering(tmp_path: Path) -> None:
    run_dir = _fx_run(tmp_path)
    records = [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    records[1]["payload"]["parallel_requested"] = True
    (run_dir / "events.jsonl").write_text(
        "".join(
            json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    _reseal(run_dir)

    with pytest.raises(RunReplayError, match=r"event hash|tampered"):
        verify_and_replay_run(run_dir)


def test_replay_rejects_a_resealed_event_with_an_untyped_state_version(
    tmp_path: Path,
) -> None:
    run_dir = _fx_run(tmp_path)
    records = [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    records[0]["state_version"] = True
    previous_hash = EVENT_GENESIS_HASH
    for record in records:
        event = Event(
            sequence=record["sequence"],
            kind=record["kind"],
            payload=record["payload"],
            schema_version=record["schema_version"],
            state_version=record["state_version"],
            previous_hash=previous_hash,
        )
        record["previous_hash"] = event.previous_hash
        record["event_hash"] = event.event_hash
        previous_hash = event.event_hash
    (run_dir / "events.jsonl").write_text(
        "".join(
            json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    _reseal(run_dir)

    with pytest.raises(RunReplayError, match="state_version"):
        verify_and_replay_run(run_dir)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("state_codec", "ewm.fx.state.v999", "state codec"),
        ("runtime_contract_digest", "a" * 64, "runtime contract"),
    ],
)
def test_replay_rejects_resealed_incompatible_runtime_metadata(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    run_dir = _fx_run(tmp_path)
    _rewrite_valid_event_chain(
        run_dir,
        lambda payload: payload.__setitem__(field, value),
    )

    with pytest.raises(RunReplayError, match=message):
        verify_and_replay_run(run_dir)


def test_replay_rejects_identity_config_mismatch_even_when_resealed(tmp_path: Path) -> None:
    run_dir = _fx_run(tmp_path)
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    config["parameters"]["periods"] = 23
    (run_dir / "config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _reseal(run_dir)

    with pytest.raises(ArtifactVerificationError, match="parameters"):
        verify_and_replay_run(run_dir)


def test_replay_rejects_legacy_and_unsupported_experiments_after_verification(
    tmp_path: Path,
) -> None:
    legacy = _fx_run(tmp_path / "legacy")
    manifest = json.loads((legacy / "manifest.json").read_text(encoding="utf-8"))
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
    _rewrite_manifest(legacy, legacy_manifest)
    unsupported = ewm.run_experiment(
        "forecasting.ddge",
        preset="smoke",
        seed=42,
        output_root=tmp_path / "unsupported",
    ).run_dir

    with pytest.raises(RunReplayError, match="sealed v2"):
        verify_and_replay_run(legacy)
    with pytest.raises(RunReplayError, match=r"fx\.rollout"):
        verify_and_replay_run(unsupported)


def test_replay_python_api_is_exposed_only_under_experiments(tmp_path: Path) -> None:
    run_dir = _fx_run(tmp_path)

    from ewm import experiments

    assert experiments.verify_and_replay_run(run_dir).matched
    assert not hasattr(ewm, "verify_and_replay_run")
