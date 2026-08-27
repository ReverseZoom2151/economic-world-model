from __future__ import annotations

from types import MappingProxyType

import pytest

from ewm.core import WorldComponent, content_digest
from ewm.core.interventions import (
    InterventionTarget,
    SetValueIntervention,
    apply_intervention,
)


def test_set_intervention_is_atomic_and_records_canonical_provenance() -> None:
    subject = {
        "transition": {"tax_rate": 0.1, "persistence": 0.9},
        "coherence": {"budget_tolerance": 0.0},
    }
    target = InterventionTarget(WorldComponent.TRANSITION, ("tax_rate",))
    intervention = SetValueIntervention(
        name="raise_tax",
        target=target,
        replacement=0.2,
        expected_before_sha256=content_digest(0.1),
    )

    application = apply_intervention(subject, intervention)

    assert subject["transition"]["tax_rate"] == 0.1
    assert application.subject["transition"]["tax_rate"] == 0.2
    assert isinstance(application.subject, MappingProxyType)
    assert application.record.name == "raise_tax"
    assert application.record.target == target
    assert application.record.before_sha256 == content_digest(subject)
    assert application.record.after_sha256 == content_digest(application.subject)
    assert application.record.before_sha256 != application.record.after_sha256
    assert application.record.target_before_sha256 == content_digest(0.1)
    assert application.record.target_after_sha256 == content_digest(0.2)
    assert application.record.diff.as_data() == {
        "op": "replace",
        "path": "/transition/tax_rate",
        "before": 0.1,
        "after": 0.2,
    }


def test_intervention_target_emits_escaped_json_pointer() -> None:
    target = InterventionTarget(
        WorldComponent.CONSTRAINTS,
        ("desk/a", "limit~hard"),
    )

    assert target.json_pointer == "/constraints/desk~1a/limit~0hard"


def test_intervention_rejects_missing_or_stale_targets_without_mutation() -> None:
    subject = {"transition": {"tax_rate": 0.1}}
    missing = SetValueIntervention(
        "missing",
        InterventionTarget(WorldComponent.TRANSITION, ("missing",)),
        0.2,
    )
    stale = SetValueIntervention(
        "stale",
        InterventionTarget(WorldComponent.TRANSITION, ("tax_rate",)),
        0.2,
        expected_before_sha256="0" * 64,
    )

    with pytest.raises(KeyError, match="does not exist"):
        apply_intervention(subject, missing)
    with pytest.raises(ValueError, match="precondition hash does not match"):
        apply_intervention(subject, stale)
    assert subject == {"transition": {"tax_rate": 0.1}}


def test_failed_compare_and_set_cannot_partially_mutate_nested_subject() -> None:
    subject = {
        "transition": {
            "regime": {"tax_rate": 0.1, "subsidy_rate": 0.02},
            "version": 4,
        }
    }
    stale = SetValueIntervention(
        "stale_nested_patch",
        InterventionTarget(WorldComponent.TRANSITION, ("regime", "tax_rate")),
        0.2,
        expected_before_sha256=content_digest(0.09),
    )
    before_hash = content_digest(subject)

    with pytest.raises(ValueError, match="precondition hash does not match"):
        apply_intervention(subject, stale)

    assert content_digest(subject) == before_hash
    assert subject["transition"] == {
        "regime": {"tax_rate": 0.1, "subsidy_rate": 0.02},
        "version": 4,
    }


def test_intervention_rejects_ambiguous_or_noncanonical_values() -> None:
    with pytest.raises(ValueError, match="name must not be empty"):
        SetValueIntervention(
            "",
            InterventionTarget(WorldComponent.TRANSITION, ("tax_rate",)),
            0.2,
        )
    with pytest.raises(ValueError, match="path segments must not be empty"):
        InterventionTarget(WorldComponent.TRANSITION, ("",))
    with pytest.raises(ValueError, match="64 lowercase hexadecimal"):
        SetValueIntervention(
            "invalid-hash",
            InterventionTarget(WorldComponent.TRANSITION, ("tax_rate",)),
            0.2,
            expected_before_sha256="not-a-hash",
        )
    with pytest.raises(TypeError, match="canonically serializable"):
        SetValueIntervention(
            "invalid-value",
            InterventionTarget(WorldComponent.TRANSITION, ("tax_rate",)),
            object(),
        )
