"""End-to-end projection from a sealed run to a sealed derived bundle."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ewm.core import ExperimentResult
from ewm.experiments.runs.artifacts import write_artifacts
from ewm.experiments.runs.identity import build_run_identity, identity_sha256
from ewm.ontology import CoverageEntry, OntologyObject
from ewm.ontology.graph.identity import make_ontology_ref
from ewm.ontology.profiles.base import OntologyProfileContext, ProfileProjection
from ewm.ontology.projection import write_projection_bundle
from ewm.ontology.projection.compiler import compile_run_projection
from ewm.ontology.projection.verification import load_projection_bundle, verify_projection_bundle


@dataclass(frozen=True, slots=True)
class IntegrationProfile:
    identity: str = "ewm.integration-profile.v1"
    experiment_ids: frozenset[str] = frozenset({"integration.experiment"})
    package_versions: frozenset[str] = frozenset({"0.2.0"})
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
            properties={"evidence_origin": "adapter_derived", "scenario": context.scenario},
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
            ),
        )


def _sealed_run(root: Path) -> Path:
    identity = build_run_identity(
        experiment="integration.experiment",
        package_version="0.2.0",
        parameters={"theta": 0.25},
        preset="smoke",
        runtime_environment={"numpy": "test", "python": "test"},
        scenario="integration",
        seed=11,
        source_fingerprint="a" * 64,
    )
    return write_artifacts(
        output_root=root,
        run_hash=identity_sha256(identity)[:20],
        experiment="integration.experiment",
        scenario="integration",
        preset="smoke",
        seed=11,
        parameters={"theta": 0.25},
        result=ExperimentResult(
            scenario="integration",
            experiment="integration.experiment",
            metrics={"loss": 0.125},
            metadata={"purpose": "real projection integration"},
        ),
        traces={"theta": np.asarray([0.0, 0.25])},
        events=({"kind": "deployed", "theta": 0.25},),
        package_version="0.2.0",
        runtime_environment={"numpy": "test", "python": "test"},
        source_fingerprint="a" * 64,
        identity=identity,
    )


def test_verified_run_projects_read_only_and_publishes_verifiable_bundle(
    tmp_path: Path,
) -> None:
    run_dir = _sealed_run(tmp_path / "runs")
    before = {path.name: path.read_bytes() for path in run_dir.iterdir()}

    compilation = compile_run_projection(run_dir, adapters=(IntegrationProfile(),))
    bundle = write_projection_bundle(
        tmp_path / "derived" / "ontology",
        compilation.projection,
        compilation.provenance,
        source_run_dir=run_dir,
    )

    assert verify_projection_bundle(bundle).source_run_hash == run_dir.name
    assert load_projection_bundle(bundle) == compilation.projection
    assert before == {path.name: path.read_bytes() for path in run_dir.iterdir()}
    assert not (run_dir / "ontology").exists()
