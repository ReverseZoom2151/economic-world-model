"""Fail-closed compilation of verified run bundles into ontology projections."""

from __future__ import annotations

import json
import math
import stat
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np

from ewm.experiments import ArtifactVerificationError, VerificationReport, verify_run
from ewm.experiments.runs.verification import PAYLOAD_FILENAMES

from .identity import make_ontology_ref
from .model import (
    CoverageEntry,
    Measurement,
    OntologyObject,
    OntologyProjection,
    OntologyRef,
    RelationAssertion,
    SourceLocator,
)
from .profiles.base import (
    OntologyProfile,
    OntologyProfileContext,
    ProfileProjection,
    profile_digest,
)
from .projection import ProjectionBundleProvenance, seal_projection
from .schema import OntologyValidationError, assert_valid_projection


class ProjectionCompilationError(ValueError):
    """Raised when source evidence cannot authorize a usable ontology projection."""


@dataclass(frozen=True, slots=True)
class SourcePreflightLimits:
    """Read limits applied before opening or verifying an untrusted run bundle."""

    max_payload_bytes: int = 512 * 1024 * 1024
    max_event_lines: int = 1_000_000
    max_npz_member_bytes: int = 256 * 1024 * 1024
    max_npz_total_uncompressed_bytes: int = 1024 * 1024 * 1024
    max_npz_compression_ratio: float = 1_000.0

    def __post_init__(self) -> None:
        integer_limits = (
            self.max_payload_bytes,
            self.max_event_lines,
            self.max_npz_member_bytes,
            self.max_npz_total_uncompressed_bytes,
        )
        if any(isinstance(value, bool) or value < 1 for value in integer_limits):
            raise ValueError("source preflight integer limits must be positive")
        if (
            isinstance(self.max_npz_compression_ratio, bool)
            or not math.isfinite(self.max_npz_compression_ratio)
            or self.max_npz_compression_ratio <= 0.0
        ):
            raise ValueError("NPZ compression-ratio limit must be positive and finite")


@dataclass(frozen=True, slots=True)
class SourceInspection:
    """Read-only verification result that never implies projection eligibility for legacy input."""

    report: VerificationReport
    artifact_schema: str
    integrity_level: str
    compilable: bool


@dataclass(frozen=True, slots=True)
class ProjectionCompilation:
    """Verified projection plus provenance required for optional atomic publication."""

    projection: OntologyProjection
    provenance: ProjectionBundleProvenance
    source_report: VerificationReport
    adapter_identity: str
    source_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _GenericProjection:
    objects: tuple[OntologyObject, ...]
    relations: tuple[RelationAssertion, ...]
    measurements: tuple[Measurement, ...]
    coverage: tuple[CoverageEntry, ...]
    source_fields: tuple[str, ...]
    run_ref: OntologyRef


def _preflight_run(run_dir: Path, limits: SourcePreflightLimits) -> None:
    path = Path(run_dir)
    try:
        if path.is_symlink() or not path.is_dir():
            raise ProjectionCompilationError("run source must be a real directory")
        entries = tuple(path.iterdir())
    except OSError as error:
        raise ProjectionCompilationError(f"could not inspect run source: {error}") from error
    for entry in entries:
        try:
            mode = entry.lstat().st_mode
            size = entry.stat().st_size
        except OSError as error:
            raise ProjectionCompilationError(
                f"could not inspect source payload: {error}"
            ) from error
        if entry.is_symlink() or not stat.S_ISREG(mode):
            raise ProjectionCompilationError(
                f"source payload {entry.name!r} must be a regular file"
            )
        if size > limits.max_payload_bytes:
            raise ProjectionCompilationError(
                f"source payload size exceeds limit for {entry.name!r}"
            )

    events_path = path / "events.jsonl"
    if events_path.is_file():
        try:
            with events_path.open("rb") as handle:
                for line_count, _line in enumerate(handle, start=1):
                    if line_count > limits.max_event_lines:
                        raise ProjectionCompilationError("source event line count exceeds limit")
        except OSError as error:
            raise ProjectionCompilationError(f"could not preflight event lines: {error}") from error

    trace_path = path / "trace.npz"
    if trace_path.is_file():
        try:
            with zipfile.ZipFile(trace_path) as archive:
                total_uncompressed = 0
                for member in archive.infolist():
                    if member.file_size > limits.max_npz_member_bytes:
                        raise ProjectionCompilationError(
                            f"NPZ member {member.filename!r} exceeds size limit"
                        )
                    total_uncompressed += member.file_size
                    if total_uncompressed > limits.max_npz_total_uncompressed_bytes:
                        raise ProjectionCompilationError(
                            "NPZ members exceed total uncompressed size limit"
                        )
                    ratio = member.file_size / max(member.compress_size, 1)
                    if ratio > limits.max_npz_compression_ratio:
                        raise ProjectionCompilationError(
                            f"NPZ member {member.filename!r} exceeds compression ratio limit"
                        )
        except ProjectionCompilationError:
            raise
        except (OSError, zipfile.BadZipFile) as error:
            raise ProjectionCompilationError(f"could not preflight NPZ archive: {error}") from error


