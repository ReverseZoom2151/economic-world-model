"""Fail-closed source selection and coverage behavior for ontology compilation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from ewm.core import ExperimentResult
from ewm.experiments.runs.artifacts import write_artifacts
from ewm.experiments.runs.identity import build_run_identity, identity_sha256
from ewm.ontology import CoverageEntry, OntologyObject
from ewm.ontology.graph.identity import make_ontology_ref
from ewm.ontology.profiles.contracts.base import OntologyProfileContext, ProfileProjection
from ewm.ontology.projection.compiler import (
    ProjectionCompilationError,
    SourcePreflightLimits,
    compile_run_projection,
    inspect_run_bundle,
)


@dataclass(frozen=True, slots=True)
class ExampleProfile:
    identity: str = "ewm.example-profile.v1"
    experiment_ids: frozenset[str] = frozenset({"example.experiment"})
    package_versions: frozenset[str] = frozenset({"0.1.0"})
    artifact_schemas: frozenset[str] = frozenset({"ewm.run.v2"})
    source_digest: str = "9" * 64

    def project(self, context: OntologyProfileContext) -> ProfileProjection:
        world_ref = make_ontology_ref(
            namespace="declaration",
            kind="world",
            source_identity=self.source_digest,
            semantic_keys={"scenario": context.scenario},
        )
        world = OntologyObject(
            ref=world_ref,
            layer="economic_declaration",
            properties={
                "scenario": context.scenario,
                "evidence_origin": "adapter_derived",
            },
            sources=(context.adapter_source,),
        )
        return ProfileProjection(
            objects=(world,),
            relations=(),
            measurements=(),
            coverage=(
                CoverageEntry(
                    source=context.adapter_source,
                    field="adapter.world",
                    status="projected",
                    targets=(world_ref,),
                    reason=None,
                ),
                CoverageEntry(
                    source=context.adapter_source,
                    field="declaration.market",
                    status="unavailable",
                    targets=(),
                    reason="the sealed run does not declare market structure",
                ),
            ),
        )


def _write_run(
    root: Path,
    *,
    experiment: str = "example.experiment",
    package_version: str = "0.1.0",
    events: tuple[dict[str, object], ...] = (
        {"kind": "created", "value": 1},
        {"kind": "measured", "value": 2},
    ),
    traces: dict[str, np.ndarray[object] | np.ndarray[np.float64]] | None = None,
) -> Path:
    identity = build_run_identity(
        experiment=experiment,
        package_version=package_version,
        parameters={"scale": 2.0},
        preset="smoke",
        runtime_environment={"numpy": "test", "python": "test"},
        scenario="example",
        seed=7,
        source_fingerprint="a" * 64,
    )
    return write_artifacts(
        output_root=root,
        run_hash=identity_sha256(identity)[:20],
        experiment=experiment,
        scenario="example",
        preset="smoke",
        seed=7,
        parameters={"scale": 2.0},
        result=ExperimentResult(
            scenario="example",
            experiment=experiment,
            metrics={"count": 2, "passed": True, "score": 1.25},
            metadata={"purpose": "ontology-compiler-test"},
        ),
        traces={"values": np.asarray([1.0, 2.0])} if traces is None else traces,
        events=events,
        package_version=package_version,
        runtime_environment={"numpy": "test", "python": "test"},
        source_fingerprint="a" * 64,
        identity=identity,
    )


def test_compiler_selects_compatible_adapter_and_projects_complete_coverage(
    tmp_path: Path,
) -> None:
    run_dir = _write_run(tmp_path / "runs")

    result = compile_run_projection(run_dir, adapters=(ExampleProfile(),))
    projection = result.projection
    coverage_by_field = {entry.field: entry for entry in projection.coverage}

    assert result.adapter_identity == "ewm.example-profile.v1"
    assert result.source_report.artifact_schema == "ewm.run.v2"
    assert set(result.source_fields) <= coverage_by_field.keys()
    assert len(coverage_by_field) == len(projection.coverage)
    assert all(
        coverage_by_field[field].status in {"projected", "omitted", "rejected"}
        for field in result.source_fields
    )
    assert coverage_by_field["declaration.market"].status == "unavailable"
    assert "manifest.json.experiment" in result.source_fields
    assert "config.json.parameters" in result.source_fields
    assert "config.json.parameters.scale" in result.source_fields
    assert "manifest.json.identity.parameters.scale" in result.source_fields
    assert "metrics.json.score" in result.source_fields
    assert "events.jsonl[0].kind" in result.source_fields
    assert "trace.npz.values.npy" in result.source_fields


def test_adapter_derived_declarations_are_labeled_and_source_digested(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path / "runs")

    projection = compile_run_projection(run_dir, adapters=(ExampleProfile(),)).projection
    world = next(item for item in projection.objects if item.ref.kind == "world")

    assert world.properties["evidence_origin"] == "adapter_derived"
    assert world.sources[0].source_kind == "scenario_adapter"
    assert world.sources[0].source_id == "ewm.example-profile.v1"
    assert world.sources[0].payload_digest == "9" * 64


def test_unknown_experiment_and_incompatible_adapter_version_fail_closed(
    tmp_path: Path,
) -> None:
    unknown = _write_run(tmp_path / "unknown", experiment="unknown.experiment")
    incompatible = _write_run(tmp_path / "incompatible", package_version="9.9.9")

    with pytest.raises(ProjectionCompilationError, match="unknown experiment"):
        compile_run_projection(unknown, adapters=(ExampleProfile(),))
    with pytest.raises(ProjectionCompilationError, match="incompatible adapter version"):
        compile_run_projection(incompatible, adapters=(ExampleProfile(),))


def test_tampered_sealed_run_never_produces_projection(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path / "runs")
    (run_dir / "config.json").write_bytes((run_dir / "config.json").read_bytes() + b"tamper")

    with pytest.raises(ProjectionCompilationError, match="verification"):
        compile_run_projection(run_dir, adapters=(ExampleProfile(),))


@pytest.mark.parametrize(
    ("limits", "message"),
    (
        (SourcePreflightLimits(max_payload_bytes=16), "payload size"),
        (SourcePreflightLimits(max_event_lines=1), "event line"),
        (SourcePreflightLimits(max_npz_member_bytes=1), "NPZ member"),
    ),
)
def test_preflight_rejects_oversized_inputs_before_verification(
    limits: SourcePreflightLimits,
    message: str,
    tmp_path: Path,
) -> None:
    run_dir = _write_run(tmp_path / message.replace(" ", "-"))

    with pytest.raises(ProjectionCompilationError, match=message):
        compile_run_projection(run_dir, adapters=(ExampleProfile(),), limits=limits)


def test_preflight_rejects_high_ratio_npz_member(tmp_path: Path) -> None:
    run_dir = _write_run(
        tmp_path / "runs",
        traces={"zeros": np.zeros(100_000, dtype=np.float64)},
    )

    with pytest.raises(ProjectionCompilationError, match="compression ratio"):
        compile_run_projection(
            run_dir,
            adapters=(ExampleProfile(),),
            limits=SourcePreflightLimits(max_npz_compression_ratio=2.0),
        )


def test_legacy_bundle_can_be_diagnosed_but_not_projected(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path / "runs")
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    legacy = {
        key: manifest[key]
        for key in (
            "artifact_schema",
            "experiment",
            "package_version",
            "preset",
            "runtime_environment",
            "run_hash",
            "scenario",
            "seed",
            "source_fingerprint",
        )
    }
    legacy["artifact_schema"] = "ewm.run.v1"
    manifest_path.write_text(json.dumps(legacy, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    inspection = inspect_run_bundle(run_dir)

    assert inspection.artifact_schema == "ewm.run.v1"
    assert inspection.integrity_level == "legacy-unsealed"
    assert inspection.compilable is False
    with pytest.raises(ProjectionCompilationError, match="legacy"):
        compile_run_projection(run_dir, adapters=(ExampleProfile(),))
