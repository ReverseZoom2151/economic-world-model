from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import scripts.run_conformance as conformance
from ewm.capabilities import (
    assess_validated_capability,
    documented_prototype_evidence,
)
from ewm.core.evidence import EvidenceStatus, ValidatedEvidenceArtifact
from ewm.experiments import (
    ClaimEvidence,
    ClaimKind,
    UnsupportedClaimError,
    ValidatedClaimEvidence,
    authorize_validated_claims,
)

pytestmark = pytest.mark.conformance


def _test_outcome(status: str) -> dict[str, Any]:
    passed = {"pass": True, "fail": False, "not_run": None}[status]
    return {
        "command": "python -m pytest tests/conformance -q",
        "passed": passed,
        "passed_count": 12 if status == "pass" else None,
        "failed_count": 1 if status == "fail" else None,
        "status": status,
    }


def test_official_claim_authorization_rejects_caller_assertions() -> None:
    assertions = ClaimEvidence(exact_replication_identified=True)

    with pytest.raises(UnsupportedClaimError, match="validated evidence artifact"):
        authorize_validated_claims((ClaimKind.EXACT_REPLICATION,), evidence=assertions)

    artifact = ValidatedEvidenceArtifact.from_observation(
        subject="exact_replication:identified_source_primitives",
        status=EvidenceStatus.PASS,
        provenance="tests/conformance/test_evidence_truthfulness.py",
        payload={"source_primitives_checked": True},
    )
    validated = ValidatedClaimEvidence(assertions=assertions, artifacts=(artifact,))

    assert authorize_validated_claims(
        (ClaimKind.EXACT_REPLICATION,), evidence=validated
    ).authorized == (ClaimKind.EXACT_REPLICATION,)


def test_official_capability_assessment_rejects_caller_assertions() -> None:
    with pytest.raises(TypeError, match="validated capability evidence"):
        assess_validated_capability(documented_prototype_evidence())


@pytest.mark.parametrize(
    ("status", "expected_scalar"),
    [("fail", "failed"), ("not_run", "not_assessed")],
)
def test_failed_or_unrun_conformance_cannot_emit_supported_evidence(
    status: str,
    expected_scalar: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        conformance,
        "_test_outcome",
        lambda *, skip_tests: _test_outcome(status),
    )

    report = conformance.build_report(skip_tests=status == "not_run", source_dir=tmp_path)

    assert report["capability_assessment"]["achieved_level"] == "L0"
    assert report["capability_assessment"]["satisfied_requirements"] == []
    assert "ddge_consistency" not in report["capability_assessment"]
    assert report["ddge_assessments"]["cong-lab-ii"]["status"] == expected_scalar
    assert all(
        item["status"] != "supported"
        for item in report["ddge_assessments"].values()
    )


def test_passing_conformance_supports_only_the_exercised_ddge_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        conformance,
        "_test_outcome",
        lambda *, skip_tests: _test_outcome("pass"),
    )

    report = conformance.build_report(source_dir=tmp_path)

    assert report["capability_assessment"]["achieved_level"] == "L2"
    assert report["ddge_assessments"] == {
        "cong-lab-i": {
            "claim": "qualitative-reconstruction",
            "evidence": [],
            "qualification": "not exercised by the conformance suite",
            "scenario": "credit",
            "status": "not_assessed",
        },
        "cong-lab-ii": {
            "claim": "exact-replication",
            "evidence": ["tests/conformance/test_cong_conformance.py"],
            "qualification": "internal scalar DDGE conformance",
            "scenario": "scalar",
            "status": "supported",
        },
        "cong-lab-iii-population": {
            "claim": "exact-replication",
            "evidence": [],
            "qualification": "external code-independent numerical oracle pending",
            "scenario": "forecasting",
            "status": "not_assessed",
        },
    }


def test_conformance_fingerprint_covers_code_registries_protocols_and_reporter(
    tmp_path: Path,
) -> None:
    tracked = {
        "src/ewm/model.py": "model = 1\n",
        "references/conformance.toml": "schema_version = 1\n",
        "tests/conformance/test_protocol.py": "def test_protocol(): ...\n",
        "scripts/run_conformance.py": "SCHEMA_VERSION = 'one'\n",
    }
    for relative, content in tracked.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    baseline = conformance._source_fingerprint(tmp_path)

    for relative, content in tracked.items():
        path = tmp_path / relative
        path.write_text(f"{content}# changed\n", encoding="utf-8")
        assert conformance._source_fingerprint(tmp_path) != baseline, relative
        path.write_text(content, encoding="utf-8")
