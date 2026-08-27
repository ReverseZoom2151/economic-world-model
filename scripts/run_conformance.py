"""Run paper-level conformance tests and emit a deterministic evidence summary."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
import tomllib
from importlib.metadata import version
from pathlib import Path
from typing import Any

from ewm import __version__
from ewm.capabilities import (
    AxisEvidence,
    EvidenceKind,
    assess_capability,
    documented_prototype_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "ewm.conformance.v1"


def _source_fingerprint() -> str:
    digest = hashlib.sha256()
    package = ROOT / "src" / "ewm"
    for path in sorted(package.rglob("*.py")):
        digest.update(path.relative_to(package).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _paper_hashes() -> dict[str, str]:
    with (ROOT / "references" / "papers.toml").open("rb") as handle:
        registry = tomllib.load(handle)
    return {
        str(source["id"]): str(source["sha256"])
        for source in registry["source"]
    }


def _test_outcome(*, skip_tests: bool) -> dict[str, Any]:
    command = [sys.executable, "-m", "pytest", "tests/conformance", "-q"]
    if skip_tests:
        return {
            "command": "python -m pytest tests/conformance -q",
            "passed": None,
            "passed_count": None,
            "failed_count": None,
            "status": "not_run",
        }
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    combined = f"{completed.stdout}\n{completed.stderr}"
    passed_matches = re.findall(r"(\d+) passed", combined)
    failed_matches = re.findall(r"(\d+) failed", combined)
    return {
        "command": "python -m pytest tests/conformance -q",
        "passed": completed.returncode == 0,
        "passed_count": int(passed_matches[-1]) if passed_matches else 0,
        "failed_count": int(failed_matches[-1]) if failed_matches else 0,
        "status": "pass" if completed.returncode == 0 else "fail",
    }


def build_report(*, skip_tests: bool = False) -> dict[str, Any]:
    """Build the complete local conformance report without writing external state."""

    assessment = assess_capability(
        documented_prototype_evidence(),
        ddge_evidence=(
            AxisEvidence(
                passed=True,
                kind=EvidenceKind.SYNTHETIC_TEST,
                provenance="tests/conformance/test_cong_conformance.py",
            ),
        ),
    )
    test_outcome = _test_outcome(skip_tests=skip_tests)
    return {
        "schema_version": SCHEMA_VERSION,
        "paper_sources": _paper_hashes(),
        "package": {
            "name": "economic-world-model",
            "version": __version__,
            "source_fingerprint": _source_fingerprint(),
        },
        "runtime": {
            "numpy": version("numpy"),
            "pandas": version("pandas"),
            "python": platform.python_version(),
            "scikit-learn": version("scikit-learn"),
            "scipy": version("scipy"),
        },
        "test_outcomes": test_outcome,
        "stochastic_seed_sets": {
            "credit_smoke": [42],
            "forecasting_smoke": [42],
            "fx_comparative_statics_smoke": list(range(1_000, 1_008)),
            "fx_rollout_smoke": [42],
        },
        "capability_assessment": {
            "achieved_level": assessment.achieved_level.name,
            "satisfied_requirements": [
                item.value for item in assessment.satisfied_requirements
            ],
            "missing_requirements": [
                item.value for item in assessment.missing_requirements
            ],
            "warnings": list(assessment.warnings),
            "ddge_consistency": assessment.ddge_consistency.status.value,
            "empirical_validity": assessment.empirical_validity.status.value,
        },
        "unresolved_external_dependencies": [
            "controlled language-model behavioral evaluation",
            "persistent capability-improvement experiment",
            "endogenous institutional-outcome experiment",
            "live external economic-data contract",
            "repeated out-of-sample drift and correction evaluation",
            "empirical calibration and validation",
            "policy evaluation evidence",
            "paper-authored numerical primitives for exact credit replication",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="emit metadata without launching the conformance pytest suite",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="optional JSON output path; stdout is always emitted",
    )
    args = parser.parse_args(argv)
    report = build_report(skip_tests=args.skip_tests)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["test_outcomes"]["passed"] is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
