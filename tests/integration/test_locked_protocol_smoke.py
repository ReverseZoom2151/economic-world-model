from __future__ import annotations

import hashlib
import json
import subprocess
import sys

from ewm.experiments.protocols import DEFAULT_PROTOCOL_PATH

PROTOCOL_PATH = DEFAULT_PROTOCOL_PATH


def test_quick_locked_protocol_runs_with_prespecified_statistics() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_protocol.py",
            "--protocol",
            str(PROTOCOL_PATH),
            "--quick",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert report["schema_version"] == "ewm.local-protocol-report.v1"
    assert report["lock_status"] == "prospectively locked locally"
    assert report["protocol_sha256"] == hashlib.sha256(
        PROTOCOL_PATH.read_bytes()
    ).hexdigest()
    assert report["mode"] == "quick"
    assert report["status"] == "fail"
    assert report["analysis_valid"] is False
    assert report["claim_authorized"] is False
    assert report["evidence_status"] == "diagnostic_only"
    assert report["completed_replications"] == 4
    assert len(report["executed_seeds"]) == 4
    assert report["deviations"] == []
    assert report["failures"] == [
        {
            "code": "tolerance_breach",
            "detail": (
                "solver_residual:seed=4634151411735334228, "
                "solver_residual:seed=9609146241510126290, "
                "solver_residual:seed=13113865875779171417, "
                "solver_residual:seed=13561250051540582239"
            ),
        }
    ]
    assert report["maximum_solver_residual"] > 0.001

    outcomes = report["outcomes"]
    assert set(outcomes) == {
        "frozen_profit_difference",
        "selective_profit_difference",
        "full_information_profit_difference",
        "selective_repair_rate",
        "full_information_repair_rate",
    }
    for name in (
        "frozen_profit_difference",
        "selective_profit_difference",
        "full_information_profit_difference",
    ):
        assert outcomes[name]["interval_method"] == "student_t"
        assert outcomes[name]["bootstrap_method"] == "paired_percentile"
    for name in ("selective_repair_rate", "full_information_repair_rate"):
        assert outcomes[name]["method"] == "wilson"

    assert report["multiplicity"]["method"] == "holm"
    assert len(report["multiplicity"]["adjusted_p_values"]) == 3
