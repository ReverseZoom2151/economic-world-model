"""Atomic construction and publication of derived ontology projection bundles."""

from __future__ import annotations

import os
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ewm.core.serialization import content_digest

from .bundles.digest import compute_projection_digest
from .identity import (
    canonical_bytes,
    coverage_entry_to_data,
    measurement_to_data,
    ontology_object_to_data,
    ontology_ref_to_data,
    relation_assertion_to_data,
)
from .model import (
    CoverageEntry,
    Measurement,
    OntologyObject,
    OntologyProjection,
    OntologyRef,
    RelationAssertion,
)
from .schema import OntologyValidationError, assert_valid_projection
from .verification import (
    ONTOLOGY_ARTIFACT_SCHEMA,
    ProjectionVerificationError,
    verify_projection_bundle,
)

_HEX_DIGITS = frozenset("0123456789abcdef")


def _require_hex(value: str, length: int, name: str) -> None:
    if len(value) != length or any(character not in _HEX_DIGITS for character in value):
        raise ValueError(f"{name} must be {length} lowercase hexadecimal characters")


@dataclass(frozen=True, slots=True)
class ProjectionBundleProvenance:
    """Verified source-run and adapter identities sealed into a projection bundle."""

    source_run_hash: str
    source_identity_sha256: str
    source_manifest_sha256: str
    source_bundle_sha256: str
    source_fingerprint: str
    adapter_identity: str
    adapter_digest: str

    def __post_init__(self) -> None:
        _require_hex(self.source_run_hash, 20, "source run hash")
        _require_hex(self.source_identity_sha256, 64, "source identity SHA-256")
        _require_hex(self.source_manifest_sha256, 64, "source manifest SHA-256")
        _require_hex(self.source_bundle_sha256, 64, "source bundle SHA-256")
        _require_hex(self.source_fingerprint, 64, "source fingerprint")
        _require_hex(self.adapter_digest, 64, "adapter digest")
        if self.source_run_hash != self.source_identity_sha256[:20]:
            raise ValueError("source run hash must be the identity digest prefix")
        if not self.adapter_identity:
            raise ValueError("adapter identity must not be empty")


def seal_projection(
    *,
    schema: str,
    source_run: OntologyRef,
    objects: tuple[OntologyObject, ...],
    relations: tuple[RelationAssertion, ...],
    measurements: tuple[Measurement, ...],
    coverage: tuple[CoverageEntry, ...],
) -> OntologyProjection:
    """Construct an immutable projection with its canonical semantic digest."""

    provisional = OntologyProjection(
        schema=schema,
        source_run=source_run,
        objects=objects,
        relations=relations,
        measurements=measurements,
        coverage=coverage,
        projection_digest="0" * 64,
    )
    return OntologyProjection(
        schema=provisional.schema,
        source_run=provisional.source_run,
        objects=provisional.objects,
        relations=provisional.relations,
        measurements=provisional.measurements,
        coverage=provisional.coverage,
        projection_digest=compute_projection_digest(provisional),
    )


def _projection_payload(projection: OntologyProjection) -> dict[str, Any]:
    return {
        "record_type": "ontology_projection_graph",
        "artifact_schema": projection.schema,
        "source_run": ontology_ref_to_data(projection.source_run),
        "objects": [ontology_object_to_data(item) for item in projection.objects],
        "relations": [relation_assertion_to_data(item) for item in projection.relations],
        "measurements": [measurement_to_data(item) for item in projection.measurements],
        "projection_digest": projection.projection_digest,
    }


def _coverage_payload(projection: OntologyProjection) -> dict[str, Any]:
    return {
        "record_type": "ontology_coverage",
        "artifact_schema": projection.schema,
        "source_run": ontology_ref_to_data(projection.source_run),
        "entries": [coverage_entry_to_data(item) for item in projection.coverage],
        "projection_digest": projection.projection_digest,
    }


