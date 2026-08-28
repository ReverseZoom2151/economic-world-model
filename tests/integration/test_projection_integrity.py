"""Adversarial integrity checks for derived ontology projection bundles."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ewm.core.serialization import content_digest
from ewm.ontology import CoverageEntry, OntologyObject, OntologyRef, SourceLocator
from ewm.ontology.projection import (
    ProjectionBundleProvenance,
    seal_projection,
    write_projection_bundle,
)
from ewm.ontology.verification import ProjectionVerificationError, verify_projection_bundle

_IDENTITY = "1" * 64


def _bundle(tmp_path: Path) -> Path:
    source = SourceLocator(
        source_kind="verified_run",
        source_id=_IDENTITY,
        artifact_path="run/manifest.json",
        record_selector="manifest",
        payload_digest="2" * 64,
    )
    run_ref = OntologyRef("ewm:runtime:run:" + "3" * 64, "run")
    run = OntologyObject(
        ref=run_ref,
        layer="runtime_occurrence",
        properties={"seed": 7},
        sources=(source,),
    )
    coverage = CoverageEntry(
        source=source,
        field="manifest.json",
        status="projected",
        targets=(run_ref,),
        reason=None,
    )
    projection = seal_projection(
        schema="ewm.ontology.v1",
        source_run=run_ref,
        objects=(run,),
        relations=(),
        measurements=(),
        coverage=(coverage,),
    )
    provenance = ProjectionBundleProvenance(
        source_run_hash=_IDENTITY[:20],
        source_identity_sha256=_IDENTITY,
        source_manifest_sha256="4" * 64,
        source_bundle_sha256="5" * 64,
        source_fingerprint="6" * 64,
        adapter_identity="ewm.generic-run.v1",
        adapter_digest="7" * 64,
    )
    return write_projection_bundle(tmp_path / "projection", projection, provenance)


@pytest.mark.parametrize("name", ("projection.json", "coverage.json"))
def test_verifier_rejects_modified_payload(name: str, tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    (bundle / name).write_bytes((bundle / name).read_bytes() + b" ")

    with pytest.raises(ProjectionVerificationError, match=name):
        verify_projection_bundle(bundle)


@pytest.mark.parametrize("mutation", ("missing", "extra", "symlink"))
def test_verifier_requires_exact_regular_files(mutation: str, tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    if mutation == "missing":
        (bundle / "coverage.json").unlink()
    elif mutation == "extra":
        (bundle / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    else:
        (bundle / "coverage.json").unlink()
        (bundle / "coverage.json").symlink_to(bundle / "projection.json")

    with pytest.raises(ProjectionVerificationError):
        verify_projection_bundle(bundle)


def test_verifier_rejects_noncanonical_payload_bytes(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    projection_path = bundle / "projection.json"
    data = json.loads(projection_path.read_bytes())
    projection_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    _reseal_payloads_only(bundle)

    with pytest.raises(ProjectionVerificationError, match="canonical"):
        verify_projection_bundle(bundle)


def test_resealed_semantic_mutation_still_fails_projection_identity(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    projection_path = bundle / "projection.json"
    data = json.loads(projection_path.read_bytes())
    data["objects"][0]["properties"]["seed"] = 99
    projection_path.write_text(_canonical_text(data), encoding="utf-8")
    _reseal_payloads_only(bundle)

    with pytest.raises(ProjectionVerificationError, match="projection digest"):
        verify_projection_bundle(bundle)


def test_self_consistent_payload_checksums_cannot_replace_projection_digest(
    tmp_path: Path,
) -> None:
    bundle = _bundle(tmp_path)
    replacement = "f" * 64
    for name in ("projection.json", "coverage.json"):
        path = bundle / name
        data = json.loads(path.read_bytes())
        data["projection_digest"] = replacement
        path.write_text(_canonical_text(data), encoding="utf-8")
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["projection_digest"] = replacement
    manifest_path.write_text(_canonical_text(manifest), encoding="utf-8")
    _reseal_payloads_only(bundle)

    with pytest.raises(ProjectionVerificationError, match="projection digest"):
        verify_projection_bundle(bundle)


def _canonical_text(value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _reseal_payloads_only(bundle: Path) -> None:
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    payloads = {}
    for name in ("projection.json", "coverage.json"):
        content = (bundle / name).read_bytes()
        payloads[name] = {
            "sha256": hashlib.sha256(content).hexdigest(),
            "size": len(content),
        }
    manifest["payloads"] = payloads
    manifest["bundle_sha256"] = content_digest(
        {
            "artifact_schema": manifest["artifact_schema"],
            "source_run": manifest["source_run"],
            "adapter": manifest["adapter"],
            "projection_digest": manifest["projection_digest"],
            "payloads": payloads,
        }
    )
    manifest_path.write_text(_canonical_text(manifest), encoding="utf-8")
