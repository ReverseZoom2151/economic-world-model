"""Integration contracts for conformance source verification."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_conformance import build_report, main


def test_conformance_report_retains_hashes_and_adds_observed_source_status(
    tmp_path: Path,
) -> None:
    report = build_report(skip_tests=True, source_dir=tmp_path)

    assert report["paper_sources"] == {
        "cong-2026": "c5ed935e09b5b0a607f0523d6be293ba4de1707bc242083ad1cd5a5937820357",
        "han-et-al-2026": "918e51bc34b102a4d51c5a55528cdd90ca78576df2bc1955dee31e65c051c8e6",
    }
    assert set(report["source_verification"]) == {
        "cong-2026",
        "han-et-al-2026",
    }
    assert {observation["status"] for observation in report["source_verification"].values()} == {
        "not_present"
    }


def test_conformance_cli_does_not_treat_missing_sources_as_verified(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["--skip-tests", "--source-dir", str(tmp_path)])

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert exit_code == 0
    assert all(
        observation["status"] == "not_present"
        for observation in report["source_verification"].values()
    )


def test_conformance_cli_require_sources_fails_when_sources_are_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "--skip-tests",
            "--source-dir",
            str(tmp_path),
            "--require-sources",
        ]
    )

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert exit_code == 1
    assert all(
        observation["status"] == "not_present"
        for observation in report["source_verification"].values()
    )
