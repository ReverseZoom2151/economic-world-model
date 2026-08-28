"""Domain contracts for economic action constraints."""

from ewm.core.constraints import ConstraintSet, FunctionalConstraint

from ewm.core import Action


def test_constraint_set_rejects_infeasible_actions_and_records_reason() -> None:
    constraints = ConstraintSet(
        (
            FunctionalConstraint(
                name="non_negative",
                predicate=lambda _state, action: (
                    "amount must be non-negative" if action.values["amount"] < 0 else None
                ),
            ),
        )
    )
    actions = (
        Action("accepted", "submit", {"amount": 2.0}),
        Action("rejected", "submit", {"amount": -1.0}),
    )

    accepted, violations = constraints.validate({}, actions)

    assert [action.agent_id for action in accepted] == ["accepted"]
    assert len(violations) == 1
    assert violations[0].agent_id == "rejected"
    assert violations[0].constraint == "non_negative"
    assert violations[0].reason == "amount must be non-negative"


def test_constraint_set_records_every_failed_rule_once() -> None:
    constraints = ConstraintSet(
        (
            FunctionalConstraint("budget", lambda _state, _action: "over budget"),
            FunctionalConstraint("permission", lambda _state, _action: "not permitted"),
        )
    )

    accepted, violations = constraints.validate({}, (Action("a", "buy"),))

    assert accepted == ()
    assert [violation.constraint for violation in violations] == ["budget", "permission"]
