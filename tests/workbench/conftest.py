"""Validated in-memory workbench registry fixtures."""

from __future__ import annotations

import pytest

from ewm.ontology import (
    Measurement,
    OntologyObject,
    OntologyProjection,
    OntologyRef,
    RelationAssertion,
    SourceLocator,
)

_DIGEST = "a" * 64


def _source(side: str) -> SourceLocator:
    return SourceLocator(
        source_kind="verified_run",
        source_id=f"source-{side}",
        artifact_path="metrics.json",
        payload_digest=_DIGEST,
    )


def _projection(side: str) -> OntologyProjection:
    source = _source(side)
    seeds = [7, 8]
    run = OntologyObject(
        ref=OntologyRef(f"ewm:workbench:run:{side}", "run"),
        layer="runtime_occurrence",
        properties={
            "natural_key": f"run-{side}",
            "comparison": {
                "world_identity": "world:test:v1",
                "protocol_identity": "protocol:test:v1",
                "software_identity": "software:test:v1",
                "seeds": seeds,
                "pairing_method": "common_random_numbers",
                "intervention": {
                    "family": "policy",
                    "level": side,
                },
                "multiplicity": {
                    "method": "holm",
                    "alpha": 0.05,
                    "family": ["price"],
                },
            },
        },
        sources=(source,),
    )
    world = OntologyObject(
        ref=OntologyRef(f"ewm:workbench:world:{side}", "world"),
        layer="economic_declaration",
        properties={"natural_key": f"world-{side}"},
        sources=(source,),
    )
    evidence = OntologyObject(
        ref=OntologyRef(f"ewm:workbench:evidence:{side}", "evidence_artifact"),
        layer="research_evidence",
        properties={"evidence_classification": "verified_run_evidence"},
        sources=(source,),
    )
    claim = OntologyObject(
        ref=OntologyRef(f"ewm:workbench:claim:{side}", "claim"),
        layer="research_evidence",
        properties={"evidence_classification": "verified_run_evidence"},
        sources=(source,),
    )
    supports = RelationAssertion(
        ref=OntologyRef(f"ewm:workbench:relation:{side}", "relation_assertion"),
        relation_type="SUPPORTS",
        source=evidence.ref,
        target=claim.ref,
        properties={},
        sources=(source,),
    )
    measurement = Measurement(
        ref=OntologyRef(f"ewm:workbench:measurement:{side}", "measurement"),
        subject=world.ref,
        name=f"{side} displayed price",
        value=1.0 if side == "left" else 1.25,
        unit="index",
        status="observed",
        sample={
            "comparison": {
                "comparison_key": "price@paired-sample",
                "estimand_identity": "price",
                "sample_identity": "paired-sample-v1",
                "estimator_identity": "paired-mean-v1",
                "paired_seeds": seeds,
                "hypothesis_id": "price",
            }
        },
        uncertainty={"method": "paired-standard-error"},
        sources=(source,),
    )
    return OntologyProjection(
        schema="ewm.ontology.v1",
        source_run=run.ref,
        objects=(run, world, evidence, claim),
        relations=(supports,),
        measurements=(measurement,),
        coverage=(),
        projection_digest=("b" if side == "left" else "c") * 64,
    )


@pytest.fixture
def approved_registry():
    from ewm.workbench.api import ApprovedRun, ApprovedRunRegistry

    return ApprovedRunRegistry(
        (
            ApprovedRun(
                run_id="left",
                projection=_projection("left"),
                source_run_hash="1" * 20,
                profile_identity="ewm.test-profile.v1",
                integrity_level="checksummed",
            ),
            ApprovedRun(
                run_id="right",
                projection=_projection("right"),
                source_run_hash="2" * 20,
                profile_identity="ewm.test-profile.v1",
                integrity_level="checksummed",
            ),
        )
    )


@pytest.fixture
def security_policy():
    from ewm.workbench.security import SecurityPolicy

    return SecurityPolicy(
        session_token="test-session-token-with-sufficient-entropy",
        allowed_hosts=("127.0.0.1",),
        allowed_origins=("http://127.0.0.1:8123",),
        max_request_body_bytes=4_096,
    )


@pytest.fixture
def client(approved_registry, security_policy):
    from fastapi.testclient import TestClient

    from ewm.workbench.api import create_workbench_app

    app = create_workbench_app(approved_registry, security_policy)
    return TestClient(app, base_url="http://127.0.0.1:8123", raise_server_exceptions=False)


@pytest.fixture
def api_headers() -> dict[str, str]:
    return {
        "Host": "127.0.0.1:8123",
        "Origin": "http://127.0.0.1:8123",
        "X-EWM-Token": "test-session-token-with-sufficient-entropy",
    }
