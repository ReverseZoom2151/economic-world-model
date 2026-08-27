"""Verify locally supplied paper PDFs against the locked source registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ewm.experiments.source_verification import verification_failed, verify_sources

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=ROOT / "references" / "papers.toml",
        help="paper registry to verify (default: references/papers.toml)",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=ROOT,
        help="directory containing the untracked source PDFs (default: repository root)",
    )
    parser.add_argument(
        "--require-all",
        action="store_true",
        help="fail when any registered source PDF is absent",
    )
    args = parser.parse_args(argv)

    results = verify_sources(args.registry, source_dir=args.source_dir)
    report = {
        "schema_version": "ewm.source-verification.v1",
        "source_verification": {result.source_id: result.as_dict() for result in results},
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if verification_failed(results, require_sources=args.require_all) else 0


if __name__ == "__main__":
    raise SystemExit(main())
