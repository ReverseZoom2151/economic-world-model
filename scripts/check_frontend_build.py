#!/usr/bin/env python3
"""Require a locked, deterministic workbench build matching packaged static assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any, cast

NODE_ENGINE = ">=22 <23"
REQUIRED_STATIC_FILES = frozenset({"index.html", "manifest.json"})


def _hashes(directory: Path) -> dict[str, str]:
    return {
        path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{location} must contain a JSON object")
    return cast(Mapping[str, Any], value)


def _load_json(path: Path) -> Mapping[str, Any]:
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")), str(path))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"could not load {path}: {error}") from error


def _asset_paths(manifest: Mapping[str, Any]) -> frozenset[str]:
    paths: set[str] = set()
    for key, raw_entry in manifest.items():
        entry = _mapping(raw_entry, f"manifest entry {key!r}")
        for field in ("file", "css", "assets"):
            raw_paths = entry.get(field, ())
            values = (raw_paths,) if isinstance(raw_paths, str) else raw_paths
            if not isinstance(values, list | tuple):
                raise RuntimeError(f"manifest entry {key!r}.{field} must contain asset paths")
            for value in values:
                if not isinstance(value, str) or not value:
                    raise RuntimeError(f"manifest entry {key!r}.{field} has an invalid path")
                path = PurePosixPath(value)
                if path.is_absolute() or ".." in path.parts or "://" in value:
                    raise RuntimeError(f"manifest asset path is not local and relative: {value!r}")
                paths.add(path.as_posix())
    return frozenset(paths)


def _validate_tree(directory: Path) -> dict[str, str]:
    hashes = _hashes(directory)
    missing = sorted(REQUIRED_STATIC_FILES - hashes.keys())
    if missing:
        raise RuntimeError(f"workbench build is missing required files: {missing}")
    manifest = _load_json(directory / "manifest.json")
    if "index.html" not in manifest:
        raise RuntimeError("workbench manifest must contain the index.html entry")
    assets = _asset_paths(manifest)
    missing_assets = sorted(assets - hashes.keys())
    if missing_assets:
        raise RuntimeError(f"workbench manifest references missing assets: {missing_assets}")
    return hashes


def _build(workbench: Path, output: Path) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "CI": "true",
            "LC_ALL": "C",
            "NODE_ENV": "production",
            "SOURCE_DATE_EPOCH": "946684800",
            "TZ": "UTC",
        }
    )
    subprocess.run(
        [
            "npm",
            "run",
            "build",
            "--",
            "--outDir",
            str(output),
            "--emptyOutDir",
        ],
        cwd=workbench,
        env=environment,
        check=True,
    )


def validate_frontend_build(project_root: Path) -> None:
    """Build twice and require both results to match packaged static bytes."""

    workbench = project_root / "workbench"
    package_path = workbench / "package.json"
    lock_path = workbench / "package-lock.json"
    static = project_root / "src" / "ewm" / "workbench" / "static"
    if not package_path.is_file():
        raise RuntimeError("workbench/package.json is required")
    if not lock_path.is_file():
        raise RuntimeError("workbench/package-lock.json is required")
    package = _load_json(package_path)
    engines = _mapping(package.get("engines"), "workbench/package.json.engines")
    if engines.get("node") != NODE_ENGINE:
        raise RuntimeError(f"workbench must pin the Node engine to {NODE_ENGINE!r}")
    if shutil.which("npm") is None:
        raise RuntimeError("npm is required to verify the workbench build")
    if not (workbench / "node_modules").is_dir():
        raise RuntimeError("workbench dependencies are absent; run 'npm ci' first")
    committed_hashes = _validate_tree(static)

    with tempfile.TemporaryDirectory(prefix="ewm-frontend-build-") as temporary:
        base = Path(temporary)
        first = base / "first"
        second = base / "second"
        _build(workbench, first)
        _build(workbench, second)
        first_hashes = _validate_tree(first)
        second_hashes = _validate_tree(second)

    if first_hashes != second_hashes:
        raise RuntimeError(
            "workbench builds are not reproducible: "
            f"first={first_hashes}, second={second_hashes}"
        )
    if committed_hashes != first_hashes:
        raise RuntimeError(
            "packaged workbench assets are stale: "
            f"committed={committed_hashes}, rebuilt={first_hashes}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    validate_frontend_build(arguments.project_root.resolve())
    print("validated reproducible workbench assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
