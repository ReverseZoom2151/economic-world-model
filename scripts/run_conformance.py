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
from ewm.experiments.source_verification import (
    SourceVerification,
    verification_failed,
    verify_sources,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "ewm.conformance.v1"
PAPER_REGISTRY = ROOT / "references" / "papers.toml"


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
    with PAPER_REGISTRY.open("rb") as handle:
        registry = tomllib.load(handle)
    return {str(source["id"]): str(source["sha256"]) for source in registry["source"]}


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


def _build_report(
    *,
    skip_tests: bool,
    source_dir: Path,
) -> tuple[dict[str, Any], tuple[SourceVerification, ...]]:
    source_results = verify_sources(PAPER_REGISTRY, source_dir=source_dir)

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
    report = {
        "schema_version": SCHEMA_VERSION,
        "paper_sources": _paper_hashes(),
        "source_verification": {result.source_id: result.as_dict() for result in source_results},
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
            "satisfied_requirements": [item.value for item in assessment.satisfied_requirements],
            "missing_requirements": [item.value for item in assessment.missing_requirements],
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
    return report, source_results


def build_report(
    *,
    skip_tests: bool = False,
    source_dir: Path | None = None,
) -> dict[str, Any]:
    """Build the complete local conformance report without writing external state."""

    report, _ = _build_report(
        skip_tests=skip_tests,
        source_dir=ROOT if source_dir is None else source_dir,
    )
    return report


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
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=ROOT,
        help="directory containing the untracked source PDFs (default: repository root)",
    )
    parser.add_argument(
        "--require-sources",
        action="store_true",
        help="fail when any registered source PDF is absent",
    )
    args = parser.parse_args(argv)
    report, source_results = _build_report(
        skip_tests=args.skip_tests,
        source_dir=args.source_dir,
    )
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    failed_tests = report["test_outcomes"]["passed"] is False
    failed_sources = verification_failed(
        source_results,
        require_sources=args.require_sources,
    )
    return 1 if failed_tests or failed_sources else 0


if __name__ == "__main__":
    raise SystemExit(main())
