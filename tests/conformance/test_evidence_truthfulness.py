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


@pytest.mark.parametrize("status", ["fail", "not_run"])
def test_failed_or_unrun_conformance_cannot_emit_supported_evidence(
    status: str,
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
    assert report["han_l1_l2_validation"]["status"] == "not_run"
    assert report["han_l1_l2_validation"]["artifacts"] == []
    assert report["han_l3_l6_readiness"]["status"] == "not_run"
    assert report["han_l3_l6_readiness"]["artifacts"] == []
    assert report["han_l3_l6_readiness"]["official_awards"] == 0
    assert "ddge_consistency" not in report["capability_assessment"]
    assert all(
        item["status"] == "not_assessed"
        for item in report["ddge_assessments"].values()
    )
    assert all(not item["evidence"] for item in report["ddge_assessments"].values())


def test_passing_conformance_reports_each_exercised_ddge_claim_at_its_boundary(
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
    validation = report["han_l1_l2_validation"]
    assert validation["classification"] == "synthetic_systems_conformance"
    assert validation["excluded_claims"] == [
        "empirical_validation",
        "prospective_behavioral_study",
    ]
    assert len(validation["artifacts"]) == 5
    assert len({item["payload_sha256"] for item in validation["artifacts"]}) == 5
    assert all(item["status"] == "pass" for item in validation["artifacts"])
    readiness = report["han_l3_l6_readiness"]
    assert readiness["classification"] == "evidence_readiness_only"
    assert readiness["status"] == "pass"
    assert len(readiness["results"]) == 16
    assert len(readiness["artifacts"]) == 16
    assert readiness["official_awards"] == 0
    assert all(item["blocked"] for item in readiness["results"])
    assert report["capability_assessment"]["achieved_level"] == "L2"
    assert report["capability_assessment"]["blocked_levels"] == {
        "L3": "missing controlled language-model behavioral evidence",
        "L4": "missing persistent capability-improvement evidence",
        "L5": "missing endogenous institutional-outcome evidence",
        "L6": "missing external repeated out-of-sample evidence",
    }
    assert report["ddge_assessments"] == {
        "cong-lab-i": {
            "claim": "qualitative-reconstruction",
            "evidence": [
                "src/ewm/protocols/credit-mechanism-v1.toml",
                "tests/integration/experiments/test_locked_protocol_smoke.py",
            ],
            "qualification": (
                "prospectively locked quick protocol failed its prespecified "
                "solver-residual threshold; diagnostic only and claim unauthorized"
            ),
            "scenario": "credit",
            "status": "diagnostic_only",
        },
        "cong-lab-ii": {
            "claim": "exact-replication",
            "evidence": [
                "tests/conformance/test_cong_conformance.py",
                "tests/oracles/scalar_oracle.py",
                "tests/integration/papers/test_independent_numerical_oracles.py",
            ],
            "qualification": (
                "exact scalar Laboratory II equations and targets; package-import-free "
                "direct-equation and bracketing oracle"
            ),
            "scenario": "scalar",
            "status": "supported",
        },
        "cong-lab-iii-population": {
            "claim": "exact-replication",
            "evidence": [
                "tests/oracles/forecasting_oracle.py",
                "tests/integration/papers/test_independent_numerical_oracles.py",
            ],
            "qualification": (
                "population stationary-kernel OLS roots only; finite-sample damping "
                "remains package-authored and excluded"
            ),
            "scenario": "forecasting",
            "status": "supported",
        },
    }


def test_conformance_gate_executes_every_reported_evidence_path() -> None:
    outcome = conformance._test_outcome(skip_tests=True)

    assert outcome["status"] == "not_run"
    assert outcome["command"] == (
        "python -m pytest tests/conformance tests/properties/test_fx_accounting.py "
        "tests/scenarios/test_fx.py "
        "tests/integration/papers/test_independent_numerical_oracles.py "
        "tests/integration/experiments/test_locked_protocol_smoke.py -q"
    )


def test_conformance_fingerprint_covers_code_registries_protocols_and_reporter(
    tmp_path: Path,
) -> None:
    tracked = {
        "src/ewm/model.py": "model = 1\n",
        "src/ewm/scenarios/fx/han-l1-l2-validation-v1.toml": (
            'schema_version = "ewm.han-l1-l2.protocol.v1"\n'
        ),
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
