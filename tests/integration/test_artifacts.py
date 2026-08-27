from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

import ewm

EXPECTED_ARTIFACTS = {
    "manifest.json",
    "config.json",
    "metrics.json",
    "summary.csv",
    "trace.npz",
    "events.jsonl",
}


def _contents(run_dir: Path) -> dict[str, bytes]:
    return {name: (run_dir / name).read_bytes() for name in EXPECTED_ARTIFACTS}


def test_identical_experiment_inputs_produce_identical_artifacts(
    tmp_path: Path,
) -> None:
    first = ewm.run_experiment(
        "forecasting.ddge",
        preset="smoke",
        seed=42,
        output_root=tmp_path,
    )
    first_contents = _contents(first.run_dir)
    second = ewm.run_experiment(
        "forecasting.ddge",
        preset="smoke",
        seed=42,
        output_root=tmp_path,
    )

    assert first.run_hash == second.run_hash
    assert first.run_dir == second.run_dir
    assert first_contents == _contents(second.run_dir)
    assert {path.name for path in first.run_dir.iterdir()} == EXPECTED_ARTIFACTS

    manifest = json.loads((first.run_dir / "manifest.json").read_text())
    config = json.loads((first.run_dir / "config.json").read_text())
    metrics = json.loads((first.run_dir / "metrics.json").read_text())
    assert manifest["run_hash"] == first.run_hash
    assert manifest["artifact_schema"] == "ewm.run.v2"
    assert manifest["identity_sha256"].startswith(first.run_hash)
    assert manifest["integrity_level"] == "checksummed"
    assert manifest["experiment"] == "forecasting.ddge"
    assert len(manifest["source_fingerprint"]) == 64
    assert set(manifest["runtime_environment"]) == {
        "numpy",
        "pandas",
        "python",
        "scikit-learn",
        "scipy",
    }
    assert config["seed"] == 42
    assert metrics["root_count"] == 3

    with np.load(first.run_dir / "trace.npz") as trace:
        assert trace["roots"].shape == (3,)
    with (first.run_dir / "summary.csv").open(newline="") as handle:
        rows = tuple(csv.DictReader(handle))
    assert {row["metric"] for row in rows} == set(metrics)
    events = tuple(
        json.loads(line)
        for line in (first.run_dir / "events.jsonl").read_text().splitlines()
    )
    assert events
    assert [event["sequence"] for event in events] == list(range(len(events)))


@pytest.mark.parametrize("experiment", ewm.list_experiments())
def test_every_registered_smoke_experiment_runs(
    experiment: str, tmp_path: Path
) -> None:
    run = ewm.run_experiment(
        experiment,
        preset="smoke",
        seed=7,
        output_root=tmp_path,
    )

    assert run.result.metrics
    assert run.run_dir.is_dir()


def test_credit_artifacts_expose_solver_convergence(tmp_path: Path) -> None:
    run = ewm.run_experiment(
        "credit.regimes",
        preset="smoke",
        seed=42,
        output_root=tmp_path,
    )
    metrics = json.loads((run.run_dir / "metrics.json").read_text())
    config = json.loads((run.run_dir / "config.json").read_text())

    assert isinstance(metrics["selective_ddge.converged"], bool)
    assert isinstance(metrics["full_information_ddge.converged"], bool)
    assert metrics["selective_ddge.iterations"] > 0
    assert metrics["full_information_ddge.iterations"] > 0
    assert config["metadata"]["configuration"] == "cong_qualitative_reconstruction"
    assert config["metadata"]["claim_type"] == "qualitative-reconstruction"
    assert config["metadata"]["exact_replication"] is False
    assert config["metadata"]["sampling_noise_floor"] is None
    assert "full_information_underperforms_selective" in config["metadata"][
        "qualitative_orderings"
    ]
