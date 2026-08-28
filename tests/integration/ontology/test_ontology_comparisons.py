"""End-to-end comparison preflight and partial alignment workflow."""

from __future__ import annotations

from ewm.ontology import (
    Measurement,
    OntologyObject,
    OntologyProjection,
    OntologyRef,
    SourceLocator,
)
from ewm.ontology.comparison import compare_projections

_DIGEST = "d" * 64


def _projection(side: str) -> OntologyProjection:
    source = SourceLocator(
        source_kind="verified_run",
        source_id=f"integration-{side}",
        payload_digest=_DIGEST,
    )
    run = OntologyObject(
        ref=OntologyRef(f"ewm:integration:run:{side}", "run"),
        layer="runtime_occurrence",
        properties={
            "natural_key": f"integration-{side}",
            "comparison": {
                "world_identity": "world:fx:v1",
                "protocol_identity": "protocol:fx-paired:v1",
                "software_identity": "source:locked",
                "seeds": [42, 43],
                "pairing_method": "common_random_numbers",
                "intervention": {
                    "family": "firm-demand-shock",
                    "level": "baseline" if side == "left" else "positive-shock",
                },
                "multiplicity": {
                    "method": "holm",
                    "alpha": 0.05,
                    "family": ["price", "volume"],
                },
            },
        },
        sources=(source,),
    )
    world = OntologyObject(
        ref=OntologyRef(f"ewm:integration:world:{side}", "world"),
        layer="economic_declaration",
        properties={"natural_key": f"world-{side}"},
        sources=(source,),
    )

    def measurement(
        key: str,
        value: float,
        unit: str,
        *,
        sample_identity: str = "paired-rollouts-v1",
    ) -> Measurement:
        return Measurement(
            ref=OntologyRef(f"ewm:integration:measurement:{side}:{key}", "measurement"),
            subject=world.ref,
            name=f"{side} display {key}",
            value=value,
            unit=unit,
            status="observed",
            sample={
                "comparison": {
                    "comparison_key": key,
                    "estimand_identity": key,
                    "sample_identity": sample_identity,
                    "estimator_identity": "paired-mean-v1",
                    "paired_seeds": [42, 43],
                    "hypothesis_id": key,
                }
            },
            uncertainty={"method": "paired-standard-error"},
            sources=(source,),
        )

    measurements = (
        measurement("price", 1.0 if side == "left" else 1.2, "index"),
        measurement("volume", 10.0 if side == "left" else 12.0, "units"),
    )
    if side == "right":
        measurements = (
            measurements[0],
            measurement("volume", 12.0, "lots"),
        )
    return OntologyProjection(
        schema="ewm.ontology.v1",
        source_run=run.ref,
        objects=(run, world),
        relations=(),
        measurements=measurements,
        coverage=(),
        projection_digest=("e" if side == "left" else "f") * 64,
    )


def test_preflight_allows_only_the_compatible_measurement_pair() -> None:
    result = compare_projections(_projection("left"), _projection("right"))

    assert result.preflight.compatible is True
    assert tuple(item.comparison_key for item in result.aligned) == ("price",)
    assert tuple(item.comparison_key for item in result.plan.entries) == ("price",)
    assert tuple(issue.code for issue in result.preflight.issues) == ("unit_mismatch",)
    assert tuple(item.measurement_id for item in result.unaligned) == (
        "ewm:integration:measurement:left:volume",
        "ewm:integration:measurement:right:volume",
    )
