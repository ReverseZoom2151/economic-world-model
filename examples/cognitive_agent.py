"""Run a deterministic provider-neutral cognitive household agent."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

import ewm
from ewm.capabilities import (
    ActionSchema,
    CognitiveAgent,
    FunctionalCognitiveTool,
    ModelRequest,
    ModelResponse,
)


@dataclass(frozen=True, slots=True)
class OfflineHouseholdBackend:
    """A local deterministic backend used only to demonstrate the protocol."""

    name: str = "offline-example"
    model: str = "rule-backed-v1"

    def complete(self, request: ModelRequest) -> ModelResponse:
        quote = float(request.observation["public"]["exchange_rate"])
        expected = float(request.beliefs["expected_rate"])
        maximum = float(
            request.tool_results["budget_calculator"]["maximum_quantity"]
        )
        if quote < expected:
            kind = "buy_fx"
            values = {"quantity": min(2.0, maximum)}
        else:
            kind = "hold"
            values = {}
        return ModelResponse(
            action_kind=kind,
            action_values=values,
            belief_updates={"expected_rate": 0.8 * expected + 0.2 * quote},
            rationale="Apply the declared quote rule within the computed budget.",
            request_id=f"offline-{request.attempt}",
        )


def main() -> None:
    specification = ewm.agent(
        role="household",
        objective="Trade FX within budget.",
        state_variables=["cash", "belief"],
        information_channels={
            "public": ["exchange_rate"],
            "private": ["cash"],
        },
        action_space=["buy_fx", "hold"],
        tools=["budget_calculator"],
        constraints=["budget"],
        memory_window=2,
    )
    tool = FunctionalCognitiveTool(
        "budget_calculator",
        lambda observation: {
            "maximum_quantity": float(observation["private"]["cash"])
            / float(observation["public"]["exchange_rate"])
        },
    )
    household = CognitiveAgent(
        agent_id="household-0",
        specification=specification,
        backend=OfflineHouseholdBackend(),
        initial_beliefs={"expected_rate": 1.1},
        tools={tool.name: tool},
        action_schema=ActionSchema(
            required_values={"buy_fx": ("quantity",), "hold": ()},
            numeric_bounds={"buy_fx.quantity": (0.0, 10.0)},
        ),
    )
    action = household.act(
        {"public": {"exchange_rate": 1.0}, "private": {"cash": 8.0}},
        np.random.default_rng(42),
    )
    assert household.last_decision is not None
    print(
        f"action={action.kind} values={dict(action.values)} "
        f"backend={household.last_decision.provenance.backend}"
    )


if __name__ == "__main__":
    main()
