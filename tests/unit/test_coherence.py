from __future__ import annotations

from typing import Any

import pytest

from ewm.core.coherence import (
    CoherenceRelation,
    HardCoherenceCondition,
    SoftCoherenceDiagnostic,
    evaluate_coherence,
)


def _value(name: str):
    def evaluate(state: dict[str, float]) -> float:
        return state[name]

    return evaluate


def test_hard_conditions_are_evaluated_atomically_in_declared_units() -> None:
    state = {
        "cash_before": 100.0,
        "cash_after": 100.0005,
        "spending": 10.2,
        "cash": 10.0,
        "reserves": 4.95,
        "required_reserves": 5.0,
    }
    conditions = (
        HardCoherenceCondition(
            name="cash_conservation",
            relation=CoherenceRelation.EQUAL,
            unit="USD",
            scale=100.0,
            tolerance=0.001,
            left=_value("cash_after"),
            right=_value("cash_before"),
        ),
        HardCoherenceCondition(
            name="budget",
            relation=CoherenceRelation.LESS_EQUAL,
            unit="USD",
            scale=10.0,
            tolerance=0.1,
            left=_value("spending"),
            right=_value("cash"),
        ),
        HardCoherenceCondition(
            name="reserve_floor",
            relation=CoherenceRelation.GREATER_EQUAL,
            unit="USD",
            scale=5.0,
            tolerance=0.05,
            left=_value("reserves"),
            right=_value("required_reserves"),
        ),
    )

    report = evaluate_coherence(state, hard_conditions=conditions)

    conservation, budget, reserve = report.hard_results
    assert conservation.passed
    assert conservation.unit == "USD"
    assert conservation.absolute_gap == pytest.approx(0.0005)
    assert conservation.normalized_gap == pytest.approx(0.000005)
    assert conservation.normalized_violation == 0.0
    assert not budget.passed
    assert budget.signed_gap == pytest.approx(0.2)
    assert budget.normalized_violation == pytest.approx(0.01)
    assert reserve.passed
    assert report.failed_conditions == ("budget",)
    assert not report.coherent


def test_opposing_hard_residuals_cannot_cancel_each_other() -> None:
    conditions = (
        HardCoherenceCondition(
            "positive_error",
            CoherenceRelation.EQUAL,
            "goods",
            1.0,
            0.1,
            lambda _state: 0.2,
            lambda _state: 0.0,
        ),
        HardCoherenceCondition(
            "negative_error",
            CoherenceRelation.EQUAL,
            "goods",
            1.0,
            0.1,
            lambda _state: -0.2,
            lambda _state: 0.0,
        ),
    )

    report = evaluate_coherence({}, hard_conditions=conditions)

    assert [result.passed for result in report.hard_results] == [False, False]
    assert report.failed_conditions == ("positive_error", "negative_error")


def test_soft_diagnostics_are_reported_without_deciding_hard_coherence() -> None:
    diagnostic = SoftCoherenceDiagnostic(
        name="price_fit",
        unit="USD/index-point",
        scale=2.0,
        tolerance=0.1,
        left=lambda state: state["predicted"],
        right=lambda state: state["observed"],
    )

    report = evaluate_coherence(
        {"predicted": 2.2, "observed": 2.0},
        soft_diagnostics=(diagnostic,),
    )

    result = report.soft_diagnostics[0]
    assert report.coherent
    assert report.failed_conditions == ()
    assert result.absolute_deviation == pytest.approx(0.2)
    assert result.normalized_deviation == pytest.approx(0.1)
    assert not result.within_tolerance
    assert not hasattr(result, "passed")


def test_soft_diagnostic_cannot_rescue_a_failed_hard_condition() -> None:
    hard = HardCoherenceCondition(
        "market_clearing",
        CoherenceRelation.EQUAL,
        "goods",
        100.0,
        0.01,
        lambda _state: 100.02,
        lambda _state: 100.0,
    )
    soft = SoftCoherenceDiagnostic(
        "price_fit",
        "USD",
        1.0,
        1.0,
        lambda _state: 4.0,
        lambda _state: 4.0,
    )

    report = evaluate_coherence(
        {},
        hard_conditions=(hard,),
        soft_diagnostics=(soft,),
    )

    assert not report.coherent
    assert report.failed_conditions == ("market_clearing",)
    assert report.soft_diagnostics[0].within_tolerance


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("name", "", "name must not be empty"),
        ("unit", "", "unit must not be empty"),
        ("scale", 0.0, "scale must be finite and positive"),
        ("scale", float("inf"), "scale must be finite and positive"),
        ("tolerance", -1.0, "tolerance must be finite and non-negative"),
        ("tolerance", float("nan"), "tolerance must be finite and non-negative"),
    ],
)
def test_conditions_reject_undefined_measurement_metadata(
    field: str,
    value: Any,
    message: str,
) -> None:
    values: dict[str, Any] = {
        "name": "condition",
        "relation": CoherenceRelation.EQUAL,
        "unit": "USD",
        "scale": 1.0,
        "tolerance": 0.0,
        "left": lambda _state: 0.0,
        "right": lambda _state: 0.0,
    }
    values[field] = value

    with pytest.raises(ValueError, match=message):
        HardCoherenceCondition(**values)


def test_coherence_evaluation_rejects_nonfinite_measurements_and_duplicate_names() -> None:
    invalid = HardCoherenceCondition(
        "invalid",
        CoherenceRelation.EQUAL,
        "USD",
        1.0,
        0.0,
        lambda _state: float("nan"),
        lambda _state: 0.0,
    )
    duplicate = SoftCoherenceDiagnostic(
        "invalid",
        "USD",
        1.0,
        0.0,
        lambda _state: 0.0,
        lambda _state: 0.0,
    )

    with pytest.raises(ValueError, match="finite numeric measurements"):
        evaluate_coherence({}, hard_conditions=(invalid,))
    with pytest.raises(ValueError, match="condition names must be unique"):
        evaluate_coherence(
            {},
            hard_conditions=(invalid,),
            soft_diagnostics=(duplicate,),
        )
