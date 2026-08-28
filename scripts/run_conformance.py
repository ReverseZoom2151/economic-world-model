"""Run paper-level conformance tests and emit a deterministic evidence summary."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ewm.conformance import report as _report

DEFAULT_SOURCE_DIR = _report.DEFAULT_SOURCE_DIR
ROOT = _report.ROOT
SCHEMA_VERSION = _report.SCHEMA_VERSION
_source_fingerprint = _report._source_fingerprint
_test_outcome = _report._test_outcome
validated_han_l1_l2_evidence = _report.validated_han_l1_l2_evidence


def build_report(
    *,
    skip_tests: bool = False,
    source_dir: Path | None = None,
) -> dict[str, Any]:
    """Build the report through the package implementation."""

    return _report.build_report(
        skip_tests=skip_tests,
        source_dir=source_dir,
        test_runner=_test_outcome,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the package CLI while preserving this historical entry point."""

    return _report.main(argv, test_runner=_test_outcome)


if __name__ == "__main__":
    raise SystemExit(main())