def inspect_run_bundle(
    run_dir: Path,
    *,
    limits: SourcePreflightLimits | None = None,
) -> SourceInspection:
    """Preflight and verify a run without claiming legacy input is projectable."""

    selected_limits = limits or SourcePreflightLimits()
    _preflight_run(Path(run_dir), selected_limits)
    try:
        report = verify_run(Path(run_dir))
    except ArtifactVerificationError as error:
        raise ProjectionCompilationError(f"source verification failed: {error}") from error
    compilable = report.artifact_schema == "ewm.run.v2" and report.integrity_level == "checksummed"
    return SourceInspection(
        report=report,
        artifact_schema=report.artifact_schema,
        integrity_level=report.integrity_level,
        compilable=compilable,
    )


def _json_mapping(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProjectionCompilationError(
            f"verified source {path.name} could not be read"
        ) from error
    if not isinstance(value, Mapping):
        raise ProjectionCompilationError(f"verified source {path.name} must contain an object")
    return cast(Mapping[str, Any], value)


def _events(path: Path) -> tuple[Mapping[str, Any], ...]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        values = tuple(json.loads(line) for line in lines)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProjectionCompilationError("verified events could not be read") from error
    if not all(isinstance(value, Mapping) for value in values):
        raise ProjectionCompilationError("verified events must contain objects")
    return cast(tuple[Mapping[str, Any], ...], values)


def _traces(path: Path) -> Mapping[str, Any]:
    try:
        with np.load(path, allow_pickle=False) as arrays:
            return {name: np.array(arrays[name], copy=True) for name in arrays.files}
    except (OSError, ValueError) as error:
        raise ProjectionCompilationError("verified traces could not be read") from error


def _validate_profile(profile: OntologyProfile) -> None:
    if not profile.identity:
        raise ProjectionCompilationError("adapter identity must not be empty")
    if not profile.experiment_ids or not profile.package_versions or not profile.artifact_schemas:
        raise ProjectionCompilationError("adapter compatibility declarations must not be empty")
    digest = profile.source_digest
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ProjectionCompilationError("adapter source digest must be lowercase SHA-256")


def _select_profile(
    adapters: Sequence[OntologyProfile],
    *,
    artifact_schema: str,
    experiment: str,
    package_version: str,
) -> OntologyProfile:
    for adapter in adapters:
        _validate_profile(adapter)
    identities = [adapter.identity for adapter in adapters]
    if len(identities) != len(set(identities)):
        raise ProjectionCompilationError("adapter identities must be unique")
    experiment_matches = tuple(
        adapter for adapter in adapters if experiment in adapter.experiment_ids
    )
    if not experiment_matches:
        raise ProjectionCompilationError(f"unknown experiment {experiment!r}")
    compatible = tuple(
        adapter
        for adapter in experiment_matches
        if artifact_schema in adapter.artifact_schemas
        and package_version in adapter.package_versions
    )
    if not compatible:
        raise ProjectionCompilationError(
            f"known experiment {experiment!r} has an incompatible adapter version"
        )
    if len(compatible) != 1:
        raise ProjectionCompilationError(
            f"experiment {experiment!r} has multiple compatible ontology adapters"
        )
    return compatible[0]


def _source_locator(
    report: VerificationReport,
    *,
    filename: str,
    selector: str | None = None,
) -> SourceLocator:
    if report.identity_sha256 is None:
        raise ProjectionCompilationError("legacy source has no sealed identity")
    if filename == "manifest.json":
        digest = report.manifest_sha256
    else:
        digest = str(report.payloads[filename]["sha256"])
    return SourceLocator(
        source_kind="verified_run",
        source_id=report.identity_sha256,
        artifact_path=f"run/{filename}",
        record_selector=selector,
        payload_digest=digest,
    )


def _record_ref(
    report: VerificationReport,
    namespace: str,
    kind: str,
    semantic_keys: Any,
) -> OntologyRef:
    if report.identity_sha256 is None:
        raise ProjectionCompilationError("legacy source has no sealed identity")
    return make_ontology_ref(
        namespace=namespace,
        kind=kind,
        source_identity=report.identity_sha256,
        semantic_keys=semantic_keys,
    )


def _relation(
    report: VerificationReport,
    *,
    relation_type: str,
    source: OntologyRef,
    target: OntologyRef,
    ordinal: int,
    locator: SourceLocator,
) -> RelationAssertion:
    ref = _record_ref(
        report,
        "relation",
        "relation_assertion",
        {
            "relation_type": relation_type,
            "source": source.id,
            "target": target.id,
            "ordinal": ordinal,
        },
    )
    return RelationAssertion(
        ref=ref,
        relation_type=relation_type,
        source=source,
        target=target,
        properties={},
        sources=(locator,),
    )


def _nested_fields(prefix: str, value: Any) -> tuple[str, ...]:
    fields: list[str] = []
    if isinstance(value, Mapping):
        for key, item in sorted(value.items(), key=lambda pair: str(pair[0])):
            child = f"{prefix}.{key}"
            fields.append(child)
            fields.extend(_nested_fields(child, item))
    elif isinstance(value, list | tuple):
        for index, item in enumerate(value):
            child = f"{prefix}[{index}]"
            fields.append(child)
            fields.extend(_nested_fields(child, item))
    return tuple(fields)


def _generic_projection(
    report: VerificationReport,
    manifest: Mapping[str, Any],
    config: Mapping[str, Any],
    metrics: Mapping[str, Any],
    events: tuple[Mapping[str, Any], ...],
    traces: Mapping[str, Any],
) -> _GenericProjection:
    manifest_source = _source_locator(report, filename="manifest.json", selector="manifest")
    run_ref = _record_ref(report, "runtime", "run", {"run_hash": report.run_hash})
    boolean_metrics = {
        name: value for name, value in metrics.items() if isinstance(value, bool)
    }
    run = OntologyObject(
        ref=run_ref,
        layer="runtime_occurrence",
        properties={
            "run_hash": report.run_hash,
            "identity_sha256": report.identity_sha256,
            "experiment": manifest["experiment"],
            "scenario": manifest["scenario"],
            "preset": manifest["preset"],
            "seed": manifest["seed"],
            "package_version": manifest["package_version"],
            "parameters": config["parameters"],
            "metadata": config["metadata"],
            "runtime_environment": manifest["runtime_environment"],
            "source_fingerprint": manifest["source_fingerprint"],
            "boolean_metrics": boolean_metrics,
        },
        sources=(manifest_source,),
    )
    objects: list[OntologyObject] = [run]
    relations: list[RelationAssertion] = []
    measurements: list[Measurement] = []
    coverage: list[CoverageEntry] = []
    source_fields: set[str] = set()
    payload_refs: dict[str, OntologyRef] = {}

    def add_coverage(
        field: str,
        target: OntologyRef,
        locator: SourceLocator,
    ) -> None:
        if field in source_fields:
            raise ProjectionCompilationError(f"source coverage field {field!r} is duplicated")
        source_fields.add(field)
        coverage.append(
            CoverageEntry(
                source=locator,
                field=field,
                status="projected",
                targets=(target,),
                reason=None,
            )
        )

    filenames = ("manifest.json", *PAYLOAD_FILENAMES)
    for ordinal, filename in enumerate(filenames):
        locator = _source_locator(report, filename=filename, selector="payload")
        payload_ref = _record_ref(
            report,
            "evidence",
            "evidence_artifact",
            {"filename": filename},
        )
        payload_refs[filename] = payload_ref
        size = (
            report.manifest_size
            if filename == "manifest.json"
            else int(report.payloads[filename]["size"])
        )
        digest = (
            report.manifest_sha256
            if filename == "manifest.json"
            else str(report.payloads[filename]["sha256"])
        )
        objects.append(
            OntologyObject(
                ref=payload_ref,
                layer="research_evidence",
                properties={
                    "filename": filename,
                    "size": size,
                    "sha256": digest,
                    "evidence_origin": "verified_run",
                },
                sources=(locator,),
            )
        )
        relations.append(
            _relation(
                report,
                relation_type="CONTAINS",
                source=run_ref,
                target=payload_ref,
                ordinal=ordinal,
                locator=manifest_source,
            )
        )
        add_coverage(filename, payload_ref, locator)

    for filename, data in (("manifest.json", manifest), ("config.json", config)):
        for key in sorted(data):
            field = f"{filename}.{key}"
            add_coverage(
                field,
                run_ref,
                _source_locator(report, filename=filename, selector=key),
            )
            for nested_field in _nested_fields(field, data[key]):
                add_coverage(
                    nested_field,
                    run_ref,
                    _source_locator(
                        report,
                        filename=filename,
                        selector=nested_field.removeprefix(f"{filename}."),
                    ),
                )

    metrics_source = _source_locator(report, filename="metrics.json")
    for name, value in sorted(metrics.items()):
        field = f"metrics.json.{name}"
        locator = _source_locator(report, filename="metrics.json", selector=name)
        if isinstance(value, bool):
            add_coverage(field, run_ref, locator)
            continue
        measurement_ref = _record_ref(
            report,
            "evidence",
            "measurement",
            {"metric": name},
        )
        measurement = Measurement(
            ref=measurement_ref,
            subject=run_ref,
            name=name,
            value=value,
            unit="1",
            status="observed",
            sample={"count": 1},
            uncertainty={},
            sources=(metrics_source,),
        )
        measurements.append(measurement)
        add_coverage(field, measurement_ref, locator)

    previous_step: OntologyRef | None = None
    for sequence, event in enumerate(events):
        locator = _source_locator(
            report,
            filename="events.jsonl",
            selector=f"sequence={sequence}",
        )
        step_ref = _record_ref(report, "runtime", "step", {"sequence": sequence})
        objects.append(
            OntologyObject(
                ref=step_ref,
                layer="runtime_occurrence",
                properties={"sequence": sequence, "event": event},
                sources=(locator,),
            )
        )
        relations.append(
            _relation(
                report,
                relation_type="CONTAINS",
                source=run_ref,
                target=step_ref,
                ordinal=sequence,
                locator=locator,
            )
        )
        if previous_step is not None:
            relations.append(
                _relation(
                    report,
                    relation_type="PRECEDES",
                    source=previous_step,
                    target=step_ref,
                    ordinal=sequence,
                    locator=locator,
                )
            )
        previous_step = step_ref
        line_field = f"events.jsonl[{sequence}]"
        add_coverage(line_field, step_ref, locator)
        for key in sorted(event):
            event_field = f"{line_field}.{key}"
            add_coverage(event_field, step_ref, locator)
            for nested_field in _nested_fields(event_field, event[key]):
                add_coverage(nested_field, step_ref, locator)

    trace_payload_ref = payload_refs["trace.npz"]
    for ordinal, (name, raw_value) in enumerate(sorted(traces.items())):
        value = np.asarray(raw_value)
        member = f"{name}.npy"
        locator = _source_locator(report, filename="trace.npz", selector=member)
        member_ref = _record_ref(
            report,
            "evidence",
            "evidence_artifact",
            {"filename": "trace.npz", "member": member},
        )
        objects.append(
            OntologyObject(
                ref=member_ref,
                layer="research_evidence",
                properties={
                    "filename": "trace.npz",
                    "member": member,
                    "shape": tuple(int(size) for size in value.shape),
                    "dtype": str(value.dtype),
                    "values": value.tolist(),
                    "evidence_origin": "verified_run",
                },
                sources=(locator,),
            )
        )
        relations.append(
            _relation(
                report,
                relation_type="CONTAINS",
                source=trace_payload_ref,
                target=member_ref,
                ordinal=ordinal,
                locator=locator,
            )
        )
        add_coverage(f"trace.npz.{member}", member_ref, locator)

    software_ref = _record_ref(
        report,
        "provenance",
        "software_identity",
        {
            "package_version": manifest["package_version"],
            "runtime_environment": manifest["runtime_environment"],
        },
    )
    digest_ref = _record_ref(
        report,
        "provenance",
        "digest",
        {"bundle_sha256": report.bundle_sha256},
    )
    objects.extend(
        (
            OntologyObject(
                ref=software_ref,
                layer="provenance",
                properties={
                    "package_version": manifest["package_version"],
                    "runtime_environment": manifest["runtime_environment"],
                },
                sources=(manifest_source,),
            ),
            OntologyObject(
                ref=digest_ref,
                layer="provenance",
                properties={
                    "identity_sha256": report.identity_sha256,
                    "bundle_sha256": report.bundle_sha256,
                    "manifest_sha256": report.manifest_sha256,
                },
                sources=(manifest_source,),
            ),
        )
    )

    return _GenericProjection(
        objects=tuple(objects),
        relations=tuple(relations),
        measurements=tuple(measurements),
        coverage=tuple(coverage),
        source_fields=tuple(sorted(source_fields)),
        run_ref=run_ref,
    )


def _validate_profile_projection(
    fragment: ProfileProjection,
    context: OntologyProfileContext,
    source_fields: tuple[str, ...],
    generic_coverage: tuple[CoverageEntry, ...],
) -> None:
    for ontology_object in fragment.objects:
        if (
            ontology_object.ref.kind in {"claim", "evidence_artifact"}
            and ontology_object.properties.get("profile_evidence") is True
        ):
            classification = ontology_object.properties.get("evidence_classification")
            if not isinstance(classification, str) or not classification.strip():
                raise ProjectionCompilationError(
                    "profile claims and evidence require an explicit evidence classification"
                )
        if ontology_object.ref.kind == "readiness_assessment":
            classification = ontology_object.properties.get("classification")
            official_awards = ontology_object.properties.get("official_awards")
            level = ontology_object.properties.get("level")
            blocked = ontology_object.properties.get("blocked")
            awards_are_zero = (
                isinstance(official_awards, int)
                and not isinstance(official_awards, bool)
                and official_awards == 0
            )
            if (
                classification != "evidence_readiness_only"
                or not awards_are_zero
                or (level in {"L3", "L4", "L5", "L6"} and blocked is not True)
            ):
                raise ProjectionCompilationError(
                    "ontology adapters cannot award Han L3-L6 capability"
                )
        if ontology_object.layer != "economic_declaration":
            continue
        if ontology_object.properties.get("evidence_origin") != "adapter_derived":
            raise ProjectionCompilationError(
                "adapter-derived declarations must be labeled 'adapter_derived'"
            )
        if context.adapter_source not in ontology_object.sources:
            raise ProjectionCompilationError(
                "adapter-derived declarations must retain the source-digested adapter locator"
            )
    fields = [entry.field for entry in (*generic_coverage, *fragment.coverage)]
    if len(fields) != len(set(fields)):
        raise ProjectionCompilationError("projection coverage fields must be unique")
    by_field = {entry.field: entry for entry in generic_coverage}
    missing = set(source_fields) - by_field.keys()
    invalid = {
        field
        for field in source_fields
        if by_field[field].status not in {"projected", "omitted", "rejected"}
    }
    if missing or invalid:
        raise ProjectionCompilationError(
            f"source coverage is incomplete: missing={sorted(missing)}, invalid={sorted(invalid)}"
        )


def compile_run_projection(
    run_dir: Path,
    *,
    adapters: Sequence[OntologyProfile],
    limits: SourcePreflightLimits | None = None,
) -> ProjectionCompilation:
    """Project one compatible sealed run after bounded preflight and full verification."""

    inspection = inspect_run_bundle(run_dir, limits=limits)
    report = inspection.report
    if not inspection.compilable:
        raise ProjectionCompilationError(
            "legacy unsealed runs are diagnostic-only and cannot produce a verified projection"
        )
    if report.identity_sha256 is None or report.bundle_sha256 is None:
        raise ProjectionCompilationError("sealed source is missing required identity digests")

    path = Path(run_dir)
    manifest = _json_mapping(path / "manifest.json")
    config = _json_mapping(path / "config.json")
    metrics = _json_mapping(path / "metrics.json")
    events = _events(path / "events.jsonl")
    traces = _traces(path / "trace.npz")
    experiment = str(manifest["experiment"])
    package_version = str(manifest["package_version"])
    adapter = _select_profile(
        adapters,
        artifact_schema=report.artifact_schema,
        experiment=experiment,
        package_version=package_version,
    )
    generic = _generic_projection(report, manifest, config, metrics, events, traces)
    adapter_source = SourceLocator(
        source_kind="scenario_adapter",
        source_id=adapter.identity,
        code_symbol=f"{type(adapter).__module__}.{type(adapter).__qualname__}",
        payload_digest=adapter.source_digest,
    )
    payload_digests = {
        name: str(metadata["sha256"])
        for name, metadata in report.payloads.items()
    }
    payload_digests["manifest.json"] = report.manifest_sha256
    context = OntologyProfileContext(
        artifact_schema=report.artifact_schema,
        experiment=experiment,
        package_version=package_version,
        scenario=str(manifest["scenario"]),
        preset=str(manifest["preset"]),
        seed=int(manifest["seed"]),
        run_ref=generic.run_ref,
        manifest=manifest,
        config=config,
        metrics=metrics,
        events=events,
        traces=traces,
        payload_digests=payload_digests,
        run_source=_source_locator(report, filename="manifest.json", selector="manifest"),
        adapter_source=adapter_source,
    )
    try:
        fragment = adapter.project(context)
    except Exception as error:
        raise ProjectionCompilationError(f"ontology adapter failed: {error}") from error
    if not isinstance(fragment, ProfileProjection):
        raise ProjectionCompilationError("ontology adapter returned an invalid projection fragment")
    _validate_profile_projection(
        fragment,
        context,
        generic.source_fields,
        generic.coverage,
    )
    coverage = tuple(sorted((*generic.coverage, *fragment.coverage), key=lambda item: item.field))
    projection = seal_projection(
        schema="ewm.ontology.v1",
        source_run=generic.run_ref,
        objects=(*generic.objects, *fragment.objects),
        relations=(*generic.relations, *fragment.relations),
        measurements=(*generic.measurements, *fragment.measurements),
        coverage=coverage,
    )
    try:
        assert_valid_projection(projection)
    except OntologyValidationError as error:
        raise ProjectionCompilationError(f"compiled ontology is invalid: {error}") from error

    source_fingerprint = str(manifest["source_fingerprint"])
    provenance = ProjectionBundleProvenance(
        source_run_hash=report.run_hash,
        source_identity_sha256=report.identity_sha256,
        source_manifest_sha256=report.manifest_sha256,
        source_bundle_sha256=report.bundle_sha256,
        source_fingerprint=source_fingerprint,
        adapter_identity=adapter.identity,
        adapter_digest=profile_digest(adapter),
    )
    return ProjectionCompilation(
        projection=projection,
        provenance=provenance,
        source_report=report,
        adapter_identity=adapter.identity,
        source_fields=generic.source_fields,
    )
