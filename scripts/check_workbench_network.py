#!/usr/bin/env python3
"""Fail if the workbench source introduces undeclared remote network access."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REMOTE_URL = re.compile(r"https?://", re.IGNORECASE)
NETWORK_APIS = re.compile(r"\b(XMLHttpRequest|WebSocket|EventSource|sendBeacon)\b")


def validate(project_root: Path) -> None:
    source = project_root / "workbench" / "src"
    violations: list[str] = []
    for path in sorted((*source.rglob("*.ts"), *source.rglob("*.tsx"))):
        text = path.read_text(encoding="utf-8")
        if REMOTE_URL.search(text) or NETWORK_APIS.search(text):
            violations.append(path.relative_to(project_root).as_posix())
        if "globalThis.fetch" in text and path.name != "ApiDataSource.ts":
            violations.append(path.relative_to(project_root).as_posix())
    api_source = (source / "data" / "ApiDataSource.ts").read_text(encoding="utf-8")
    if "`${this.#apiBase}${path}`" not in api_source:
        violations.append("workbench/src/data/ApiDataSource.ts:non-relative-fetch")
    snapshot_source = (source / "data" / "SnapshotDataSource.ts").read_text(
        encoding="utf-8"
    )
    if re.search(r"\bfetch\b", snapshot_source):
        violations.append("workbench/src/data/SnapshotDataSource.ts:network-api")
    if violations:
        raise RuntimeError(f"undeclared workbench network access: {sorted(set(violations))}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    validate(arguments.project_root.resolve())
    print("validated workbench network boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
