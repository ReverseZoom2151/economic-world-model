#!/usr/bin/env python3
"""Validate built wheel and source-distribution contents and metadata."""

from __future__ import annotations

import argparse
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
    "src/ewm/_version.py",
}
REQUIRED_WHEEL_FILES = {
    "ewm/_version.py",
    "ewm/protocols/credit-mechanism-v1.toml",
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
    missing_source = sorted(REQUIRED_SDIST_FILES - relative_members)
    if missing_source:
        raise RuntimeError(f"source distribution is missing required files: {missing_source}")
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
