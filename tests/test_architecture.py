from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

SRC = Path(__file__).parents[1] / "src"
PACKAGE = SRC / "ewm"

LAYER_IMPORTS = {
    "core": ("ewm.core",),
    "equilibrium": ("ewm.core", "ewm.equilibrium"),
    "scenarios": ("ewm.core", "ewm.scenarios"),
    "experiments": (
        "ewm._version",
        "ewm.core",
        "ewm.equilibrium",
        "ewm.experiments",
        "ewm.scenarios",
    ),
}


def _package_parts(path: Path) -> tuple[str, ...]:
    return path.relative_to(SRC).with_suffix("").parts[:-1]


def _imported_modules(path: Path) -> Iterator[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    package = _package_parts(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, node.lineno
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if node.module is not None:
                    yield node.module, node.lineno
                continue
            parent_count = node.level - 1
            base = package[: len(package) - parent_count]
            if node.module is not None:
                yield ".".join((*base, *node.module.split("."))), node.lineno
            else:
                for alias in node.names:
                    yield ".".join((*base, alias.name)), node.lineno


def _is_allowed(module: str, allowed: tuple[str, ...]) -> bool:
    return not module.startswith("ewm") or any(
        module == prefix or module.startswith(f"{prefix}.") for prefix in allowed
    )


@pytest.mark.parametrize(("layer", "allowed"), LAYER_IMPORTS.items())
def test_layer_imports_only_same_or_lower_layers(
    layer: str, allowed: tuple[str, ...]
) -> None:
    violations = [
        f"{path.relative_to(PACKAGE)}:{line} imports {module}"
        for path in sorted((PACKAGE / layer).rglob("*.py"))
        for module, line in _imported_modules(path)
        if not _is_allowed(module, allowed)
    ]

    assert not violations, "architecture boundary violations:\n" + "\n".join(violations)
