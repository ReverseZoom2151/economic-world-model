from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_provider_neutral_cognitive_agent_example_runs_offline() -> None:
    completed = subprocess.run(
        [sys.executable, str(Path("examples/cognitive_agent.py"))],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "action=buy_fx" in completed.stdout
    assert "backend=offline-example" in completed.stdout
