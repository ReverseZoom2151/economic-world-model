"""Scientific comparability contracts for ontology projections."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from ewm.ontology import (
    Measurement,
    OntologyObject,
    OntologyProjection,
    OntologyRef,
    SourceLocator,
)
from ewm.ontology.comparison import compare_projections

_DIGEST = "a" * 64


def _source(side: str) -> SourceLocator:
    return SourceLocator(
        source_kind="verified_run",
        source_id=f"run-{side}",
        artifact_path="runs/metrics.json",
        record_selector="metric",
        payload_digest=_DIGEST,
    )


def _run_metadata(side: str) -> dict[str, object]:
    return {
        "world_identity": "world:credit:v1",
        "protocol_identity": "protocol:paired:v1",
        "software_identity": "sha256:source-v1",
        "seeds": [11, 12, 13],
        "pairing_method": "common_random_numbers",
        "intervention": {
            "family": "credit-information-policy",
            "level": "baseline" if side == "left" else "selective",
        },
        "multiplicity": {
            "method": "holm",
            "alpha": 0.05,
            "family": ["approval-rate", "profit-per-applicant"],
        },
    }


def _measurement_metadata() -> dict[str, object]:
    return {
        "comparison_key": "approval-rate@locked-sample",
        "estimand_identity": "approval-rate",
        "sample_identity": "locked-synthetic-population-v1",
        "estimator_identity": "paired-mean-difference-v1",
        "paired_seeds": [11, 12, 13],
        "hypothesis_id": "approval-rate",
    }


def _projection(
    side: str,
    *,
    run_overrides: Mapping[str, object] | None = None,
    measurement_overrides: Mapping[str, object] | None = None,
    unit: str = "percentage_point",
    schema: str = "ewm.ontology.v1",
    extra_measurements: tuple[Measurement, ...] = (),
) -> OntologyProjection:
    run_metadata = _run_metadata(side)
    run_metadata.update(run_overrides or {})
    run = OntologyObject(
        ref=OntologyRef(f"ewm:test:run:{side}", "run"),
        layer="runtime_occurrence",
        properties={"natural_key": f"run-{side}", "comparison": run_metadata},
        sources=(_source(side),),
    )
    world = OntologyObject(
        ref=OntologyRef(f"ewm:test:world:{side}", "world"),
        layer="economic_declaration",
        properties={"natural_key": f"world-{side}"},
        sources=(_source(side),),
    )
    measurement_metadata = _measurement_metadata()
    measurement_metadata.update(measurement_overrides or {})
    measurement = Measurement(
        ref=OntologyRef(f"ewm:test:measurement:{side}:approval", "measurement"),
        subject=world.ref,
        name="Observed approval" if side == "left" else "Modeled approvals",
        value=0.41 if side == "left" else 0.46,
        unit=unit,
        status="observed",
        sample={"comparison": measurement_metadata},
        uncertainty={"standard_error": 0.02},
        sources=(_source(side),),
    )
    return OntologyProjection(
        schema=schema,
        source_run=run.ref,
        objects=(world, run),
        relations=(),
        measurements=(measurement, *extra_measurements),
        coverage=(),
        projection_digest=("b" if side == "left" else "c") * 64,
    )


def test_explicit_semantic_key_aligns_different_labels_and_preserves_design() -> None:
    result = compare_projections(_projection("left"), _projection("right"))

    assert result.preflight.compatible is True
    assert result.preflight.issues == ()
    assert tuple(entry.comparison_key for entry in result.plan.entries) == (
        "approval-rate@locked-sample",
    )
    assert len(result.aligned) == 1
    aligned = result.aligned[0]
    assert aligned.estimand_identity == "approval-rate"
    assert aligned.left_value == 0.41
    assert aligned.right_value == 0.46
    assert aligned.unit == "percentage_point"
    assert aligned.pairing.method == "common_random_numbers"
    assert aligned.pairing.seeds == (11, 12, 13)
    assert aligned.multiplicity.method == "holm"
    assert aligned.multiplicity.family == (
        "approval-rate",
        "profit-per-applicant",
    )
    assert aligned.left_intervention.level == "baseline"
    assert aligned.right_intervention.level == "selective"
    assert result.unaligned == ()


@pytest.mark.parametrize(
    ("run_overrides", "schema", "expected_code"),
    (
        ({"world_identity": "world:other"}, "ewm.ontology.v1", "world_identity_mismatch"),
        (
            {"protocol_identity": "protocol:other"},
            "ewm.ontology.v1",
            "protocol_identity_mismatch",
        ),
        ({"seeds": [11, 14]}, "ewm.ontology.v1", "paired_seed_mismatch"),
        ({"pairing_method": "independent"}, "ewm.ontology.v1", "pairing_method_mismatch"),
        (
            {"software_identity": "sha256:source-v2"},
            "ewm.ontology.v1",
            "software_identity_mismatch",
        ),
        (
            {"intervention": {"family": "tax-policy", "level": "selective"}},
            "ewm.ontology.v1",
            "intervention_family_mismatch",
        ),
        (
            {
                "multiplicity": {
                    "method": "none",
                    "alpha": 0.05,
                    "family": ["approval-rate", "profit-per-applicant"],
                }
            },
            "ewm.ontology.v1",
            "multiplicity_mismatch",
        ),
        ({}, "ewm.ontology.v2", "ontology_schema_mismatch"),
    ),
)
def test_run_level_incompatibility_blocks_every_aligned_value(
    run_overrides: Mapping[str, object],
    schema: str,
    expected_code: str,
) -> None:
    result = compare_projections(
        _projection("left"),
        _projection("right", run_overrides=run_overrides, schema=schema),
    )

    assert result.preflight.compatible is False
    assert expected_code in {issue.code for issue in result.preflight.issues}
    assert result.plan.entries == ()
    assert result.aligned == ()
    assert {record.reason_code for record in result.unaligned} == {"preflight_failed"}


@pytest.mark.parametrize(
    ("measurement_overrides", "unit", "expected_code"),
    (
        ({"estimand_identity": "default-rate"}, "percentage_point", "estimand_mismatch"),
        ({"sample_identity": "other-sample"}, "percentage_point", "sample_mismatch"),
        ({"estimator_identity": "median-v1"}, "percentage_point", "estimator_mismatch"),
        ({"paired_seeds": [11, 12]}, "percentage_point", "measurement_seed_mismatch"),
        ({"hypothesis_id": "profit-per-applicant"}, "percentage_point", "hypothesis_mismatch"),
        ({}, "fraction", "unit_mismatch"),
    ),
)
def test_measurement_incompatibility_is_explicit_and_never_coerced(
    measurement_overrides: Mapping[str, object],
    unit: str,
    expected_code: str,
) -> None:
    result = compare_projections(
        _projection("left"),
        _projection(
            "right",
            measurement_overrides=measurement_overrides,
            unit=unit,
        ),
    )

    assert result.preflight.compatible is True
    assert expected_code in {issue.code for issue in result.preflight.issues}
    assert result.plan.entries == ()
    assert result.aligned == ()
    assert len(result.unaligned) == 2


def test_missing_and_duplicate_explicit_keys_remain_unaligned() -> None:
    duplicate = Measurement(
        ref=OntologyRef("ewm:test:measurement:right:duplicate", "measurement"),
        subject=OntologyRef("ewm:test:world:right", "world"),
        name="Another display label",
        value=0.5,
        unit="percentage_point",
        status="observed",
        sample={"comparison": _measurement_metadata()},
        uncertainty={},
        sources=(_source("right"),),
    )
    result = compare_projections(
        _projection("left"),
        _projection("right", extra_measurements=(duplicate,)),
    )

    assert "duplicate_comparison_key" in {issue.code for issue in result.preflight.issues}
    assert result.aligned == ()
    assert tuple(record.measurement_id for record in result.unaligned) == (
        "ewm:test:measurement:left:approval",
        "ewm:test:measurement:right:approval",
        "ewm:test:measurement:right:duplicate",
    )


def test_missing_comparison_metadata_is_reported_not_inferred_from_name() -> None:
    result = compare_projections(
        _projection("left"),
        _projection("right", measurement_overrides={"comparison_key": ""}),
    )

    assert "invalid_measurement_metadata" in {
        issue.code for issue in result.preflight.issues
    }
    assert result.aligned == ()
    assert {record.reason_code for record in result.unaligned} == {
        "missing_counterpart",
        "invalid_measurement_metadata",
    }
