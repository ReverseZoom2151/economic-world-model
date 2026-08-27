#!/usr/bin/env python3
"""Fail a mutation workflow unless the exact bounded target is fully killed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FAILURE_FIELDS = (
    "survived",
    "no_tests",
    "suspicious",
    "timeout",
    "check_was_interrupted_by_user",
    "segfault",
)


def validate_mutation_stats(path: Path, *, expected_killed: int) -> dict[str, int]:
    """Return validated mutmut CI stats or raise for an incomplete mutation gate."""

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("mutation stats must be a JSON object")
    required_fields = ("killed", *FAILURE_FIELDS)
    stats: dict[str, int] = {}
    for field in required_fields:
        value = raw.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"mutation stat {field!r} must be a nonnegative integer")
        stats[field] = value

    failures = {field: stats[field] for field in FAILURE_FIELDS if stats[field] != 0}
    if failures:
        raise RuntimeError(f"mutation gate has unresolved mutants: {failures}")
    if stats["killed"] != expected_killed:
        raise RuntimeError(
            f"mutation gate expected {expected_killed} killed mutants, "
            f"found {stats['killed']}"
        )
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stats", type=Path)
    parser.add_argument("--expected-killed", type=int, required=True)
    arguments = parser.parse_args()
    stats = validate_mutation_stats(
        arguments.stats,
        expected_killed=arguments.expected_killed,
    )
    print(f"mutation gate passed: {stats['killed']} killed, 0 unresolved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
