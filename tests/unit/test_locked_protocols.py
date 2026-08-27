from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from ewm.experiments import protocol_cli
from ewm.experiments.protocol_runner import run_locked_protocol
from ewm.experiments.protocols import (
    DEFAULT_PROTOCOL_PATH,
    ProtocolValidationError,
    audit_protocol_execution,
    load_protocol,
    spawn_seed_manifest,
)

PROTOCOL_PATH = DEFAULT_PROTOCOL_PATH


def test_versioned_protocol_loads_as_immutable_locked_contract() -> None:
    protocol = load_protocol(PROTOCOL_PATH)

    assert protocol.schema_version == "ewm.local-scientific-protocol.v1"
    assert protocol.protocol_id == "credit-mechanism"
    assert protocol.protocol_version == 1
    assert protocol.lock_status == "prospectively locked locally"
    assert protocol.content_sha256 == hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()
    assert protocol.sample_sizes.quick_replications == 4
    assert protocol.sample_sizes.full_replications == 12
    assert protocol.stopping.rule == "fixed_sample"
    assert protocol.stopping.interim_looks == 0
    assert protocol.multiplicity.method == "holm"
    assert "engineering" in protocol.sample_size_rationale
    assert "not a powered empirical design" in protocol.sample_size_rationale
    assert tuple(outcome.name for outcome in protocol.outcomes) == (
        "frozen_profit_difference",
        "selective_profit_difference",
        "full_information_profit_difference",
        "selective_repair_rate",
        "full_information_repair_rate",
    )
    assert tuple(tolerance.name for tolerance in protocol.tolerances) == (
        "solver_residual",
        "comparison_slack",
    )
    assert all(outcome.direction for outcome in protocol.outcomes)
    assert all(outcome.unit for outcome in protocol.outcomes)
    assert all(outcome.null for outcome in protocol.outcomes)
    assert all("synthetic" in outcome.interpretation for outcome in protocol.outcomes)
    with pytest.raises(FrozenInstanceError):
        protocol.sample_sizes.quick_replications = 99  # type: ignore[misc]


def test_seed_manifest_is_exact_seedsequence_spawn_output() -> None:
    protocol = load_protocol(PROTOCOL_PATH)
    regenerated = spawn_seed_manifest(
        entropy=protocol.seed_manifest.entropy,
        count=protocol.seed_manifest.spawn_count,
    )

    assert protocol.seed_manifest.method == "numpy.random.SeedSequence.spawn"
    assert protocol.seed_manifest.seeds == regenerated
    assert len(set(regenerated)) == len(regenerated)


def test_loader_rejects_a_tampered_seed_manifest(tmp_path: Path) -> None:
    contents = PROTOCOL_PATH.read_text(encoding="utf-8")
    first_seed = str(load_protocol(PROTOCOL_PATH).seed_manifest.seeds[0])
    tampered = tmp_path / "credit-mechanism-v1.toml"
    tampered.write_text(contents.replace(first_seed, "1", 1), encoding="utf-8")

    with pytest.raises(ProtocolValidationError, match="seed manifest"):
        load_protocol(tampered)


def test_protocol_hash_normalizes_line_endings_and_covers_semantics(
    tmp_path: Path,
) -> None:
    original = load_protocol(PROTOCOL_PATH)
    contents = PROTOCOL_PATH.read_text(encoding="utf-8")
    crlf_path = tmp_path / "credit-mechanism-v1.toml"
    crlf_path.write_bytes(contents.replace("\n", "\r\n").encode("utf-8"))

    crlf = load_protocol(crlf_path)

    assert crlf.content_sha256 == original.content_sha256
    assert crlf.semantic_sha256 == original.semantic_sha256

    changed_path = tmp_path / "changed" / "credit-mechanism-v1.toml"
    changed_path.parent.mkdir()
    changed_path.write_text(
        contents.replace("engineering quick/research budgets", "fixed local budgets", 1),
        encoding="utf-8",
    )
    changed = load_protocol(changed_path)
    assert changed.content_sha256 != original.content_sha256
    assert changed.semantic_sha256 != original.semantic_sha256


def test_execution_audit_reports_deviations_and_failures_without_hiding_them() -> None:
    protocol = load_protocol(PROTOCOL_PATH)
    audit = audit_protocol_execution(
        protocol,
        mode="quick",
        observed_protocol_sha256="0" * 64,
        executed_seeds=protocol.seed_manifest.seeds[:3],
        completed_replications=3,
        observed_outcomes=("frozen_profit_difference",),
        stopped_early=True,
        tolerance_breaches=("solver_residual",),
    )

    assert {issue.code for issue in audit.deviations} == {
        "protocol_hash_mismatch",
        "seed_manifest_mismatch",
        "sample_size_mismatch",
        "unplanned_early_stop",
    }
    assert {issue.code for issue in audit.failures} == {
        "missing_outcomes",
        "tolerance_breach",
    }
    assert audit.passed is False


def test_execution_audit_accepts_only_the_exact_quick_contract() -> None:
    protocol = load_protocol(PROTOCOL_PATH)
    quick_count = protocol.sample_sizes.quick_replications
    audit = audit_protocol_execution(
        protocol,
        mode="quick",
        observed_protocol_sha256=protocol.content_sha256,
        executed_seeds=protocol.seed_manifest.seeds[:quick_count],
        completed_replications=quick_count,
        observed_outcomes=tuple(outcome.name for outcome in protocol.outcomes),
        stopped_early=False,
        tolerance_breaches=(),
    )

    assert audit.deviations == ()
    assert audit.failures == ()
    assert audit.passed is True


def test_locked_runner_retains_diagnostics_but_invalidates_analysis() -> None:
    report = run_locked_protocol(load_protocol(PROTOCOL_PATH), mode="quick")

    assert report["status"] == "fail"
    assert report["analysis_valid"] is False
    assert report["claim_authorized"] is False
    assert report["evidence_status"] == "diagnostic_only"
    assert len(report["executed_seeds"]) == 4  # type: ignore[arg-type]
    assert set(report["outcomes"]) == {  # type: ignore[arg-type]
        "frozen_profit_difference",
        "selective_profit_difference",
        "full_information_profit_difference",
        "selective_repair_rate",
        "full_information_repair_rate",
    }


def test_installed_protocol_cli_serializes_runner_result(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    protocol = load_protocol(PROTOCOL_PATH)

    monkeypatch.setattr(protocol_cli, "load_protocol", lambda _path: protocol)

    def fake_run(_protocol: object, *, mode: str) -> dict[str, Any]:
        return {"schema_version": "test", "status": "pass", "mode": mode}

    monkeypatch.setattr(protocol_cli, "run_locked_protocol", fake_run)

    assert protocol_cli.main(["--quick"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "mode": "quick",
        "schema_version": "test",
        "status": "pass",
    }


def test_installed_protocol_cli_reports_validation_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_load(_path: object) -> None:
        raise ProtocolValidationError("bad lock")

    monkeypatch.setattr(protocol_cli, "load_protocol", fail_load)

    assert protocol_cli.main(["--quick"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "fail"
    assert report["analysis_valid"] is False
    assert report["claim_authorized"] is False
    assert report["evidence_status"] == "diagnostic_only"
    assert report["failures"] == [
        {"code": "protocol_execution_error", "detail": "bad lock"}
    ]
