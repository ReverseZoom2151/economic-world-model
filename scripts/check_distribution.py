#!/usr/bin/env python3
"""Validate built wheel and source-distribution contents and metadata."""

from __future__ import annotations

import argparse
import json
import re
import tarfile
import zipfile
from email.parser import BytesParser
from email.policy import default
from pathlib import Path

PROJECT_NAME = "economic-world-model"
IMPORT_NAME = "ewm"
REQUIRED_SDIST_FILES = {
    ".github/CODEOWNERS",
    ".github/dependabot.yml",
    "CHANGELOG.md",
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "GOVERNANCE.md",
    "LICENSE",
    "MAINTAINERS.md",
    "SECURITY.md",
    "SUPPORT.md",
    "pyproject.toml",
    "scripts/check_frontend_build.py",
    "src/ewm/_version.py",
    "src/ewm/workbench/static/index.html",
    "src/ewm/workbench/static/manifest.json",
    "workbench/package-lock.json",
    "workbench/package.json",
}
REQUIRED_WHEEL_FILES = {
    "ewm/_version.py",
    "ewm/protocols/credit-mechanism-v1.toml",
    "ewm/workbench/static/index.html",
    "ewm/workbench/static/manifest.json",
}


def _expected_version(project_root: Path) -> str:
    version_file = project_root / "src" / IMPORT_NAME / "_version.py"
    match = re.search(
        r'^__version__\s*=\s*["\'](?P<version>[^"\']+)["\']$',
        version_file.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    if match is None:
        raise RuntimeError(f"cannot read version from {version_file}")
    return match.group("version")


def _single_distribution(dist_dir: Path, pattern: str) -> Path:
    matches = sorted(dist_dir.glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"expected one {pattern} in {dist_dir}, found {matches}")
    return matches[0]


def _wheel_metadata(archive: zipfile.ZipFile) -> bytes:
    metadata_paths = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
    if len(metadata_paths) != 1:
        raise RuntimeError(f"expected one wheel METADATA file, found {metadata_paths}")
    return archive.read(metadata_paths[0])


def _workbench_assets(manifest_bytes: bytes, *, prefix: str) -> set[str]:
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"workbench manifest is invalid: {error}") from error
    if not isinstance(manifest, dict) or "index.html" not in manifest:
        raise RuntimeError("workbench manifest must contain an index.html entry")
    assets: set[str] = set()
    for key, entry in manifest.items():
        if not isinstance(entry, dict):
            raise RuntimeError(f"workbench manifest entry {key!r} must be an object")
        for field in ("file", "css", "assets"):
            value = entry.get(field, ())
            paths = (value,) if isinstance(value, str) else value
            if not isinstance(paths, list | tuple):
                raise RuntimeError(f"workbench manifest entry {key!r}.{field} is invalid")
            for path in paths:
                if (
                    not isinstance(path, str)
                    or not path
                    or path.startswith("/")
                    or ".." in path.split("/")
                    or "://" in path
                ):
                    raise RuntimeError(f"workbench manifest asset path is invalid: {path!r}")
                assets.add(f"{prefix}/{path}")
    return assets


def validate_distributions(dist_dir: Path, project_root: Path) -> tuple[Path, Path]:
    """Validate filenames, package data, source files, and core metadata."""

    expected_version = _expected_version(project_root)
    normalized_name = PROJECT_NAME.replace("-", "_")
    wheel = _single_distribution(dist_dir, f"{normalized_name}-{expected_version}-*.whl")
    source = _single_distribution(dist_dir, f"{normalized_name}-{expected_version}.tar.gz")

    with zipfile.ZipFile(wheel) as archive:
        wheel_names = set(archive.namelist())
        missing_wheel = sorted(REQUIRED_WHEEL_FILES - wheel_names)
        if missing_wheel:
            raise RuntimeError(f"wheel is missing required files: {missing_wheel}")
        wheel_assets = _workbench_assets(
            archive.read("ewm/workbench/static/manifest.json"),
            prefix="ewm/workbench/static",
        )
        missing_assets = sorted(wheel_assets - wheel_names)
        if missing_assets:
            raise RuntimeError(f"wheel is missing workbench assets: {missing_assets}")
        metadata = BytesParser(policy=default).parsebytes(_wheel_metadata(archive))

    if metadata["Name"] != PROJECT_NAME:
        raise RuntimeError(f"unexpected distribution name: {metadata['Name']}")
    if metadata["Version"] != expected_version:
        raise RuntimeError(f"unexpected distribution version: {metadata['Version']}")
    if metadata["Requires-Python"] != ">=3.11":
        raise RuntimeError(f"unexpected Python requirement: {metadata['Requires-Python']}")
    project_urls = set(metadata.get_all("Project-URL", []))
    required_url_labels = {"Changelog", "Documentation", "Repository", "Security"}
    present_url_labels = {entry.split(",", maxsplit=1)[0] for entry in project_urls}
    if not required_url_labels <= present_url_labels:
        missing_url_labels = sorted(required_url_labels - present_url_labels)
        raise RuntimeError(
            f"wheel metadata is missing project URLs: {missing_url_labels}"
        )

    with tarfile.open(source, mode="r:gz") as archive:
        members = archive.getnames()
        roots = {name.split("/", maxsplit=1)[0] for name in members}
        if len(roots) != 1:
            raise RuntimeError(f"source distribution has unexpected roots: {sorted(roots)}")
        root = roots.pop()
        relative_members = {
            name.removeprefix(f"{root}/") for name in members if name != root
        }
        manifest_member = archive.extractfile(
            f"{root}/src/ewm/workbench/static/manifest.json"
        )
        if manifest_member is None:
            raise RuntimeError("source distribution workbench manifest cannot be read")
        source_assets = _workbench_assets(
            manifest_member.read(),
            prefix="src/ewm/workbench/static",
        )
    missing_source = sorted(REQUIRED_SDIST_FILES - relative_members)
    if missing_source:
        raise RuntimeError(f"source distribution is missing required files: {missing_source}")
    missing_source_assets = sorted(source_assets - relative_members)
    if missing_source_assets:
        raise RuntimeError(
            f"source distribution is missing workbench assets: {missing_source_assets}"
        )
    return wheel, source


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist_dir", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    wheel, source = validate_distributions(
        arguments.dist_dir.resolve(),
        arguments.project_root.resolve(),
    )
    print(f"validated {wheel.name}")
    print(f"validated {source.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
