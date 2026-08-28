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
    GeoOverlayError,
    ProjectionCompilationError,
    ProjectionVerificationError,
    ProjectionVerificationReport,
    apply_geo_overlay,
    compile_run_projection,
    verify_projection_bundle,
    write_projection_bundle,
)
from .ontology.snapshot import (
    SnapshotSelection,
    SnapshotSizeError,
    SnapshotSource,
    compile_investigation,
)
from .workbench.export import (
    SnapshotExportError,
    SnapshotVerificationError,
    export_snapshot_html,
    verify_snapshot_html,
    write_detached_sha256,
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
    project_parser.add_argument(
        "--geo-overlay",
        type=Path,
        help="optional explicit ewm.geo-overlay.v1 sidecar outside the sealed run",
    )
    ontology_verify_parser = ontology_commands.add_parser(
        "verify",
        help="verify one sealed ontology projection bundle",
    )
    ontology_verify_parser.add_argument("--bundle", type=Path, required=True)
    snapshot_parser = commands.add_parser(
        "snapshot",
        help="compile and verify portable offline investigations",
    )
    snapshot_commands = snapshot_parser.add_subparsers(
        dest="snapshot_command",
        required=True,
    )
    snapshot_export_parser = snapshot_commands.add_parser(
        "export",
        help="compile one verified run into a standalone HTML investigation",
    )
    snapshot_export_parser.add_argument("run_dir", type=Path)
    snapshot_export_parser.add_argument("--selection", type=Path, required=True)
    snapshot_export_parser.add_argument("--output", type=Path, required=True)
    snapshot_verify_parser = snapshot_commands.add_parser(
        "verify",
        help="verify standalone HTML and its embedded investigation",
    )
    snapshot_verify_parser.add_argument("file", type=Path)
    snapshot_verify_parser.add_argument(
        "--expected-sha256",
        help="separately obtained full-file SHA-256 for authenticity comparison",
    )
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


def _ontology_project(
    run_dir: Path,
    output: Path,
    geo_overlay: Path | None = None,
) -> int:
    try:
        compilation = compile_run_projection(run_dir, adapters=DEFAULT_PROFILES)
        application = (
            apply_geo_overlay(compilation.projection, geo_overlay)
            if geo_overlay is not None
            else None
        )
        projection = (
            application.projection if application is not None else compilation.projection
        )
        bundle = write_projection_bundle(
            output,
            projection,
            compilation.provenance,
            source_run_dir=run_dir,
        )
        report = verify_projection_bundle(bundle)
    except (
        OSError,
        GeoOverlayError,
        ProjectionCompilationError,
        ProjectionVerificationError,
    ) as error:
        _print_json(
            {
                "error": str(error),
                "error_type": type(error).__name__,
                "ok": False,
                "operation": "ontology.project",
                "output": str(output),
                "run_dir": str(run_dir),
                **(
                    {"geo_overlay": str(geo_overlay)}
                    if geo_overlay is not None
                    else {}
                ),
            }
        )
        return 1
    result: dict[str, object] = {
        "adapter_identity": report.adapter_identity,
        "bundle_dir": str(bundle),
        "bundle_sha256": report.bundle_sha256,
        "ok": True,
        "operation": "ontology.project",
        "projection_digest": report.projection_digest,
        "source_run_hash": report.source_run_hash,
    }
    if application is not None:
        result["geo_overlay_digest"] = application.overlay_digest
        result["geo_anchor_count"] = application.anchor_count
    _print_json(result)
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


def _snapshot_export(run_dir: Path, selection_path: Path, output: Path) -> int:
    try:
        selection_value = json.loads(selection_path.read_text(encoding="utf-8"))
        if not isinstance(selection_value, dict):
            raise ValueError("snapshot selection must contain a JSON object")
        selection = SnapshotSelection.from_data(selection_value)
        compilation = compile_run_projection(run_dir, adapters=DEFAULT_PROFILES)
        provenance = compilation.provenance
        snapshot = compile_investigation(
            compilation.projection,
            SnapshotSource(
                run_id=provenance.source_run_hash,
                source_run_hash=provenance.source_run_hash,
                source_identity_sha256=provenance.source_identity_sha256,
                source_bundle_sha256=provenance.source_bundle_sha256,
                profile_identity=provenance.adapter_identity,
                profile_digest=provenance.adapter_digest,
                integrity_level="checksummed",
            ),
            selection,
        )
        report = export_snapshot_html(snapshot, output)
        detached = write_detached_sha256(report)
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        ProjectionCompilationError,
        SnapshotExportError,
        SnapshotSizeError,
    ) as error:
        result: dict[str, object] = {
            "error": str(error),
            "error_type": type(error).__name__,
            "ok": False,
            "operation": "snapshot.export",
            "output": str(output),
            "run_dir": str(run_dir),
            "selection": str(selection_path),
        }
        if isinstance(error, SnapshotExportError | SnapshotSizeError):
            result["diagnostic"] = error.as_dict()
        _print_json(result)
        return 1
    _print_json(
        {
            "authenticity_claim": report.authenticity_claim,
            "detached_sha256": str(detached),
            "digital_signature_present": report.digital_signature_present,
            "embedded_sha256": report.embedded_sha256,
            "file_sha256": report.file_sha256,
            "html_bytes": report.html_bytes,
            "ok": True,
            "operation": "snapshot.export",
            "output": str(output),
            "projection_digest": report.projection_digest,
            "subset_digest": report.subset_digest,
        }
    )
    return 0


def _snapshot_verify(path: Path, expected_file_sha256: str | None) -> int:
    try:
        report = verify_snapshot_html(
            path,
            expected_file_sha256=expected_file_sha256,
        )
    except SnapshotVerificationError as error:
        _print_json(
            {
                "error": str(error),
                "error_type": type(error).__name__,
                "file": str(path),
                "ok": False,
                "operation": "snapshot.verify",
            }
        )
        return 1
    _print_json(
        {
            "authenticity_claim": report.authenticity_claim,
            "authenticity_verified": report.authenticity_verified,
            "digital_signature_present": report.digital_signature_present,
            "embedded_sha256": report.embedded_sha256,
            "file": str(path),
            "file_sha256": report.file_sha256,
            "ok": True,
            "operation": "snapshot.verify",
            "projection_digest": report.projection_digest,
            "source_bundle_sha256": report.source_bundle_sha256,
            "subset_digest": report.subset_digest,
        }
    )
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
            return _ontology_project(
                Path(arguments.run_dir),
                Path(arguments.output),
                (
                    Path(arguments.geo_overlay)
                    if arguments.geo_overlay is not None
                    else None
                ),
            )
        return _ontology_verify(Path(arguments.bundle))
    if arguments.command == "snapshot":
        if arguments.snapshot_command == "export":
            return _snapshot_export(
                Path(arguments.run_dir),
                Path(arguments.selection),
                Path(arguments.output),
            )
        return _snapshot_verify(
            Path(arguments.file),
            (
                str(arguments.expected_sha256)
                if arguments.expected_sha256 is not None
                else None
            ),
        )
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
