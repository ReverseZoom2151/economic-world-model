from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import ewm
from ewm.cli import main


def _fx_run(tmp_path: Path) -> Path:
    return ewm.run_experiment(
        "fx.rollout",
        preset="smoke",
        seed=17,
        output_root=tmp_path,
    ).run_dir


def test_verify_run_command_emits_stable_success_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_dir = _fx_run(tmp_path)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))

    status = main(["verify-run", str(run_dir)])
    output = json.loads(capsys.readouterr().out)

    assert status == 0
    assert output == {
        "artifact_schema": "ewm.run.v2",
        "bundle_sha256": manifest["bundle_sha256"],
        "identity_sha256": manifest["identity_sha256"],
        "integrity_level": "checksummed",
        "manifest_sha256": hashlib.sha256(
            (run_dir / "manifest.json").read_bytes()
        ).hexdigest(),
        "manifest_size": (run_dir / "manifest.json").stat().st_size,
        "ok": True,
        "payloads": manifest["payloads"],
        "run_dir": str(run_dir),
        "run_hash": manifest["run_hash"],
    }


def test_verify_run_command_emits_useful_failure_json_and_nonzero_status(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_dir = _fx_run(tmp_path)
    (run_dir / "metrics.json").write_text("{}\n", encoding="utf-8")

    status = main(["verify-run", str(run_dir)])
    output = json.loads(capsys.readouterr().out)

    assert status == 1
    assert output["ok"] is False
    assert output["operation"] == "verify-run"
    assert output["run_dir"] == str(run_dir)
    assert output["error_type"] == "ArtifactVerificationError"
    assert "metrics.json" in output["error"]


def test_replay_run_command_emits_exact_replay_report_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_dir = _fx_run(tmp_path)

    status = main(["replay-run", str(run_dir)])
    output = json.loads(capsys.readouterr().out)

    assert status == 0
    assert output["matched"] is True
    assert output["replayed_event_count"] == 49
    assert output["replayed_step_count"] == 24
    assert set(output) == {
        "event_chain_hash",
        "final_state_digest",
        "matched",
        "replayed_event_count",
        "replayed_step_count",
    }


def test_replay_run_command_fails_closed_for_unsupported_experiment(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_dir = ewm.run_experiment(
        "forecasting.ddge",
        preset="smoke",
        seed=17,
        output_root=tmp_path,
    ).run_dir

    status = main(["replay-run", str(run_dir)])
    output = json.loads(capsys.readouterr().out)

    assert status == 1
    assert output["ok"] is False
    assert output["operation"] == "replay-run"
    assert output["error_type"] == "RunReplayError"
    assert "fx.rollout" in output["error"]


def test_existing_cli_commands_remain_available(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["list"]) == 0
    assert "fx.rollout" in capsys.readouterr().out
    assert main(["describe", "fx.rollout"]) == 0
    assert "clearing" in capsys.readouterr().out
    assert main(
        [
            "run",
            "fx.rollout",
            "--preset",
            "smoke",
            "--seed",
            "19",
            "--output",
            str(tmp_path),
        ]
    ) == 0
    assert Path(json.loads(capsys.readouterr().out)["run_dir"]).is_dir()
