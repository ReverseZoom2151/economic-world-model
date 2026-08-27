from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

import ewm
from ewm.capabilities import (
    AbsoluteErrorMetric,
    AlignmentContext,
    BoundedAlignment,
    CorrectionProposal,
    ExternalObservation,
    FunctionalCorrectionPlanner,
)
from ewm.core import (
    Action,
    CoevolutionProposal,
    ControlledCoevolution,
    FunctionalAgent,
    FunctionalMechanism,
    World,
)
from ewm.experiments import MetricEvidence, evaluate_layered

pytestmark = pytest.mark.conformance
NOW = datetime(2026, 8, 27, 12, tzinfo=UTC)


def _declaration():
    trader = ewm.agent(
        role="trader",
        objective="Submit a feasible unit order.",
        state_variables=["cash", "belief"],
        information_channels={"public": ["price"]},
        action_space=["order"],
        constraints=["budget"],
        memory_window=2,
    )
    environment = ewm.environment(
        state=ewm.state(
            variables={"price": 1.0},
            accounts={"trader": {"cash": 2.0}},
        ),
        constraints=ewm.constraints(rules=["budget"]),
        scheduler=ewm.scheduler(),
        mechanism=ewm.mechanism(
            type="batch_clearing",
            participants=["trader"],
            input_actions=["order"],
            pricing_rule="uniform_clearing",
            settlement_rule="cash_asset_delivery",
        ),
    )
    coevolution = ewm.coevolution(
        agent_updates=ewm.agent_updates(
            targets=["belief"],
            signals=["realized_price"],
        ),
        environment_updates=ewm.environment_updates(
            targets=["mechanism_parameters"],
            signals=["order_imbalance"],
        ),
    )
    alignment = ewm.alignment(
        data_sources=ewm.data_sources(streams=["official-price"], frequency="daily"),
        targets=["price"],
        metrics=["price_error"],
        tolerance={"price_error": 0.05},
        correction=ewm.correction(
            agent_targets=[],
            environment_targets=["mechanism_parameters"],
            policy="bounded_update",
            max_delta=0.1,
        ),
    )
    evaluation = ewm.evaluation(
        layers={
            "agents": ["action_validity", "role_consistency"],
            "environment": ["constraint_rate", "clearing_error"],
            "coevolution": ["adaptation_gain", "stability"],
            "alignment": ["state_error", "correction_magnitude"],
            "efficiency": ["runtime", "memory"],
        }
    )
    return ewm.make(
        "HanConformance-v0",
        agents=[trader],
        environment=environment,
        coevolution=coevolution,
        alignment=alignment,
        evaluation=evaluation,
    )


def _world(specification) -> World:
    assert specification.coevolution is not None
    assert specification.alignment is not None

    def propose(state, actions, next_state, _snapshot):
        return (
            CoevolutionProposal(
                scope="agent",
                owner_id="trader-0",
                target="belief",
                signal="realized_price",
                signal_value=float(next_state["price"]),
                delta=0.05,
            ),
            CoevolutionProposal(
                scope="environment",
                owner_id=None,
                target="mechanism_parameters",
                signal="order_imbalance",
                signal_value=sum(float(item.values["amount"]) for item in actions),
                delta=0.05,
            ),
        )

    coevolution = ControlledCoevolution(
        specification=specification.coevolution,
        agent_components={"trader-0": {"belief": 1.0}},
        environment_components={"mechanism_parameters": 1.0},
        agent_bounds={"belief": 0.1},
        environment_bounds={"mechanism_parameters": 0.1},
        proposal_rule=propose,
    )

    def plan(_context: AlignmentContext) -> tuple[CorrectionProposal, ...]:
        return (
            CorrectionProposal(
                scope="environment",
                owner_id=None,
                target="mechanism_parameters",
                delta=0.05,
                source_metric="price_error",
                diagnosis="official price exceeds the simulated transition price",
            ),
        )

    alignment = BoundedAlignment(
        specification=specification.alignment,
        metrics={"price_error": AbsoluteErrorMetric("price_error", "price")},
        agent_components={},
        environment_components={"mechanism_parameters": 1.0},
        planner=FunctionalCorrectionPlanner("conformance-planner", plan),
        max_evidence_age=timedelta(days=1),
    )
    agent = FunctionalAgent(
        "trader-0",
        lambda _state, _rng: Action("trader-0", "order", {"amount": 1.0}),
    )

    def clear(state, actions, _rng):
        state["price"] += 0.1 * sum(float(item.values["amount"]) for item in actions)
        return state, {"clearing_error": 0.0, "accounting_error": 0.0}

    return World(
        initial_state=lambda _rng: {"price": 1.0},
        agents=(agent,),
        mechanism=FunctionalMechanism(clear),
        coevolution=coevolution,
        alignment=alignment,
    )


def test_han_specification_through_alignment_and_layered_evaluation() -> None:
    specification = _declaration()
    world = _world(specification)
    state = world.reset(seed=17)
    actions = world.run_agents(state)
    transition = world.step(actions)
    coevolution = world.coevolve(state, actions, transition.state)
    alignment = world.align(
        {"price": float(transition.state["price"])},
        ExternalObservation(
            stream="official-price",
            observed_at=NOW,
            values={"price": 1.25},
            reference="offline://han-conformance/price",
        ),
        as_of=NOW,
    )
    _ = world.evaluate()
    events = world.events.snapshot()
    layered = evaluate_layered(
        events,
        state_version=world.state_version,
        evidence={
            "agents": {
                "role_consistency_rate": MetricEvidence(
                    1.0,
                    "ratio",
                    "conformance/typed-agent",
                    1,
                )
            },
            "environment": {
                "clearing_error": MetricEvidence(
                    0.0,
                    "absolute_residual",
                    "conformance/clearing",
                    1,
                ),
                "accounting_error": MetricEvidence(
                    0.0,
                    "absolute_residual",
                    "conformance/accounting",
                    1,
                ),
            },
            "coevolution": {
                "adaptation_gain": MetricEvidence(
                    0.01,
                    "score_delta",
                    "conformance/adaptation",
                    1,
                )
            },
            "efficiency": {
                "runtime_seconds": MetricEvidence(
                    0.01,
                    "seconds",
                    "conformance/deterministic-fixture",
                    1,
                )
            },
        },
    )

    assert specification.runtime_mechanism == "fx_uniform_batch_v1"
    assert transition.state["price"] == pytest.approx(1.1)
    assert coevolution.after_version == 1
    assert alignment.after_version == 1
    assert tuple(event.kind for event in events) == (
        "reset",
        "run_agents",
        "step",
        "coevolve",
        "align",
        "evaluate",
    )
    assert all(event.schema_version == "ewm.event.v1" for event in events)
    assert all(event.state_version in {0, 1} for event in events)
    assert layered.layers["agents"].metrics["action_validity_rate"].value == 1.0
    assert layered.layers["environment"].metrics["clearing_error"].value == 0.0
    assert layered.layers["alignment"].metrics["correction_magnitude"].value == 0.05
