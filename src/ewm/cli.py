"""Non-interactive command-line access to the EWM experiment registry."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from .api import (
    describe,
    list_experiments,
    list_scenarios,
    run_experiment,
)
from .experiments import (
    ArtifactVerificationError,
    RunReplayError,
    VerificationReport,
    verify_and_replay_run,
    verify_run,
)
from .ontology import (
    DEFAULT_PROFILES,
    ProjectionCompilationError,
    ProjectionVerificationError,
    ProjectionVerificationReport,
    compile_run_projection,
    verify_projection_bundle,
    write_projection_bundle,
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
    verify_parser = commands.add_parser(
        "verify-run", help="verify one sealed or legacy run bundle"
    )
    verify_parser.add_argument("run_dir", type=Path)
    replay_parser = commands.add_parser(
        "replay-run", help="verify and deterministically replay one supported run"
    )
    replay_parser.add_argument("run_dir", type=Path)
    ontology_parser = commands.add_parser(
        "ontology",
        help="project and verify read-only ontology bundles",
    )
    ontology_commands = ontology_parser.add_subparsers(
        dest="ontology_command",
        required=True,
    )
    project_parser = ontology_commands.add_parser(
        "project",
        help="project one verified run into an explicit derived output path",
    )
    project_parser.add_argument("--run-dir", type=Path, required=True)
    project_parser.add_argument("--output", type=Path, required=True)
    ontology_verify_parser = ontology_commands.add_parser(
        "verify",
        help="verify one sealed ontology projection bundle",
    )
    ontology_verify_parser.add_argument("--bundle", type=Path, required=True)
    return parser


def _print_json(value: object) -> None:
    print(json.dumps(value, allow_nan=False, sort_keys=True))


def _verification_data(report: VerificationReport) -> dict[str, object]:
    return {
        "artifact_schema": report.artifact_schema,
        "bundle_sha256": report.bundle_sha256,
        "identity_sha256": report.identity_sha256,
        "integrity_level": report.integrity_level,
        "manifest_sha256": report.manifest_sha256,
        "manifest_size": report.manifest_size,
        "ok": True,
        "payloads": {
            name: dict(checksum) for name, checksum in report.payloads.items()
        },
        "run_dir": str(report.run_dir),
        "run_hash": report.run_hash,
    }


def _failure_data(operation: str, run_dir: Path, error: Exception) -> dict[str, object]:
    return {
        "error": str(error),
        "error_type": type(error).__name__,
        "ok": False,
        "operation": operation,
        "run_dir": str(run_dir),
    }


def _projection_verification_data(
    report: ProjectionVerificationReport,
) -> dict[str, object]:
    return {
        "adapter_digest": report.adapter_digest,
        "adapter_identity": report.adapter_identity,
        "artifact_schema": report.artifact_schema,
        "bundle_dir": str(report.bundle_dir),
        "bundle_sha256": report.bundle_sha256,
        "integrity_level": report.integrity_level,
        "ok": True,
        "operation": "ontology.verify",
        "payloads": {
            name: dict(checksum) for name, checksum in report.payloads.items()
        },
        "projection_digest": report.projection_digest,
        "source_bundle_sha256": report.source_bundle_sha256,
        "source_fingerprint": report.source_fingerprint,
        "source_identity_sha256": report.source_identity_sha256,
        "source_manifest_sha256": report.source_manifest_sha256,
        "source_run_hash": report.source_run_hash,
    }


def _ontology_project(run_dir: Path, output: Path) -> int:
    try:
        compilation = compile_run_projection(run_dir, adapters=DEFAULT_PROFILES)
        bundle = write_projection_bundle(
            output,
            compilation.projection,
            compilation.provenance,
            source_run_dir=run_dir,
        )
        report = verify_projection_bundle(bundle)
    except (OSError, ProjectionCompilationError, ProjectionVerificationError) as error:
        _print_json(
            {
                "error": str(error),
                "error_type": type(error).__name__,
                "ok": False,
                "operation": "ontology.project",
                "output": str(output),
                "run_dir": str(run_dir),
            }
        )
        return 1
    _print_json(
        {
            "adapter_identity": report.adapter_identity,
            "bundle_dir": str(bundle),
            "bundle_sha256": report.bundle_sha256,
            "ok": True,
            "operation": "ontology.project",
            "projection_digest": report.projection_digest,
            "source_run_hash": report.source_run_hash,
        }
    )
    return 0


def _ontology_verify(bundle: Path) -> int:
    try:
        report = verify_projection_bundle(bundle)
    except ProjectionVerificationError as error:
        _print_json(
            {
                "bundle_dir": str(bundle),
                "error": str(error),
                "error_type": type(error).__name__,
                "ok": False,
                "operation": "ontology.verify",
            }
        )
        return 1
    _print_json(_projection_verification_data(report))
    return 0


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
    if arguments.command == "verify-run":
        run_dir = Path(arguments.run_dir)
        try:
            _print_json(_verification_data(verify_run(run_dir)))
        except ArtifactVerificationError as error:
            _print_json(_failure_data("verify-run", run_dir, error))
            return 1
        return 0
    if arguments.command == "replay-run":
        run_dir = Path(arguments.run_dir)
        try:
            _print_json(asdict(verify_and_replay_run(run_dir)))
        except (ArtifactVerificationError, RunReplayError) as error:
            _print_json(_failure_data("replay-run", run_dir, error))
            return 1
        return 0
    if arguments.command == "ontology":
        if arguments.ontology_command == "project":
            return _ontology_project(Path(arguments.run_dir), Path(arguments.output))
        return _ontology_verify(Path(arguments.bundle))
    run = run_experiment(
        str(arguments.experiment),
        preset=str(arguments.preset),
        seed=int(arguments.seed),
        output_root=arguments.output,
    )
    _print_json(
        {
            "run_hash": run.run_hash,
            "run_dir": str(run.run_dir),
            "elapsed_seconds": run.elapsed_seconds,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
