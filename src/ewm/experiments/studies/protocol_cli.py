"""Command entry point for locked local scientific protocols."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .protocol_runner import run_locked_protocol
from .protocols import (
    DEFAULT_PROTOCOL_PATH,
    ProtocolMode,
    ProtocolValidationError,
    load_protocol,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Run a shipped or explicitly selected versioned protocol."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL_PATH)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true")
    mode.add_argument("--full", action="store_true")
    args = parser.parse_args(argv)
    selected_mode: ProtocolMode = "quick" if args.quick else "full"
    try:
        protocol = load_protocol(args.protocol)
        report = run_locked_protocol(protocol, mode=selected_mode)
    except (OSError, ProtocolValidationError, RuntimeError, ValueError) as error:
        report = {
            "schema_version": "ewm.local-protocol-report.v1",
            "status": "fail",
            "analysis_valid": False,
            "claim_authorized": False,
            "evidence_status": "diagnostic_only",
            "deviations": (),
            "failures": (
                {
                    "code": "protocol_execution_error",
                    "detail": str(error),
                },
            ),
        }
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
