"""Unit contracts for declarative economic worlds."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ewm.core import (
    AgentBlock,
    CoherenceCondition,
    CoherenceKind,
    EconomicWorldModelDefinition,
    InterventionSemantics,
    KernelDefinition,
    SpaceDefinition,
    WorldComponent,
)


def _agent(agent_id: str) -> AgentBlock:
    return AgentBlock(
        agent_id=agent_id,
        information=("public_price", f"{agent_id}_inventory"),
        policies=("buy", "sell", "hold"),
        beliefs=("expected_price",),
    )


def _definition(*, number_of_agents: int = 2) -> EconomicWorldModelDefinition:
    return EconomicWorldModelDefinition(
        state_space=SpaceDefinition("S", "Economic states"),
        action_space=SpaceDefinition("A", "Typed actions"),
        outcome_space=SpaceDefinition("Y", "Observed outcomes"),
        intervention_space=SpaceDefinition(
            "I", "Declared regimes", elements=("baseline", "tax")
        ),
        number_of_agents=number_of_agents,
        agents=(_agent("household"), _agent("firm")),
        coherence_conditions=(
            CoherenceCondition(
                "cash_conservation",
                CoherenceKind.HARD_EQUALITY,
                "sum(cash_next) = sum(cash)",
            ),
            CoherenceCondition(
                "budget",
                CoherenceKind.INEQUALITY,
                "spending <= cash",
            ),
            CoherenceCondition(
                "price_fit",
                CoherenceKind.SOFT,
                "absolute(predicted_price - observed_price)",
                tolerance=0.05,
            ),
        ),
        transition_kernel=KernelDefinition(
            "T_theta", inputs=("S", "A", "I"), output="S", parameter="theta"
        ),
        observation_kernel=KernelDefinition(
            "O_theta", inputs=("S", "A", "I"), output="Y", parameter="theta"
        ),
        intervention_semantics=(
            InterventionSemantics(
                "baseline",
                modifies=frozenset(),
                description="Reference regime",
            ),
            InterventionSemantics(
                "tax",
                modifies=frozenset(
                    {
                        WorldComponent.COHERENCE,
                        WorldComponent.OBJECTIVES,
                        WorldComponent.TRANSITION,
                    }
                ),
                description="Changes the tax rule and induced dynamics",
            ),
        ),
    )


def test_definition_encodes_every_block_of_cong_definition_2_6() -> None:
    definition = _definition()

    assert definition.state_space.name == "S"
    assert definition.action_space.name == "A"
    assert definition.outcome_space.name == "Y"
    assert definition.intervention_space.name == "I"
    assert definition.number_of_agents == 2
    assert definition.agent_ids == ("household", "firm")
    assert definition.agents[0].information == ("public_price", "household_inventory")
    assert definition.agents[0].policies == ("buy", "sell", "hold")
    assert definition.agents[0].beliefs == ("expected_price",)
    assert definition.hard_coherence[0].name == "cash_conservation"
    assert definition.inequality_coherence[0].name == "budget"
    assert definition.soft_coherence[0].name == "price_fit"
    assert definition.transition_kernel.parameter == "theta"
    assert definition.observation_kernel.output == "Y"
    assert definition.intervention("tax").modifies == frozenset(
        {
            WorldComponent.COHERENCE,
            WorldComponent.OBJECTIVES,
            WorldComponent.TRANSITION,
        }
    )


def test_definition_is_immutable_and_owns_nested_declarations() -> None:
    elements = ["baseline", "tax"]
    space = SpaceDefinition("I", "Regimes", elements=elements)
    elements.append("subsidy")
    definition = _definition()

    assert space.elements == ("baseline", "tax")
    with pytest.raises(FrozenInstanceError):
        definition.number_of_agents = 3  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        definition.agents[0].agent_id = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("number_of_agents", "number_of_agents must equal"),
        ("duplicate_agent", "agent identifiers must be unique"),
        ("missing_semantics", "missing intervention semantics"),
    ],
)
def test_definition_rejects_incoherent_declarations(field: str, expected: str) -> None:
    if field == "number_of_agents":
        with pytest.raises(ValueError, match=expected):
            _definition(number_of_agents=1)
        return

    definition = _definition()
    values = {
        "state_space": definition.state_space,
        "action_space": definition.action_space,
        "outcome_space": definition.outcome_space,
        "intervention_space": definition.intervention_space,
        "number_of_agents": definition.number_of_agents,
        "agents": definition.agents,
        "coherence_conditions": definition.coherence_conditions,
        "transition_kernel": definition.transition_kernel,
        "observation_kernel": definition.observation_kernel,
        "intervention_semantics": definition.intervention_semantics,
    }
    if field == "duplicate_agent":
        values["agents"] = (_agent("household"), _agent("household"))
    else:
        values["intervention_semantics"] = (definition.intervention("baseline"),)

    with pytest.raises(ValueError, match=expected):
        EconomicWorldModelDefinition(**values)  # type: ignore[arg-type]


def test_declarations_reject_duplicate_or_unknown_names() -> None:
    with pytest.raises(ValueError, match="space elements must be unique"):
        SpaceDefinition("I", "Regimes", elements=("baseline", "baseline"))
    with pytest.raises(ValueError, match="agent policies must be unique"):
        AgentBlock("a", information=("x",), policies=("hold", "hold"), beliefs=("b",))
    with pytest.raises(ValueError, match="kernel inputs must be unique"):
        KernelDefinition("T", inputs=("S", "S"), output="S")
