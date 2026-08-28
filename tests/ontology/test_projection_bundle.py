"""Contract tests for atomic, deterministic ontology projection bundles."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ewm.ontology import CoverageEntry, OntologyObject, OntologyRef, SourceLocator
from ewm.ontology.projection import (
    ProjectionBundleProvenance,
    seal_projection,
    write_projection_bundle,
)
from ewm.ontology.verification import (
    ProjectionVerificationError,
    load_projection_bundle,
    verify_projection_bundle,
)

EXPECTED_FILES = {"manifest.json", "projection.json", "coverage.json"}
_SOURCE_IDENTITY = "1" * 64
_RUN_HASH = _SOURCE_IDENTITY[:20]


def _source() -> SourceLocator:
    return SourceLocator(
        source_kind="verified_run",
        source_id=_SOURCE_IDENTITY,
        artifact_path="run/manifest.json",
        record_selector="manifest",
        payload_digest="2" * 64,
    )


def _projection(*, seed: int = 7):
    source = _source()
    run_ref = OntologyRef("ewm:runtime:run:" + "3" * 64, "run")
    run = OntologyObject(
        ref=run_ref,
        layer="runtime_occurrence",
        properties={"seed": seed, "natural_key": _RUN_HASH},
        sources=(source,),
    )
    coverage = CoverageEntry(
        source=source,
        field="manifest.json",
        status="projected",
        targets=(run_ref,),
        reason=None,
    )
    return seal_projection(
        schema="ewm.ontology.v1",
        source_run=run_ref,
        objects=(run,),
        relations=(),
        measurements=(),
        coverage=(coverage,),
    )


def _provenance() -> ProjectionBundleProvenance:
    return ProjectionBundleProvenance(
        source_run_hash=_RUN_HASH,
        source_identity_sha256=_SOURCE_IDENTITY,
        source_manifest_sha256="4" * 64,
        source_bundle_sha256="5" * 64,
        source_fingerprint="6" * 64,
        adapter_identity="ewm.generic-run.v1",
        adapter_digest="7" * 64,
    )


def test_writer_publishes_exact_canonical_bundle_and_verifier_loads_it(
    tmp_path: Path,
) -> None:
    target = tmp_path / "projection"
    projection = _projection()

    assert write_projection_bundle(target, projection, _provenance()) == target
    report = verify_projection_bundle(target)
    loaded = load_projection_bundle(target)
    manifest = json.loads((target / "manifest.json").read_bytes())

    assert {path.name for path in target.iterdir()} == EXPECTED_FILES
    assert loaded == projection
    assert report.artifact_schema == "ewm.ontology.v1"
    assert report.integrity_level == "checksummed"
    assert report.projection_digest == projection.projection_digest
    assert report.source_run_hash == _RUN_HASH
    assert report.adapter_identity == "ewm.generic-run.v1"
    assert manifest["source_run"]["identity_sha256"] == _SOURCE_IDENTITY
    assert manifest["source_run"]["source_fingerprint"] == "6" * 64
    assert manifest["adapter"]["digest"] == "7" * 64
    assert "created_at" not in manifest
    assert "timestamp" not in manifest
    for name in EXPECTED_FILES:
        content = (target / name).read_bytes()
        assert content == json.dumps(
            json.loads(content),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")


def test_manifest_seals_payload_sizes_and_digests(tmp_path: Path) -> None:
    target = write_projection_bundle(tmp_path / "projection", _projection(), _provenance())
    manifest = json.loads((target / "manifest.json").read_bytes())

    assert set(manifest["payloads"]) == {"projection.json", "coverage.json"}
    for name, metadata in manifest["payloads"].items():
        content = (target / name).read_bytes()
        assert metadata["size"] == len(content)
        assert len(metadata["sha256"]) == 64


def test_identical_publication_converges_and_different_collision_fails(
    tmp_path: Path,
) -> None:
    target = tmp_path / "projection"
    first = write_projection_bundle(target, _projection(), _provenance())
    second = write_projection_bundle(target, _projection(), _provenance())

    assert first == second
    with pytest.raises(ProjectionVerificationError, match="collision"):
        write_projection_bundle(target, _projection(seed=8), _provenance())
    assert load_projection_bundle(target) == _projection()


def test_writer_refuses_to_publish_inside_the_sealed_source_run(tmp_path: Path) -> None:
    source_run = tmp_path / "sealed-run"
    source_run.mkdir()
    sentinel = source_run / "manifest.json"
    sentinel.write_bytes(b"sealed")

    with pytest.raises(ProjectionVerificationError, match="source run"):
        write_projection_bundle(
            source_run / "ontology",
            _projection(),
            _provenance(),
            source_run_dir=source_run,
        )

    assert sentinel.read_bytes() == b"sealed"
    assert set(source_run.iterdir()) == {sentinel}


def test_failed_validation_leaves_no_target_or_staging_directory(tmp_path: Path) -> None:
    projection = _projection()
    invalid = type(projection)(
        schema=projection.schema,
        source_run=projection.source_run,
        objects=(),
        relations=projection.relations,
        measurements=projection.measurements,
        coverage=projection.coverage,
        projection_digest=projection.projection_digest,
    )
    target = tmp_path / "projection"

    with pytest.raises((ProjectionVerificationError, ValueError)):
        write_projection_bundle(target, invalid, _provenance())

    assert not target.exists()
    assert tuple(tmp_path.iterdir()) == ()

