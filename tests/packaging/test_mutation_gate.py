from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_mutation_results import validate_mutation_stats


def _write_stats(path: Path, **overrides: int) -> None:
    stats = {
        "killed": 11,
        "survived": 0,
        "no_tests": 0,
        "suspicious": 0,
        "timeout": 0,
        "check_was_interrupted_by_user": 0,
        "segfault": 0,
        **overrides,
    }
    path.write_text(json.dumps(stats), encoding="utf-8")


def test_mutation_gate_accepts_exact_fully_killed_target(tmp_path: Path) -> None:
    path = tmp_path / "stats.json"
    _write_stats(path)

    stats = validate_mutation_stats(path, expected_killed=11)

    assert stats["killed"] == 11


@pytest.mark.parametrize("field", ("survived", "no_tests", "suspicious", "timeout"))
def test_mutation_gate_fails_closed_on_unresolved_results(
    tmp_path: Path,
    field: str,
) -> None:
    path = tmp_path / "stats.json"
    _write_stats(path, **{field: 1})

    with pytest.raises(RuntimeError, match="unresolved mutants"):
        validate_mutation_stats(path, expected_killed=11)


def test_mutation_gate_rejects_an_unexpected_target_size(tmp_path: Path) -> None:
    path = tmp_path / "stats.json"
    _write_stats(path, killed=10)

    with pytest.raises(RuntimeError, match="expected 11 killed mutants"):
        validate_mutation_stats(path, expected_killed=11)
