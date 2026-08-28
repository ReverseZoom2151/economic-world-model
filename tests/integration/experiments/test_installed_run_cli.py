"""Installed-distribution contracts for experiment commands."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import sysconfig
from pathlib import Path

import ewm


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def test_built_wheel_installs_verify_and_replay_commands(tmp_path: Path) -> None:
    repository = Path(__file__).parents[3]
    run_dir = ewm.run_experiment(
        "fx.rollout",
        preset="smoke",
        seed=23,
        output_root=tmp_path / "runs",
    ).run_dir
    distribution = tmp_path / "dist"
    _run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--outdir",
            str(distribution),
        ],
        cwd=repository,
    )
    wheel = next(distribution.glob("*.whl"))
    environment_dir = tmp_path / "installed"
    _run(
        [sys.executable, "-m", "venv", "--system-site-packages", str(environment_dir)],
        cwd=tmp_path,
    )
    scripts = environment_dir / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    command = scripts / ("ewm.exe" if os.name == "nt" else "ewm")
    _run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--force-reinstall",
            "--no-deps",
            str(wheel),
        ],
        cwd=tmp_path,
    )
    installed_site = Path(
        _run(
            [str(python), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
            cwd=tmp_path,
        ).strip()
    )
    (installed_site / "ewm-test-dependencies.pth").write_text(
        str(sysconfig.get_paths()["purelib"]) + "\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)

    listing = _run([str(command), "list"], cwd=tmp_path, env=env)
    verification = json.loads(
        _run([str(command), "verify-run", str(run_dir)], cwd=tmp_path, env=env)
    )
    replay = json.loads(
        _run([str(command), "replay-run", str(run_dir)], cwd=tmp_path, env=env)
    )
    installed_path = Path(
        _run(
            [str(python), "-c", "import ewm; print(ewm.__file__)"],
            cwd=tmp_path,
            env=env,
        ).strip()
    )

    assert "fx.rollout" in listing
    assert verification["ok"] is True
    assert replay["matched"] is True
    assert environment_dir in installed_path.parents
