from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pytest

from ewm.capabilities import (
    ActionSchema,
    CognitiveActionError,
    CognitiveAgent,
    FunctionalCognitiveTool,
    ModelRequest,
    ModelResponse,
)
from ewm.core import AgentSpecification


@dataclass
class ScriptedBackend:
    responses: list[ModelResponse]
    name: str = "fake"
    model: str = "deterministic-v1"

    def __post_init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        if not self.responses:
            raise RuntimeError("script exhausted")
        return self.responses.pop(0)


def _spec(*, memory_window: int = 2) -> AgentSpecification:
    return AgentSpecification(
        role="household",
        objective="Buy FX only within the declared budget.",
        state_variables=("cash", "belief"),
        information_channels={
            "public": ("exchange_rate",),
            "private": ("cash",),
        },
        action_space=("buy_fx", "hold"),
        tools=("budget_calculator",),
        constraints=("budget",),
        memory_window=memory_window,
    )


def _response(
    *,
    kind: str = "buy_fx",
    quantity: float = 2.0,
    belief: float = 1.1,
    request_id: str = "req-1",
) -> ModelResponse:
    return ModelResponse(
        action_kind=kind,
        action_values={} if kind == "hold" else {"quantity": quantity},
        belief_updates={"expected_rate": belief},
        rationale="The quote is below my explicit expected rate.",
        request_id=request_id,
    )


def _agent(backend: ScriptedBackend, *, memory_window: int = 2) -> CognitiveAgent:
    tool = FunctionalCognitiveTool(
        name="budget_calculator",
        function=lambda observation: {
            "maximum_quantity": float(observation["private"]["cash"]) / float(
                observation["public"]["exchange_rate"]
            )
        },
    )
    return CognitiveAgent(
        agent_id="household-0",
        specification=_spec(memory_window=memory_window),
        backend=backend,
        initial_beliefs={"expected_rate": 1.0},
        tools={tool.name: tool},
        action_schema=ActionSchema(
            required_values={"buy_fx": ("quantity",), "hold": ()},
            numeric_bounds={"buy_fx.quantity": (0.0, 10.0)},
        ),
        max_attempts=2,
    )


def _observation() -> Mapping[str, Any]:
    return {
        "public": {"exchange_rate": 1.05, "transaction_volume": 999.0},
        "private": {"cash": 8.0, "secret_identity": "must-not-leak"},
        "administrator": {"prompt": "must-not-leak"},
    }


def test_cognitive_agent_filters_observation_and_records_provenance() -> None:
    backend = ScriptedBackend([_response()])
    agent = _agent(backend)

    action = agent.act(_observation(), np.random.default_rng(9))
    request = backend.requests[0]
    decision = agent.last_decision

    assert action.agent_id == "household-0"
    assert action.kind == "buy_fx"
    assert action.values == {"quantity": 2.0}
    assert request.observation == {
        "public": {"exchange_rate": 1.05},
        "private": {"cash": 8.0},
    }
    assert request.beliefs == {"expected_rate": 1.0}
    assert request.tool_results["budget_calculator"] == {"maximum_quantity": 8.0 / 1.05}
    assert request.allowed_actions == ("buy_fx", "hold")
    assert decision is not None
    assert decision.beliefs == {"expected_rate": 1.1}
    assert decision.provenance.backend == "fake"
    assert decision.provenance.model == "deterministic-v1"
    assert decision.provenance.attempts == 1
    assert decision.provenance.request_ids == ("req-1",)
    assert decision.provenance.tools == ("budget_calculator",)


def test_memory_is_bounded_and_passed_as_owned_history() -> None:
    backend = ScriptedBackend(
        [_response(request_id=f"req-{index}") for index in range(3)]
    )
    agent = _agent(backend, memory_window=2)
    rng = np.random.default_rng(4)

    for _round in range(3):
        agent.act(_observation(), rng)

    assert len(agent.memory) == 2
    assert [entry.request_id for entry in agent.memory] == ["req-1", "req-2"]
    assert len(backend.requests[0].memory) == 0
    assert len(backend.requests[1].memory) == 1
    assert len(backend.requests[2].memory) == 2


def test_invalid_action_is_retried_then_validated_against_schema() -> None:
    backend = ScriptedBackend(
        [
            _response(kind="transfer_all_assets", request_id="bad"),
            _response(kind="hold", request_id="good"),
        ]
    )
    agent = _agent(backend)

    action = agent.act(_observation(), np.random.default_rng(1))

    assert action.kind == "hold"
    assert len(backend.requests) == 2
    assert backend.requests[1].attempt == 2
    assert "not declared" in (backend.requests[1].prior_error or "")
    assert agent.last_decision is not None
    assert agent.last_decision.provenance.attempts == 2
    assert agent.last_decision.provenance.request_ids == ("bad", "good")


def test_exhausted_retries_leave_beliefs_and_memory_unchanged() -> None:
    backend = ScriptedBackend(
        [
            _response(quantity=100.0, request_id="bad-1"),
            _response(quantity=100.0, request_id="bad-2"),
        ]
    )
    agent = _agent(backend)

    with pytest.raises(CognitiveActionError, match="after 2 attempts"):
        agent.act(_observation(), np.random.default_rng(2))

    assert agent.beliefs == {"expected_rate": 1.0}
    assert agent.memory == ()
    assert agent.last_decision is None


def test_declared_tool_registry_must_match_agent_specification() -> None:
    backend = ScriptedBackend([_response()])

    with pytest.raises(ValueError, match="tool registry"):
        CognitiveAgent(
            agent_id="household-0",
            specification=_spec(),
            backend=backend,
            initial_beliefs={"expected_rate": 1.0},
            tools={},
            action_schema=ActionSchema(
                required_values={"buy_fx": ("quantity",), "hold": ()}
            ),
        )
