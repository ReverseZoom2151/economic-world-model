"""Compatibility wrapper for the installed locked-protocol command."""

from __future__ import annotations

from ewm.experiments.protocol_cli import main

if __name__ == "__main__":
    raise SystemExit(main())
