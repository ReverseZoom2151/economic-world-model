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
    CapabilityEvidence,
    EvidenceKind,
    LevelRequirement,
    ValidatedCapabilityEvidence,
    assess_validated_capability,
)
from ewm.core.evidence import EvidenceStatus, ValidatedEvidenceArtifact
from ewm.experiments.source_verification import (
    SourceVerification,
    verification_failed,
    verify_sources,
)
from ewm.scenarios.fx.validation import (
    DEFAULT_HAN_L1_L2_PROTOCOL,
    HanValidationReport,
    han_l1_l2_artifacts,
    load_han_l1_l2_protocol,
    run_han_l1_l2_validation,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "ewm.conformance.v1"
PAPER_REGISTRY = ROOT / "references" / "papers.toml"
CAPABILITY_EVIDENCE_PATHS = (
    "tests/properties/test_fx_accounting.py",
    "tests/scenarios/test_fx.py",
)


def _source_fingerprint(root: Path = ROOT) -> str:
    digest = hashlib.sha256()
    paths: set[Path] = set()
    for pattern in (
        "src/ewm/**/*.py",
        "src/ewm/**/*.toml",
        "references/*.toml",
        "protocols/**/*",
        "tests/conformance/**/*.py",
        "tests/integration/test_han_runtime_protocol.py",
        *CAPABILITY_EVIDENCE_PATHS,
        "scripts/run_conformance.py",
    ):
        paths.update(path for path in root.glob(pattern) if path.is_file())
    for path in sorted(paths):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def validated_han_l1_l2_evidence(
    report: HanValidationReport,
    *,
    protocol_path: Path = DEFAULT_HAN_L1_L2_PROTOCOL,
) -> tuple[ValidatedCapabilityEvidence, ...]:
    """Bind each observed FX requirement result to its own validation artifact."""

    artifacts = {
        artifact.subject: artifact
        for artifact in han_l1_l2_artifacts(report, protocol_path=protocol_path)
    }
    if len(artifacts) != len(report.requirements):
        raise ValueError("Han validation artifact subjects must be unique")
    return tuple(
        ValidatedCapabilityEvidence(
            assertion=CapabilityEvidence(
                requirement=LevelRequirement(requirement.requirement),
                passed=requirement.passed,
                kind=EvidenceKind(requirement.evidence_kind),
                provenance=artifacts[f"capability:{requirement.requirement}"].provenance,
                observations=requirement.observations,
            ),
            artifact=artifacts[f"capability:{requirement.requirement}"],
        )
        for requirement in report.requirements
    )


def _artifact_record(artifact: ValidatedEvidenceArtifact) -> dict[str, Any]:
    return {
        "observations": artifact.observations,
        "payload_sha256": artifact.payload_sha256,
        "provenance": artifact.provenance,
        "status": artifact.status.value,
        "subject": artifact.subject,
    }


def _han_validation_outcome(
    test_outcome: dict[str, Any],
) -> tuple[dict[str, Any], tuple[ValidatedCapabilityEvidence, ...]]:
    protocol = load_han_l1_l2_protocol()
    if test_outcome["status"] != EvidenceStatus.PASS.value:
        return (
            {
                "artifacts": [],
                "arms": list(protocol.arms),
                "classification": protocol.classification,
                "excluded_claims": list(protocol.excluded_claims),
                "protocol_filename": protocol.protocol_filename,
                "protocol_schema": protocol.schema_version,
                "protocol_sha256": protocol.protocol_sha256,
                "protocol_version": protocol.protocol_version,
                "report_schema": protocol.report_schema,
                "source_sha256": protocol.source_sha256,
                "status": EvidenceStatus.NOT_RUN.value,
                "test_gate_status": test_outcome["status"],
            },
            (),
        )

    validation_report = run_han_l1_l2_validation()
    evidence = validated_han_l1_l2_evidence(validation_report)
    artifacts = tuple(item.artifact for item in evidence)
    payload = validation_report.as_dict()
    payload.update(
        {
            "artifacts": [_artifact_record(artifact) for artifact in artifacts],
            "status": (
                EvidenceStatus.PASS.value
                if all(item.status is EvidenceStatus.PASS for item in artifacts)
                else EvidenceStatus.FAIL.value
            ),
            "test_gate_status": test_outcome["status"],
        }
    )
    return payload, evidence


def _ddge_assessments(test_outcome: dict[str, Any]) -> dict[str, dict[str, Any]]:
    suite_status = str(test_outcome["status"])
    scalar_status = {
        EvidenceStatus.PASS.value: "supported",
        EvidenceStatus.FAIL.value: "failed",
        EvidenceStatus.NOT_RUN.value: "not_assessed",
    }[suite_status]
    scalar_evidence = (
        ["tests/conformance/test_cong_conformance.py"]
        if suite_status == EvidenceStatus.PASS.value
        else []
    )
    return {
        "cong-lab-i": {
            "claim": "qualitative-reconstruction",
            "evidence": [],
            "qualification": "not exercised by the conformance suite",
            "scenario": "credit",
            "status": "not_assessed",
        },
        "cong-lab-ii": {
            "claim": "exact-replication",
            "evidence": scalar_evidence,
            "qualification": "internal scalar DDGE conformance",
            "scenario": "scalar",
            "status": scalar_status,
        },
        "cong-lab-iii-population": {
            "claim": "exact-replication",
            "evidence": [],
            "qualification": "external code-independent numerical oracle pending",
            "scenario": "forecasting",
            "status": "not_assessed",
        },
    }


def _paper_hashes() -> dict[str, str]:
    with PAPER_REGISTRY.open("rb") as handle:
        registry = tomllib.load(handle)
    return {str(source["id"]): str(source["sha256"]) for source in registry["source"]}


def _test_outcome(*, skip_tests: bool) -> dict[str, Any]:
    test_paths = ("tests/conformance", *CAPABILITY_EVIDENCE_PATHS)
    command = [sys.executable, "-m", "pytest", *test_paths, "-q"]
    displayed_command = f"python -m pytest {' '.join(test_paths)} -q"
    if skip_tests:
        return {
            "command": displayed_command,
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
        "command": displayed_command,
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

    test_outcome = _test_outcome(skip_tests=skip_tests)
    han_validation, capability_evidence = _han_validation_outcome(test_outcome)
    assessment = assess_validated_capability(capability_evidence)
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
        "han_l1_l2_validation": han_validation,
        "ddge_assessments": _ddge_assessments(test_outcome),
        "stochastic_seed_sets": {
            "credit_smoke": [42],
            "forecasting_smoke": [42],
            "fx_comparative_statics_smoke": list(range(1_000, 1_008)),
            "fx_rollout_smoke": list(load_han_l1_l2_protocol().seeds),
        },
        "capability_assessment": {
            "achieved_level": assessment.achieved_level.name,
            "satisfied_requirements": [item.value for item in assessment.satisfied_requirements],
            "missing_requirements": [item.value for item in assessment.missing_requirements],
            "warnings": list(assessment.warnings),
            "evidence_basis": "validated_conformance_artifacts",
            "validation_status": han_validation["status"],
            "empirical_validity": assessment.empirical_validity.status.value,
            "blocked_levels": {
                "L3": "missing controlled language-model behavioral evidence",
                "L4": "missing persistent capability-improvement evidence",
                "L5": "missing endogenous institutional-outcome evidence",
                "L6": "missing external repeated out-of-sample evidence",
            },
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
    failed_han_validation = report["han_l1_l2_validation"]["status"] == "fail"
    failed_sources = verification_failed(
        source_results,
        require_sources=args.require_sources,
    )
    return 1 if failed_tests or failed_han_validation or failed_sources else 0


if __name__ == "__main__":
    raise SystemExit(main())
