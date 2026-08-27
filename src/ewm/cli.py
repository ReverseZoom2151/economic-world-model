"""Non-interactive command-line access to the EWM experiment registry."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .api import (
    describe,
    list_experiments,
    list_scenarios,
    run_experiment,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ewm",
        description="Run transparent Economic World Model experiments.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list scenarios and experiments")
    describe_parser = commands.add_parser("describe", help="describe one registry entry")
    describe_parser.add_argument("name")
    run_parser = commands.add_parser("run", help="execute one registered experiment")
    run_parser.add_argument("experiment", choices=list_experiments())
    run_parser.add_argument("--preset", choices=("smoke", "research"), default="smoke")
    run_parser.add_argument("--seed", type=int, default=42)
    run_parser.add_argument("--output", type=Path, default=Path("runs"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the CLI and return a process status code."""

    arguments = _parser().parse_args(argv)
    if arguments.command == "list":
        print("Scenarios:")
        for name in list_scenarios():
            print(f"  {name}")
        print("Experiments:")
        for name in list_experiments():
            print(f"  {name}")
        return 0
    if arguments.command == "describe":
        print(describe(str(arguments.name)))
        return 0
    run = run_experiment(
        str(arguments.experiment),
        preset=str(arguments.preset),
        seed=int(arguments.seed),
        output_root=arguments.output,
    )
    print(
        json.dumps(
            {
                "run_hash": run.run_hash,
                "run_dir": str(run.run_dir),
                "elapsed_seconds": run.elapsed_seconds,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
