"""Fail-closed scientific comparison of two validated ontology projections."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from math import isfinite
from typing import Any, Literal, TypeAlias, cast

from ewm.core.provenance.serialization import canonical_json

from ..graph.model import Measurement, OntologyObject, OntologyProjection
from ..graph.schema import assert_valid_projection
from .contracts import (
    AlignedMeasurement,
    AlignmentEntry,
    AlignmentPlan,
    ComparisonIssue,
    ComparisonPreflight,
    ComparisonResult,
    ComparisonSide,
    InterventionIdentity,
    MeasurementComparisonMetadata,
    MultiplicityMetadata,
    PairingMetadata,
    RunComparisonMetadata,
    UnalignedMeasurement,
)

_Comparable: TypeAlias = str | tuple[int, ...] | None


def _issue(
    code: str,
    scope: Literal["run", "measurement"],
    message: str,
    *,
    left: _Comparable,
    right: _Comparable,
    blocking: bool,
) -> ComparisonIssue:
    return ComparisonIssue(
        code=code,
        scope=scope,
        message=message,
        left=left,
        right=right,
        blocking=blocking,
    )


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")
    if not all(isinstance(key, str) for key in value):
        raise ValueError(f"{field} keys must be text")
    return cast(Mapping[str, Any], value)


def _seeds(value: object, field: str) -> tuple[int, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise ValueError(f"{field} must be a non-empty seed sequence")
    seeds = tuple(value)
    if not seeds or any(
        not isinstance(seed, int) or isinstance(seed, bool) or seed < 0 for seed in seeds
    ):
        raise ValueError(f"{field} must contain non-negative integer seeds")
    if len(set(seeds)) != len(seeds):
        raise ValueError(f"{field} must not contain duplicate seeds")
    return cast(tuple[int, ...], seeds)


def _text_sequence(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise ValueError(f"{field} must be a non-empty text sequence")
    values = tuple(value)
    if not values or any(not isinstance(item, str) or not item.strip() for item in values):
        raise ValueError(f"{field} must contain non-empty text")
    if len(set(values)) != len(values):
        raise ValueError(f"{field} must not contain duplicates")
    return cast(tuple[str, ...], values)


def _alpha(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("multiplicity alpha must be numeric")
    converted = float(value)
    if not isfinite(converted) or not 0.0 < converted < 1.0:
        raise ValueError("multiplicity alpha must lie in (0, 1)")
    return converted


def _source_run(projection: OntologyProjection) -> OntologyObject:
    matches = tuple(
        ontology_object
        for ontology_object in projection.objects
        if ontology_object.ref == projection.source_run
    )
    if len(matches) != 1:
        raise ValueError("projection must contain exactly one source-run object")
    return matches[0]


def _run_metadata(
    projection: OntologyProjection,
    side: ComparisonSide,
) -> tuple[RunComparisonMetadata | None, tuple[ComparisonIssue, ...]]:
    run = _source_run(projection)
    try:
        comparison = _mapping(run.properties.get("comparison"), "run comparison metadata")
        intervention_data = _mapping(comparison.get("intervention"), "intervention")
        intervention = InterventionIdentity(
            family=_text(intervention_data.get("family"), "intervention family"),
            level=_text(intervention_data.get("level"), "intervention level"),
        )
        pairing = PairingMetadata(
            method=_text(comparison.get("pairing_method"), "pairing method"),
            seeds=_seeds(comparison.get("seeds"), "paired seeds"),
        )
        multiplicity_data = _mapping(comparison.get("multiplicity"), "multiplicity")
        multiplicity = MultiplicityMetadata(
            method=_text(multiplicity_data.get("method"), "multiplicity method"),
            alpha=_alpha(multiplicity_data.get("alpha")),
            family=_text_sequence(multiplicity_data.get("family"), "multiplicity family"),
        )
        metadata = RunComparisonMetadata(
            run=run.ref,
            ontology_schema=projection.schema,
            world_identity=_text(comparison.get("world_identity"), "world identity"),
            protocol_identity=_text(comparison.get("protocol_identity"), "protocol identity"),
            software_identity=_text(comparison.get("software_identity"), "software identity"),
            intervention=intervention,
            pairing=pairing,
            multiplicity=multiplicity,
        )
    except (TypeError, ValueError) as error:
        issue = _issue(
            "invalid_run_comparison_metadata",
            "run",
            f"{side} run comparison metadata is invalid: {error}",
            left=str(error) if side == "left" else None,
            right=str(error) if side == "right" else None,
            blocking=True,
        )
        return None, (issue,)
    return metadata, ()


def _multiplicity_identity(value: MultiplicityMetadata) -> str:
    return canonical_json(
        {"method": value.method, "alpha": value.alpha, "family": value.family}
    )


def _run_issues(
    left: RunComparisonMetadata,
    right: RunComparisonMetadata,
) -> tuple[ComparisonIssue, ...]:
    issues: list[ComparisonIssue] = []

    def compare(code: str, label: str, left_value: _Comparable, right_value: _Comparable) -> None:
        if left_value != right_value:
            issues.append(
                _issue(
                    code,
                    "run",
                    f"{label} must match exactly before values can be aligned",
                    left=left_value,
                    right=right_value,
                    blocking=True,
                )
            )

    compare(
        "world_identity_mismatch",
        "world identity",
        left.world_identity,
        right.world_identity,
    )
    compare(
        "protocol_identity_mismatch",
        "protocol identity",
        left.protocol_identity,
        right.protocol_identity,
    )
    compare(
        "ontology_schema_mismatch",
        "ontology schema",
        left.ontology_schema,
        right.ontology_schema,
    )
    compare(
        "paired_seed_mismatch",
        "paired seeds",
        left.pairing.seeds,
        right.pairing.seeds,
    )
    compare(
        "pairing_method_mismatch",
        "pairing method",
        left.pairing.method,
        right.pairing.method,
    )
    compare(
        "intervention_family_mismatch",
        "intervention family",
        left.intervention.family,
        right.intervention.family,
    )
    compare(
        "software_identity_mismatch",
        "software identity",
        left.software_identity,
        right.software_identity,
    )
    compare(
        "multiplicity_mismatch",
        "multiplicity design",
        _multiplicity_identity(left.multiplicity),
        _multiplicity_identity(right.multiplicity),
    )
    return tuple(issues)


def _measurement_metadata(
    measurement: Measurement,
    run: RunComparisonMetadata,
    side: ComparisonSide,
) -> tuple[
    MeasurementComparisonMetadata | None,
    ComparisonIssue | None,
    UnalignedMeasurement | None,
]:
    comparison_key: str | None = None
    issue_code = "invalid_measurement_metadata"
    try:
        comparison = _mapping(
            measurement.sample.get("comparison"),
            "measurement comparison metadata",
        )
        comparison_key = _text(comparison.get("comparison_key"), "comparison key")
        paired_seeds = _seeds(comparison.get("paired_seeds"), "measurement paired seeds")
        if paired_seeds != run.pairing.seeds:
            issue_code = "measurement_seed_mismatch"
            raise ValueError("measurement paired seeds do not match the run pairing design")
        hypothesis_id = _text(comparison.get("hypothesis_id"), "hypothesis id")
        if hypothesis_id not in run.multiplicity.family:
            raise ValueError("hypothesis id is absent from the run multiplicity family")
        metadata = MeasurementComparisonMetadata(
            measurement=measurement.ref,
            comparison_key=comparison_key,
            estimand_identity=_text(
                comparison.get("estimand_identity"),
                "estimand identity",
            ),
            sample_identity=_text(comparison.get("sample_identity"), "sample identity"),
            estimator_identity=_text(
                comparison.get("estimator_identity"),
                "estimator identity",
            ),
            paired_seeds=paired_seeds,
            hypothesis_id=hypothesis_id,
        )
    except (TypeError, ValueError) as error:
        issue = _issue(
            issue_code,
            "measurement",
            f"{side} measurement {measurement.ref.id!r} is not alignable: {error}",
            left=str(error) if side == "left" else None,
            right=str(error) if side == "right" else None,
            blocking=False,
        )
        unaligned = UnalignedMeasurement(
            side=side,
            measurement_id=measurement.ref.id,
            comparison_key=comparison_key,
            reason_code=issue_code,
            reason=str(error),
        )
        return None, issue, unaligned
    return metadata, None, None


def _all_preflight_failed(
    left: OntologyProjection,
    right: OntologyProjection,
) -> tuple[UnalignedMeasurement, ...]:
    return tuple(
        sorted(
            (
                *(
                    UnalignedMeasurement(
                        "left",
                        measurement.ref.id,
                        None,
                        "preflight_failed",
                        "run-level comparison preflight failed",
                    )
                    for measurement in left.measurements
                ),
                *(
                    UnalignedMeasurement(
                        "right",
                        measurement.ref.id,
                        None,
                        "preflight_failed",
                        "run-level comparison preflight failed",
                    )
                    for measurement in right.measurements
                ),
            ),
            key=lambda item: (item.measurement_id, item.side),
        )
    )


def _pair_issue(
    code: str,
    label: str,
    left: str | tuple[int, ...],
    right: str | tuple[int, ...],
) -> ComparisonIssue:
    return _issue(
        code,
        "measurement",
        f"{label} must match exactly; no representation or unit coercion is permitted",
        left=left,
        right=right,
        blocking=False,
    )


def _pair_mismatch(
    left_metadata: MeasurementComparisonMetadata,
    right_metadata: MeasurementComparisonMetadata,
    left_measurement: Measurement,
    right_measurement: Measurement,
) -> ComparisonIssue | None:
    comparisons: tuple[tuple[str, str, str | tuple[int, ...], str | tuple[int, ...]], ...] = (
        (
            "estimand_mismatch",
            "estimand identity",
            left_metadata.estimand_identity,
            right_metadata.estimand_identity,
        ),
        ("unit_mismatch", "measurement unit", left_measurement.unit, right_measurement.unit),
        (
            "sample_mismatch",
            "sample identity",
            left_metadata.sample_identity,
            right_metadata.sample_identity,
        ),
        (
            "estimator_mismatch",
            "estimator identity",
            left_metadata.estimator_identity,
            right_metadata.estimator_identity,
        ),
        (
            "measurement_seed_mismatch",
            "measurement paired seeds",
            left_metadata.paired_seeds,
            right_metadata.paired_seeds,
        ),
        (
            "hypothesis_mismatch",
            "multiplicity hypothesis",
            left_metadata.hypothesis_id,
            right_metadata.hypothesis_id,
        ),
    )
    for code, label, left_value, right_value in comparisons:
        if left_value != right_value:
            return _pair_issue(code, label, left_value, right_value)
    return None


def _unaligned_pair(
    left: Measurement,
    right: Measurement,
    comparison_key: str,
    issue: ComparisonIssue,
) -> tuple[UnalignedMeasurement, UnalignedMeasurement]:
    return (
        UnalignedMeasurement(
            "left",
            left.ref.id,
            comparison_key,
            issue.code,
            issue.message,
        ),
        UnalignedMeasurement(
            "right",
            right.ref.id,
            comparison_key,
            issue.code,
            issue.message,
        ),
    )


def compare_projections(
    left_projection: OntologyProjection,
    right_projection: OntologyProjection,
) -> ComparisonResult:
    """Preflight and align two projections using explicit scientific identities only."""

    assert_valid_projection(left_projection)
    assert_valid_projection(right_projection)
    left_run, left_issues = _run_metadata(left_projection, "left")
    right_run, right_issues = _run_metadata(right_projection, "right")
    issues: list[ComparisonIssue] = [*left_issues, *right_issues]
    if left_run is not None and right_run is not None:
        issues.extend(_run_issues(left_run, right_run))
    compatible = left_run is not None and right_run is not None and not any(
        issue.blocking for issue in issues
    )
    preflight = ComparisonPreflight(
        compatible=compatible,
        issues=tuple(issues),
        left=left_run,
        right=right_run,
    )
    if not compatible or left_run is None or right_run is None:
        failed_records = _all_preflight_failed(left_projection, right_projection)
        return ComparisonResult(
            preflight=preflight,
            plan=AlignmentPlan((), tuple(item.measurement_id for item in failed_records)),
            aligned=(),
            unaligned=failed_records,
        )

    measurements = {
        measurement.ref.id: measurement
        for measurement in (*left_projection.measurements, *right_projection.measurements)
    }
    grouped: dict[
        ComparisonSide,
        defaultdict[str, list[MeasurementComparisonMetadata]],
    ] = {
        "left": defaultdict(list),
        "right": defaultdict(list),
    }
    unaligned_records: list[UnalignedMeasurement] = []
    comparison_sides: tuple[
        tuple[ComparisonSide, OntologyProjection, RunComparisonMetadata],
        ...,
    ] = (
        ("left", left_projection, left_run),
        ("right", right_projection, right_run),
    )
    for side, projection, run in comparison_sides:
        for measurement in sorted(projection.measurements, key=lambda item: item.ref.id):
            metadata, issue, unaligned = _measurement_metadata(measurement, run, side)
            if issue is not None:
                issues.append(issue)
            if unaligned is not None:
                unaligned_records.append(unaligned)
            if metadata is not None:
                grouped[side][metadata.comparison_key].append(metadata)

    entries: list[AlignmentEntry] = []
    aligned: list[AlignedMeasurement] = []
    keys = sorted(set(grouped["left"]) | set(grouped["right"]))
    for comparison_key in keys:
        left_candidates = grouped["left"].get(comparison_key, [])
        right_candidates = grouped["right"].get(comparison_key, [])
        if len(left_candidates) != 1 or len(right_candidates) != 1:
            if not left_candidates or not right_candidates:
                issue = _issue(
                    "missing_counterpart",
                    "measurement",
                    "an explicit comparison key exists on only one side",
                    left=comparison_key if left_candidates else None,
                    right=comparison_key if right_candidates else None,
                    blocking=False,
                )
            else:
                issue = _issue(
                    "duplicate_comparison_key",
                    "measurement",
                    "an explicit comparison key must identify exactly one measurement per side",
                    left=str(len(left_candidates)),
                    right=str(len(right_candidates)),
                    blocking=False,
                )
            issues.append(issue)
            candidate_groups: tuple[
                tuple[ComparisonSide, list[MeasurementComparisonMetadata]],
                ...,
            ] = (
                ("left", left_candidates),
                ("right", right_candidates),
            )
            for side, candidates in candidate_groups:
                unaligned_records.extend(
                    UnalignedMeasurement(
                        side,
                        candidate.measurement.id,
                        comparison_key,
                        issue.code,
                        issue.message,
                    )
                    for candidate in candidates
                )
            continue

        left_metadata = left_candidates[0]
        right_metadata = right_candidates[0]
        left_measurement = measurements[left_metadata.measurement.id]
        right_measurement = measurements[right_metadata.measurement.id]
        mismatch = _pair_mismatch(
            left_metadata,
            right_metadata,
            left_measurement,
            right_measurement,
        )
        if mismatch is not None:
            issues.append(mismatch)
            unaligned_records.extend(
                _unaligned_pair(
                    left_measurement,
                    right_measurement,
                    comparison_key,
                    mismatch,
                )
            )
            continue
        entries.append(
            AlignmentEntry(
                comparison_key,
                left_measurement.ref,
                right_measurement.ref,
            )
        )
        aligned.append(
            AlignedMeasurement(
                comparison_key=comparison_key,
                estimand_identity=left_metadata.estimand_identity,
                sample_identity=left_metadata.sample_identity,
                estimator_identity=left_metadata.estimator_identity,
                hypothesis_id=left_metadata.hypothesis_id,
                unit=left_measurement.unit,
                left_measurement=left_measurement.ref,
                right_measurement=right_measurement.ref,
                left_name=left_measurement.name,
                right_name=right_measurement.name,
                left_value=left_measurement.value,
                right_value=right_measurement.value,
                left_intervention=left_run.intervention,
                right_intervention=right_run.intervention,
                pairing=left_run.pairing,
                multiplicity=left_run.multiplicity,
            )
        )

    ordered_unaligned = tuple(
        sorted(
            unaligned_records,
            key=lambda item: (item.measurement_id, item.side, item.reason_code),
        )
    )
    final_preflight = ComparisonPreflight(
        compatible=True,
        issues=tuple(issues),
        left=left_run,
        right=right_run,
    )
    plan = AlignmentPlan(
        entries=tuple(sorted(entries, key=lambda item: item.comparison_key)),
        unaligned_measurement_ids=tuple(item.measurement_id for item in ordered_unaligned),
    )
    return ComparisonResult(
        preflight=final_preflight,
        plan=plan,
        aligned=tuple(sorted(aligned, key=lambda item: item.comparison_key)),
        unaligned=ordered_unaligned,
    )
