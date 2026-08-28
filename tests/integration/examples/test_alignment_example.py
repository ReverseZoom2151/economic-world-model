"""Integration coverage for the alignment example."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_offline_alignment_example_runs_without_network_access() -> None:
    completed = subprocess.run(
        [sys.executable, str(Path("examples/offline_alignment.py"))],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "evidence=offline://official-price/2026-08-27" in completed.stdout
    assert "corrections=1 version=1" in completed.stdout
