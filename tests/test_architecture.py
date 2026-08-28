from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

SRC = Path(__file__).parents[1] / "src"
PACKAGE = SRC / "ewm"

LAYER_IMPORTS = {
    "_internal": ("ewm._internal",),
    "core": ("ewm._internal", "ewm.core"),
    "capabilities": ("ewm._internal", "ewm.capabilities", "ewm.core"),
    "equilibrium": ("ewm._internal", "ewm.core", "ewm.equilibrium"),
    "scenarios": ("ewm._internal", "ewm.core", "ewm.scenarios"),
    "experiments": (
        "ewm._internal",
        "ewm._version",
        "ewm.core",
        "ewm.equilibrium",
        "ewm.experiments",
        "ewm.scenarios",
    ),
    "ontology": (
        "ewm._internal",
        "ewm._version",
        "ewm.core",
        "ewm.equilibrium",
        "ewm.experiments",
        "ewm.ontology",
        "ewm.scenarios",
    ),
    "workbench": (
        "ewm._internal",
        "ewm._version",
        "ewm.ontology",
        "ewm.workbench",
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


def test_declared_architecture_layers_exist() -> None:
    missing = sorted(layer for layer in LAYER_IMPORTS if not (PACKAGE / layer).is_dir())

    assert not missing, f"declared architecture layers do not exist: {missing}"


@pytest.mark.parametrize("category", ("unit", "unit/core", "integration"))
def test_large_test_categories_are_subdivided_by_evidence_domain(category: str) -> None:
    loose_tests = {
        path.name for path in (PACKAGE.parents[1] / "tests" / category).glob("test_*.py")
    }
    expected = (
        {
            "test_alignment.py",
            "test_capability_evolution.py",
            "test_cognition.py",
            "test_institutions.py",
        }
        if category == "unit"
        else set()
    )

    assert loose_tests == expected


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


def _module_name(path: Path) -> str:
    relative = path.relative_to(SRC).with_suffix("")
    parts = relative.parts[:-1] if relative.name == "__init__" else relative.parts
    return ".".join(parts)


def test_internal_module_import_graph_is_acyclic() -> None:
    paths = tuple(sorted(PACKAGE.rglob("*.py")))
    modules = {_module_name(path): path for path in paths}
    dependencies: dict[str, set[str]] = {module: set() for module in modules}
    for module, path in modules.items():
        for imported, _line in _imported_modules(path):
            candidates = tuple(
                candidate
                for candidate in modules
                if imported == candidate or imported.startswith(f"{candidate}.")
            )
            if candidates:
                dependencies[module].add(max(candidates, key=len))

    visiting: list[str] = []
    visited: set[str] = set()

    def visit(module: str) -> tuple[str, ...] | None:
        if module in visiting:
            start = visiting.index(module)
            return (*visiting[start:], module)
        if module in visited:
            return None
        visiting.append(module)
        for dependency in sorted(dependencies[module]):
            cycle = visit(dependency)
            if cycle is not None:
                return cycle
        visiting.pop()
        visited.add(module)
        return None

    cycle = next(
        (found for module in sorted(modules) if (found := visit(module)) is not None),
        None,
    )
    assert cycle is None, "internal import cycle: " + " -> ".join(cycle or ())
