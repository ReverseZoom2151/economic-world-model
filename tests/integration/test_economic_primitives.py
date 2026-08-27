from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from ewm.core import (
    CallableStochasticKernel,
    CoherenceRelation,
    HardCoherenceCondition,
    InterventionTarget,
    SetValueIntervention,
    SoftCoherenceDiagnostic,
    WorldComponent,
    apply_intervention,
    evaluate_coherence,
)


def test_intervention_kernel_and_coherence_primitives_bind_without_hidden_runtime() -> None:
    baseline = {
        "transition": {"default_probability": 0.05},
        "coherence": {"assets": 100.0, "liabilities": 95.0},
        "observations": {"predicted_default_rate": 0.06, "default_rate": 0.05},
    }
    intervention = SetValueIntervention(
        "stress_default_probability",
        InterventionTarget(WorldComponent.TRANSITION, ("default_probability",)),
        0.25,
    )
    stressed = apply_intervention(baseline, intervention)

    def distribution(state: Mapping[str, object]) -> Mapping[str, float]:
        transition = state["transition"]
        assert isinstance(transition, Mapping)
        probability = float(transition["default_probability"])
        return {"repay": 1.0 - probability, "default": probability}

    kernel = CallableStochasticKernel(
        "credit_outcome",
        ("repay", "default"),
        distribution,
    )
    hard = HardCoherenceCondition(
        "solvency",
        CoherenceRelation.GREATER_EQUAL,
        "USD",
        100.0,
        0.0,
        lambda state: float(state["coherence"]["assets"]),
        lambda state: float(state["coherence"]["liabilities"]),
    )
    soft = SoftCoherenceDiagnostic(
        "default_rate_fit",
        "share",
        1.0,
        0.02,
        lambda state: float(state["observations"]["predicted_default_rate"]),
        lambda state: float(state["observations"]["default_rate"]),
    )

    row = kernel.probabilities(stressed.subject)
    draw = kernel.sample(
        stressed.subject,
        rng=np.random.default_rng(17),
        stream_id="stress/replicate-0",
    )
    report = evaluate_coherence(
        stressed.subject,
        hard_conditions=(hard,),
        soft_diagnostics=(soft,),
    )

    assert dict(row) == {"repay": 0.75, "default": 0.25}
    assert draw.value in row
    assert draw.provenance.stream_id == "stress/replicate-0"
    assert report.coherent
    assert report.soft_diagnostics[0].within_tolerance
    assert stressed.record.diff.as_data()["path"] == "/transition/default_probability"
