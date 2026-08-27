from __future__ import annotations

import numpy as np
import pytest

from ewm.core import (
    AgentBlock,
    CoherenceCondition,
    CoherenceKind,
    DDGECandidate,
    EconomicWorldModelDefinition,
    InterventionSemantics,
    KernelDefinition,
    SpaceDefinition,
    WorldComponent,
)
from ewm.equilibrium import (
    EquilibriumCorrespondence,
    FixedPointConfig,
    fixed_point_residual,
    frozen_counterfactual_bounds,
    solve_ddge,
)
from ewm.scenarios.scalar import (
    ScalarConfig,
    ScalarLearner,
    ScalarProblem,
    inner_solution,
    linear_displacement,
    outer_update,
)

pytestmark = pytest.mark.conformance


def _definition() -> EconomicWorldModelDefinition:
    return EconomicWorldModelDefinition(
        state_space=SpaceDefinition("state", "behavior and response", ("a", "b")),
        action_space=SpaceDefinition("action", "behavior", ("a",)),
        outcome_space=SpaceDefinition("outcome", "generated statistic", ("a",)),
        intervention_space=SpaceDefinition(
            "regime",
            "scalar displacement regime",
            ("adoption-shock",),
        ),
        number_of_agents=1,
        agents=(
            AgentBlock(
                agent_id="representative-agent",
                information=("theta", "delta"),
                policies=("linear-best-response",),
                beliefs=("response-consistency",),
            ),
        ),
        coherence_conditions=(
            CoherenceCondition(
                "behavior",
                CoherenceKind.HARD_EQUALITY,
                "a = kappa * b + theta + delta",
            ),
            CoherenceCondition(
                "belief",
                CoherenceKind.HARD_EQUALITY,
                "b = gamma * a",
            ),
        ),
        transition_kernel=KernelDefinition(
            "scalar-learning",
            ("a",),
            "theta_next",
            parameter="theta",
        ),
        observation_kernel=KernelDefinition(
            "observe-behavior",
            ("a", "b"),
            "dataset",
        ),
        intervention_semantics=(
            InterventionSemantics(
                "adoption-shock",
                frozenset({WorldComponent.TRANSITION, WorldComponent.POLICIES}),
                "Shift the scalar behavioral equation by delta.",
            ),
        ),
    )


def _candidate(theta: float, config: ScalarConfig) -> DDGECandidate:
    inner = inner_solution(theta, config)
    generated_data = {"behavior": inner.behavior, "response": inner.response}
    return DDGECandidate(
        policies={"representative-agent": inner.behavior},
        beliefs={"representative-agent": inner.response},
        theta=np.array([theta]),
        aggregates={"behavior": inner.behavior},
        data=generated_data,
    )


def _correspondence(config: ScalarConfig) -> EquilibriumCorrespondence:
    return EquilibriumCorrespondence(
        behavioral_residual=lambda candidate: abs(
            float(candidate.policies["representative-agent"])
            - (
                config.kappa * float(candidate.beliefs["representative-agent"])
                + float(candidate.theta[0])
                + config.intervention
            )
        ),
        belief_residual=lambda candidate: abs(
            float(candidate.beliefs["representative-agent"])
            - config.gamma * float(candidate.policies["representative-agent"])
        ),
        feasibility_residual=lambda candidate: max(
            0.0,
            -float(candidate.aggregates["behavior"]) - 100.0,
        ),
        aggregate_residual=lambda candidate: abs(
            float(candidate.aggregates["behavior"])
            - float(candidate.data["behavior"])
        ),
        learning_update=lambda candidate: np.array(
            [config.learning_gain * float(candidate.data["behavior"])]
        ),
        tolerance=1e-9,
    )


def test_cong_definition_to_equilibrium_data_learning_and_bounds() -> None:
    definition = _definition()
    config = ScalarConfig(
        kappa=0.2,
        gamma=0.5,
        learning_gain=0.4,
        intervention=0.1,
        learner=ScalarLearner.LINEAR,
    )
    problem = ScalarProblem(config)
    solved = solve_ddge(
        problem,
        (np.array([-0.5]), np.array([0.0]), np.array([0.5])),
        FixedPointConfig(tolerance=1e-12, max_iterations=1_000),
    )
    displacement = linear_displacement(config)

    assert definition.number_of_agents == 1
    assert len(solved.fixed_points) == 1
    theta_star = float(solved.fixed_points[0].theta[0])
    assert theta_star == pytest.approx(displacement.fixed_point, abs=1e-11)

    candidate = _candidate(theta_star, config)
    correspondence = _correspondence(config)
    assert correspondence.select(candidate.theta, (candidate,)) == candidate
    certificate = correspondence.verify(candidate)
    assert certificate.consistent
    assert tuple(check.component for check in certificate.checks) == (
        "behavioral_optimality",
        "belief_consistency",
        "feasibility",
        "aggregate_consistency",
        "learning",
    )
    assert fixed_point_residual(problem.update, candidate.theta) < 1e-11

    bounds = frozen_counterfactual_bounds(
        residual_norm=abs(outer_update(0.0, config)),
        contraction=abs(config.composite_gain),
        discount=0.9,
        utility_sensitivity=1.0,
        transition_sensitivity=0.2,
        reward_bound=1.0,
    )
    assert abs(theta_star) <= bounds.displacement_bound + 1e-12
    assert bounds.welfare_bound >= 0.0


def test_inner_equilibrium_does_not_imply_learning_consistency() -> None:
    config = ScalarConfig(
        kappa=0.2,
        gamma=0.5,
        learning_gain=0.4,
        intervention=0.1,
        learner=ScalarLearner.LINEAR,
    )
    candidate = _candidate(0.0, config)
    correspondence = _correspondence(config)

    assert correspondence.inner_equilibria(candidate.theta, (candidate,)) == (candidate,)
    certificate = correspondence.verify(candidate)

    assert not certificate.consistent
    assert certificate.failed_components == ("learning",)
