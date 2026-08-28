"""Integration contracts for ontology projection and verification commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import ewm
from ewm.cli import main


def _fx_run(root: Path) -> Path:
    return ewm.run_experiment(
        "fx.rollout",
        preset="smoke",
        seed=31,
        output_root=root,
    ).run_dir


def test_ontology_project_and_verify_emit_stable_success_envelopes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_dir = _fx_run(tmp_path / "runs")
    output = tmp_path / "derived" / "ontology"

    project_status = main(
        [
            "ontology",
            "project",
            "--run-dir",
            str(run_dir),
            "--output",
            str(output),
        ]
    )
    project = json.loads(capsys.readouterr().out)
    verify_status = main(["ontology", "verify", "--bundle", str(output)])
    verification = json.loads(capsys.readouterr().out)

    assert project_status == 0
    assert project == {
        "adapter_identity": "ewm.fx-ontology-profile.v1",
        "bundle_dir": str(output),
        "bundle_sha256": verification["bundle_sha256"],
        "ok": True,
        "operation": "ontology.project",
        "projection_digest": verification["projection_digest"],
        "source_run_hash": run_dir.name,
    }
    assert verify_status == 0
    assert verification["ok"] is True
    assert verification["operation"] == "ontology.verify"
    assert verification["bundle_dir"] == str(output)
    assert verification["artifact_schema"] == "ewm.ontology.v1"
    assert set(verification["payloads"]) == {"coverage.json", "projection.json"}


def test_ontology_project_verifies_source_before_creating_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_dir = _fx_run(tmp_path / "runs")
    (run_dir / "metrics.json").write_text("{}\n", encoding="utf-8")
    output = tmp_path / "must-not-exist" / "ontology"

    status = main(
        [
            "ontology",
            "project",
            "--run-dir",
            str(run_dir),
            "--output",
            str(output),
        ]
    )
    failure = json.loads(capsys.readouterr().out)

    assert status != 0
    assert failure["ok"] is False
    assert failure["operation"] == "ontology.project"
    assert failure["run_dir"] == str(run_dir)
    assert failure["output"] == str(output)
    assert failure["error_type"] == "ProjectionCompilationError"
    assert not output.exists()
    assert not output.parent.exists()


def test_ontology_verify_fails_closed_without_mutating_bundle(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_dir = _fx_run(tmp_path / "runs")
    output = tmp_path / "ontology"
    assert main(
        [
            "ontology",
            "project",
            "--run-dir",
            str(run_dir),
            "--output",
            str(output),
        ]
    ) == 0
    capsys.readouterr()
    graph = output / "projection.json"
    graph.write_text("{}\n", encoding="utf-8")
    before = {path.name: path.read_bytes() for path in output.iterdir()}

    status = main(["ontology", "verify", "--bundle", str(output)])
    failure = json.loads(capsys.readouterr().out)

    assert status != 0
    assert failure == {
        "bundle_dir": str(output),
        "error": failure["error"],
        "error_type": "ProjectionVerificationError",
        "ok": False,
        "operation": "ontology.verify",
    }
    assert "projection.json" in failure["error"]
    assert before == {path.name: path.read_bytes() for path in output.iterdir()}


def test_ontology_project_requires_an_explicit_output_path(
    tmp_path: Path,
) -> None:
    run_dir = _fx_run(tmp_path / "runs")

    with pytest.raises(SystemExit) as error:
        main(["ontology", "project", "--run-dir", str(run_dir)])

    assert error.value.code == 2
    assert not (tmp_path / "ontology").exists()
