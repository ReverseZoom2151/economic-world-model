"""End-to-end portable snapshot CLI contracts."""

from __future__ import annotations

import json
from pathlib import Path

import ewm
from ewm.cli import main


def _run(root: Path) -> Path:
    return ewm.run_experiment(
        "fx.rollout",
        preset="smoke",
        seed=47,
        output_root=root,
    ).run_dir


def test_snapshot_export_and_verify_publish_stable_machine_reports(
    tmp_path: Path,
    capsys,
) -> None:
    run_dir = _run(tmp_path / "runs")
    selection = tmp_path / "selection.json"
    selection.write_text(
        json.dumps(
            {
                "lens": "scene",
                "camera": {
                    "projection": "perspective",
                    "position": [4, 5, 6],
                    "target": [0, 0, 0],
                },
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "investigation.html"

    export_status = main(
        [
            "snapshot",
            "export",
            str(run_dir),
            "--selection",
            str(selection),
            "--output",
            str(output),
        ]
    )
    exported = json.loads(capsys.readouterr().out)
    verify_status = main(["snapshot", "verify", str(output)])
    verified = json.loads(capsys.readouterr().out)

    assert export_status == verify_status == 0
    assert exported["ok"] is True
    assert exported["operation"] == "snapshot.export"
    assert exported["file_sha256"] == verified["file_sha256"]
    assert exported["subset_digest"] == verified["subset_digest"]
    assert output.is_file()
    assert output.with_suffix(".html.sha256").read_text(encoding="ascii").strip() == (
        exported["file_sha256"]
    )
    assert verified["authenticity_verified"] is False
    assert verified["digital_signature_present"] is False


def test_snapshot_verify_fails_closed_for_corruption(
    tmp_path: Path,
    capsys,
) -> None:
    run_dir = _run(tmp_path / "runs")
    selection = tmp_path / "selection.json"
    selection.write_text('{"lens":"world"}', encoding="utf-8")
    output = tmp_path / "investigation.html"
    assert main(
        [
            "snapshot",
            "export",
            str(run_dir),
            "--selection",
            str(selection),
            "--output",
            str(output),
        ]
    ) == 0
    capsys.readouterr()
    output.write_bytes(
        output.read_bytes().replace(
            b"ewm.investigation.v1",
            b"ewm.investigation.v0",
            1,
        )
    )

    status = main(["snapshot", "verify", str(output)])
    failure = json.loads(capsys.readouterr().out)

    assert status == 1
    assert failure["ok"] is False
    assert failure["operation"] == "snapshot.verify"
