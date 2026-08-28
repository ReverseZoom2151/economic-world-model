from __future__ import annotations

from ewm.ontology.compiler import ProjectionCompilation


def test_credit_profile_preserves_regimes_and_locked_diagnostics(
    credit_projection: ProjectionCompilation,
) -> None:
    projection = credit_projection.projection
    regimes = tuple(
        obj
        for obj in projection.objects
        if obj.ref.kind == "outcome" and obj.properties.get("outcome_kind") == "credit_regime"
    )
    candidates = tuple(obj for obj in projection.objects if obj.ref.kind == "ddge_candidate")
    limitations = tuple(obj for obj in projection.objects if obj.ref.kind == "limitation")

    assert {item.properties["regime"] for item in regimes} == {
        "no_genai",
        "frozen",
        "selective_ddge",
        "full_information_ddge",
        "omniscient_oracle",
    }
    assert {item.properties["regime"] for item in candidates} == {
        "selective_ddge",
        "full_information_ddge",
    }
    assert any(
        "sampling noise floor" in str(item.properties["description"])
        for item in limitations
    )
    selective = next(item for item in candidates if item.properties["regime"] == "selective_ddge")
    assert selective.properties["status"] == "residual_qualified"
    assert selective.sources[0].record_selector == "sequence=2"


def test_credit_profile_does_not_promote_qualitative_reconstruction(
    credit_projection: ProjectionCompilation,
) -> None:
    projection = credit_projection.projection
    evidence = tuple(
        obj
        for obj in projection.objects
        if obj.ref.kind == "evidence_artifact"
        and obj.properties.get("profile_evidence") is True
    )
    gaps = {entry.field: entry for entry in projection.coverage}

    assert {item.properties["evidence_classification"] for item in evidence} == {
        "qualitative-reconstruction"
    }
    assert gaps["adapter.credit.exact_replication"].status == "rejected"
    assert gaps["adapter.credit.sampling_noise_floor"].status == "unavailable"
