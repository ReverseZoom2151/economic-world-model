"""Unit contracts for economic world specifications."""

from __future__ import annotations

from types import MappingProxyType

import pytest

import ewm
from ewm.core import WorldSpecification


def _fx_specification() -> WorldSpecification:
    household = ewm.agent(
        role="household",
        objective="Hold cash and FX while respecting budget constraints.",
        state_variables=["cash", "fx_inventory", "belief"],
        information_channels={
            "public": ["exchange_rate", "transaction_volume"],
            "private": ["cash", "fx_inventory"],
        },
        action_space=["buy_fx", "sell_fx", "hold"],
        tools=["budget_calculator", "fx_quote_lookup"],
        constraints=["budget", "inventory", "role_permission"],
        memory_window=4,
    )
    firm = ewm.agent(
        role="firm",
        objective="Purchase foreign currency for trade settlement.",
        state_variables=["cash", "fx_need"],
        information_channels={"public": ["exchange_rate"]},
        action_space=["buy_fx", "hold"],
        constraints=["budget", "role_permission"],
    )
    bank = ewm.agent(
        role="bank",
        objective="Provide two-sided FX liquidity within exposure limits.",
        state_variables=["cash", "fx_inventory"],
        information_channels={"public": ["exchange_rate", "transaction_volume"]},
        action_space=["quote_bid", "quote_ask", "hold"],
        constraints=["budget", "inventory", "role_permission", "exposure_limit"],
    )
    market_state = ewm.state(
        variables={"exchange_rate": 1.0, "volume": 1_000.0, "volatility": 0.02},
        accounts={
            "household": {"cash": 1_000.0, "fx_inventory": 0.0},
            "firm": {"cash": 3_000.0, "fx_need": 500.0},
            "bank": {"cash": 10_000.0, "fx_inventory": 2_000.0},
        },
    )
    market_constraints = ewm.constraints(
        rules=["budget", "inventory", "role_permission", "exposure_limit"],
        violation_policy="reject_and_log",
    )
    clearing = ewm.mechanism(
        type="batch_clearing",
        participants=["household", "firm", "bank"],
        input_actions=["buy_fx", "sell_fx", "quote_bid", "quote_ask"],
        pricing_rule="uniform_clearing",
        settlement_rule="cash_asset_delivery",
    )
    environment = ewm.environment(
        state=market_state,
        constraints=market_constraints,
        scheduler=ewm.scheduler(),
        mechanism=clearing,
    )
    coevolution = ewm.coevolution(
        agent_updates=ewm.agent_updates(
            targets=["belief", "memory", "policy"],
            signals=["observation", "realized_outcome", "reward"],
        ),
        environment_updates=ewm.environment_updates(
            targets=["mechanism_parameters"],
            signals=["trading_volume", "price_error", "constraint_violations"],
        ),
    )
    alignment = ewm.alignment(
        data_sources=ewm.data_sources(
            streams=["exchange_rate", "trading_volume", "volatility"],
            frequency="daily",
        ),
        targets=["exchange_rate", "volume", "volatility"],
        metrics=["price_error", "volume_error", "volatility_error"],
        tolerance={
            "price_error": 0.02,
            "volume_error": 0.10,
            "volatility_error": 0.05,
        },
        correction=ewm.correction(
            agent_targets=["belief", "state"],
            environment_targets=["mechanism_parameters"],
            policy="bounded_update",
            max_delta=0.10,
        ),
    )
    evaluation = ewm.evaluation(
        layers={
            "agents": ["action_validity", "role_consistency"],
            "environment": ["constraint_violation_rate", "market_clearing_error"],
            "coevolution": ["adaptation_gain", "stability"],
            "alignment": ["state_error", "correction_magnitude"],
            "efficiency": ["runtime_cost", "memory_usage"],
        }
    )
    result = ewm.make(
        "FXMarket-v0",
        agents=[household, firm, bank],
        environment=environment,
        coevolution=coevolution,
        alignment=alignment,
        evaluation=evaluation,
    )
    assert isinstance(result, WorldSpecification)
    return result


def test_han_figures_9_11_13_and_15_construct_one_world_specification() -> None:
    specification = _fx_specification()

    assert specification.name == "FXMarket-v0"
    assert specification.roles == ("household", "firm", "bank")
    assert specification.environment.mechanism.type == "batch_clearing"
    assert specification.coevolution is not None
    assert specification.alignment is not None
    assert specification.evaluation is not None
    assert specification.runtime_mechanism == "fx_uniform_batch_v1"


def test_specs_take_immutable_ownership_of_mutable_inputs() -> None:
    variables = {"exchange_rate": 1.0}
    channels = {"public": ["exchange_rate"]}
    agent = ewm.agent(
        role="household",
        objective="Trade FX.",
        state_variables=["cash"],
        information_channels=channels,
        action_space=["hold"],
    )
    state = ewm.state(variables=variables, accounts={"household": {"cash": 1.0}})
    variables["exchange_rate"] = 2.0
    channels["public"].append("private_leak")

    assert isinstance(state.variables, MappingProxyType)
    assert state.variables["exchange_rate"] == 1.0
    assert agent.information_channels["public"] == ("exchange_rate",)


def test_world_specification_validates_cross_references() -> None:
    participant = ewm.agent(
        role="household",
        objective="Hold.",
        state_variables=["cash"],
        information_channels={"public": ["price"]},
        action_space=["hold"],
        constraints=["budget"],
    )
    environment = ewm.environment(
        state=ewm.state(variables={"price": 1.0}, accounts={"household": {"cash": 1.0}}),
        constraints=ewm.constraints(rules=["budget"]),
        scheduler=ewm.scheduler(),
        mechanism=ewm.mechanism(
            type="batch_clearing",
            participants=["unknown_role"],
            input_actions=["hold"],
            pricing_rule="uniform_clearing",
            settlement_rule="cash_asset_delivery",
        ),
    )

    with pytest.raises(ValueError, match="unknown mechanism participants"):
        ewm.make("invalid", agents=[participant], environment=environment)


def test_alignment_tolerances_and_correction_bounds_are_validated() -> None:
    sources = ewm.data_sources(streams=["price"], frequency="daily")
    correction = ewm.correction(
        agent_targets=["belief"],
        environment_targets=["mechanism_parameters"],
        policy="bounded_update",
        max_delta=0.1,
    )

    with pytest.raises(ValueError, match="tolerance keys"):
        ewm.alignment(
            data_sources=sources,
            targets=["price"],
            metrics=["price_error"],
            tolerance={"wrong_metric": 0.1},
            correction=correction,
        )
    with pytest.raises(ValueError, match="max_delta"):
        ewm.correction(
            agent_targets=["belief"],
            environment_targets=[],
            policy="bounded_update",
            max_delta=0.0,
        )


def test_unsupported_mechanism_has_an_explicit_runtime_gate() -> None:
    specification = _fx_specification()
    unsupported = ewm.mechanism(
        type="continuous_double_auction",
        participants=specification.roles,
        input_actions=["buy_fx", "sell_fx", "quote_bid", "quote_ask"],
        pricing_rule="price_time_priority",
        settlement_rule="cash_asset_delivery",
    )
    environment = ewm.environment(
        state=specification.environment.state,
        constraints=specification.environment.constraints,
        scheduler=specification.environment.scheduler,
        mechanism=unsupported,
    )
    declared = ewm.make(
        "UnsupportedMarket-v0",
        agents=specification.agents,
        environment=environment,
    )

    assert isinstance(declared, WorldSpecification)
    with pytest.raises(NotImplementedError, match="continuous_double_auction"):
        _ = declared.runtime_mechanism
