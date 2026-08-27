from __future__ import annotations

import json
import subprocess
import sys


def test_quick_scientific_stress_protocol_passes() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/scientific_stress.py", "--quick"],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)

    assert all(report["checks"].values())
    assert report["credit"]["replications"] == 3
    assert report["fx"]["comparison_replications"] == 8
    assert report["forecasting"]["case_count"] == 4
