#!/usr/bin/env python3
"""Build twice with Hatchling and require byte-identical distributions."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _hashes(directory: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.iterdir())
        if path.is_file()
    }


def _build(project_root: Path, output: Path, source_date_epoch: str) -> None:
    environment = os.environ.copy()
    environment["SOURCE_DATE_EPOCH"] = source_date_epoch
    subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(output)],
        cwd=project_root,
        env=environment,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--source-date-epoch", default="946684800")
    arguments = parser.parse_args()
    project_root = arguments.project_root.resolve()

    with tempfile.TemporaryDirectory(prefix="ewm-reproducible-build-") as temporary:
        base = Path(temporary)
        first = base / "first"
        second = base / "second"
        first.mkdir()
        second.mkdir()
        _build(project_root, first, arguments.source_date_epoch)
        _build(project_root, second, arguments.source_date_epoch)
        first_hashes = _hashes(first)
        second_hashes = _hashes(second)

    if not first_hashes or first_hashes != second_hashes:
        raise RuntimeError(
            "distribution builds are not reproducible: "
            f"first={first_hashes}, second={second_hashes}"
        )
    for name, digest in sorted(first_hashes.items()):
        print(f"{digest}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
