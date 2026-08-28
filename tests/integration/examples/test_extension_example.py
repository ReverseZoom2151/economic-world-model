"""Integration coverage for package extension examples."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path


def test_cobweb_extension_runs_through_public_interfaces() -> None:
    example = Path("examples/extensions/cobweb.py")

    completed = subprocess.run(
        [sys.executable, str(example)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "theta=3.000000" in completed.stdout
    assert "price=3.000000" in completed.stdout
    assert "quantity=4.000000" in completed.stdout
    assert "stable=True" in completed.stdout
    assert "demand_intervention theta=4.000000" in completed.stdout


def test_cobweb_extension_does_not_import_private_package_modules() -> None:
    example = Path("examples/extensions/cobweb.py")
    tree = ast.parse(example.read_text())
    package_imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("ewm")
    }

    assert package_imports <= {"ewm", "ewm.core", "ewm.equilibrium"}
