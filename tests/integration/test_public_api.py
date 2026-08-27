from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import ewm
from ewm.cli import main
from ewm.equilibrium import FixedPointConfig
from ewm.scenarios.fx import FXSimulationResult


def test_make_rollout_and_ddge_use_the_public_facade() -> None:
    fx = ewm.make("fx", preset="smoke", seed=42)
    trajectory = ewm.rollout(fx, periods=4)

    assert isinstance(trajectory, FXSimulationResult)
    assert len(trajectory.volumes) == 4

    forecasting = ewm.make("forecasting", preset="smoke", seed=42)
    problem = forecasting.ddge_problem()
    result = ewm.solve_ddge(
        problem,
        (np.array([-1.5]), np.array([0.0]), np.array([1.5])),
        FixedPointConfig(tolerance=1e-9, max_iterations=500),
    )

    assert len(result.fixed_points) == 3


def test_registry_descriptions_and_errors_are_helpful() -> None:
    assert ewm.list_scenarios() == ("credit", "forecasting", "fx", "scalar")
    assert "Data-Driven Generative Equilibrium" in ewm.describe("forecasting")

    with pytest.raises(ValueError, match=r"unknown scenario.*credit, forecasting, fx, scalar"):
        ewm.make("missing")
    with pytest.raises(ValueError, match="does not define a DDGE problem"):
        ewm.make("fx").ddge_problem()


def test_cli_lists_and_describes_scenarios(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list"]) == 0
    listing = capsys.readouterr().out
    assert "forecasting" in listing
    assert "fx" in listing
    assert "credit" in listing

    assert main(["describe", "credit"]) == 0
    assert "selective" in capsys.readouterr().out.lower()


def test_cli_run_writes_and_reports_reproducible_artifacts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = main(
        [
            "run",
            "forecasting.ddge",
            "--preset",
            "smoke",
            "--seed",
            "42",
            "--output",
            str(tmp_path),
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert status == 0
    assert output["run_hash"]
    assert Path(output["run_dir"]).is_dir()
    assert (Path(output["run_dir"]) / "manifest.json").is_file()
