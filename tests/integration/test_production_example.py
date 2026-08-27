from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_disclosed_production_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, str(Path("examples/production.py"))],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "converged=True" in completed.stdout
    assert "primitive_source=package-authored" in completed.stdout
    assert "template_source=Cong Appendix D" in completed.stdout