def _manifest(
    projection: OntologyProjection,
    provenance: ProjectionBundleProvenance,
    payloads: dict[str, dict[str, int | str]],
) -> dict[str, Any]:
    source_run = {
        "run_hash": provenance.source_run_hash,
        "identity_sha256": provenance.source_identity_sha256,
        "manifest_sha256": provenance.source_manifest_sha256,
        "bundle_sha256": provenance.source_bundle_sha256,
        "source_fingerprint": provenance.source_fingerprint,
    }
    adapter = {"identity": provenance.adapter_identity, "digest": provenance.adapter_digest}
    bundle_payload = {
        "artifact_schema": ONTOLOGY_ARTIFACT_SCHEMA,
        "source_run": source_run,
        "adapter": adapter,
        "projection_digest": projection.projection_digest,
        "payloads": payloads,
    }
    return {
        **bundle_payload,
        "integrity_level": "checksummed",
        "bundle_sha256": content_digest(bundle_payload),
    }


def _write_file(path: Path, data: dict[str, Any]) -> bytes:
    content = canonical_bytes(data)
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    return content


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _prepare_parent(parent: Path) -> None:
    parent.mkdir(parents=True, exist_ok=True)
    mode = parent.lstat().st_mode
    if parent.is_symlink() or not stat.S_ISDIR(mode):
        raise ProjectionVerificationError("projection output parent must be a real directory")


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=False))
    except ValueError:
        return False
    return True


def _remove_stage(stage: Path) -> None:
    if stage.is_symlink():
        stage.unlink()
    elif stage.exists():
        shutil.rmtree(stage)


def _existing_bundle(target: Path, staged_bundle_sha256: str) -> Path:
    try:
        existing = verify_projection_bundle(target)
    except ProjectionVerificationError as error:
        raise ProjectionVerificationError(
            f"projection collision at {target}: existing bundle is invalid: {error}"
        ) from error
    if existing.bundle_sha256 != staged_bundle_sha256:
        raise ProjectionVerificationError(
            f"projection collision at {target}: existing bundle has different content"
        )
    return target


def write_projection_bundle(
    target: Path,
    projection: OntologyProjection,
    provenance: ProjectionBundleProvenance,
    *,
    source_run_dir: Path | None = None,
) -> Path:
    """Stage, verify, and atomically publish a derived projection outside its source run."""

    selected_target = Path(target)
    if source_run_dir is not None and _inside(selected_target, Path(source_run_dir)):
        raise ProjectionVerificationError(
            "projection output must remain outside the sealed source run directory"
        )
    if projection.schema != ONTOLOGY_ARTIFACT_SCHEMA:
        raise ProjectionVerificationError("projection must use schema ewm.ontology.v1")
    if compute_projection_digest(projection) != projection.projection_digest:
        raise ProjectionVerificationError("projection digest is not self-consistent")
    try:
        assert_valid_projection(projection)
    except OntologyValidationError as error:
        raise ProjectionVerificationError(
            f"projection violates ontology schema: {error}"
        ) from error

    _prepare_parent(selected_target.parent)
    if selected_target.is_symlink():
        raise ProjectionVerificationError("projection output target must not be a symbolic link")
    stage = Path(
        tempfile.mkdtemp(
            prefix=f".{selected_target.name}.",
            suffix=".staging",
            dir=selected_target.parent,
        )
    )
    try:
        graph = _projection_payload(projection)
        coverage = _coverage_payload(projection)
        graph_bytes = _write_file(stage / "projection.json", graph)
        coverage_bytes = _write_file(stage / "coverage.json", coverage)
        payloads: dict[str, dict[str, int | str]] = {
            "projection.json": {
                "sha256": content_digest(graph),
                "size": len(graph_bytes),
            },
            "coverage.json": {
                "sha256": content_digest(coverage),
                "size": len(coverage_bytes),
            },
        }
        _write_file(stage / "manifest.json", _manifest(projection, provenance, payloads))
        _fsync_directory(stage)
        staged_report = verify_projection_bundle(stage)
        try:
            os.rename(stage, selected_target)
        except OSError:
            if not selected_target.exists() and not selected_target.is_symlink():
                raise
            return _existing_bundle(selected_target, staged_report.bundle_sha256)
        _fsync_directory(selected_target.parent)
        return selected_target
    finally:
        _remove_stage(stage)
