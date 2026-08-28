"""Declarative compiler blueprint for the heterogeneous FX world."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

import numpy as np

from ewm.core import (
    Action,
    AgentPolicy,
    AgentSpecification,
    FunctionalAgent,
    FunctionalConstraint,
    RuntimeAdapter,
    RuntimeAdapterRegistry,
    World,
    WorldBindings,
    WorldSpecification,
    compile_world,
)
from ewm.core.records import freeze_value
from ewm.core.specs import agent, constraints, environment, mechanism, scheduler, state
from ewm.core.world import ProvenanceMode

from ..economy.agents import bank_orders, firm_order, household_order
from ..economy.mechanism import FXBatchMechanism
from ..economy.model import FXAccount, FXOrder, FXState, HouseholdBelief
from ..economy.presets import FXSimulationConfig

FX_MECHANISM_KEY = (
    "batch_clearing",
    "uniform_clearing",
    "cash_asset_delivery",
)


def _order_values(order: FXOrder) -> Mapping[str, Any]:
    return {
        "limit_price": order.limit_price,
        "order_id": order.order_id,
        "quantity": order.quantity,
        "side": order.side,
    }


class FXStateCodec:
    """Canonical lossless codec for typed FX accounts and household beliefs."""

    @property
    def codec_id(self) -> str:
        return "ewm.fx.state.v1"

    def encode(self, state: Any) -> Any:
        if not isinstance(state, FXState):
            raise TypeError("FX state codec requires FXState")
        return freeze_value(
            {
                "accounts": {
                    agent_id: {
                        "cash": account.cash,
                        "foreign": account.foreign,
                    }
                    for agent_id, account in state.accounts.items()
                },
                "beliefs": {
                    agent_id: {
                        "expected_return": belief.expected_return,
                        "observations": belief.observations,
                    }
                    for agent_id, belief in state.beliefs.items()
                },
                "period": state.period,
                "price_history": state.price_history,
                "spot": state.spot,
            }
        )

    def decode(self, payload: Any) -> FXState:
        root = _require_mapping(payload, label="FX state payload")
        account_records = _require_mapping(
            root.get("accounts"),
            label="FX state accounts",
        )
        accounts = {
            str(agent_id): FXAccount(
                cash=float(record["cash"]),
                foreign=float(record["foreign"]),
            )
            for agent_id, values in account_records.items()
            for record in (_require_mapping(values, label="FX account record"),)
        }
        belief_records = _require_mapping(
            root.get("beliefs"),
            label="FX state beliefs",
        )
        beliefs = {
            str(agent_id): HouseholdBelief(
                expected_return=float(record["expected_return"]),
                observations=tuple(
                    float(item)
                    for item in _require_sequence(
                        record.get("observations"),
                        label="FX belief observations",
                    )
                ),
            )
            for agent_id, values in belief_records.items()
            for record in (_require_mapping(values, label="FX belief record"),)
        }
        return FXState(
            period=int(root["period"]),
            spot=float(root["spot"]),
            accounts=accounts,
            price_history=tuple(
                float(item)
                for item in _require_sequence(
                    root.get("price_history"),
                    label="FX price history",
                )
            ),
            beliefs=beliefs,
        )


def _require_mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return cast(Mapping[str, Any], value)


def _require_sequence(value: Any, *, label: str) -> tuple[Any, ...]:
    if not isinstance(value, tuple | list):
        raise TypeError(f"{label} must be a sequence")
    return tuple(value)


@dataclass(frozen=True, slots=True)
class FXWorldBlueprint:
    """Complete declarative and executable inputs for one FX world."""

    specification: WorldSpecification
    bindings: WorldBindings
    adapters: RuntimeAdapterRegistry

    def compile(self, *, provenance_mode: ProvenanceMode = "full") -> World:
        return compile_world(
            self.specification,
            bindings=self.bindings,
            adapters=self.adapters,
            provenance_mode=provenance_mode,
        )


def _fx_specification(config: FXSimulationConfig) -> WorldSpecification:
    household = agent(
        role="household",
        objective="Submit one feasible speculative FX order.",
        state_variables=["cash", "foreign", "belief"],
        information_channels={"market": ["spot", "price_history"]},
        action_space=["fx_order"],
        constraints=["fx_policy"],
        memory_window=config.belief_memory,
        count=config.households,
    )
    firm = agent(
        role="firm",
        objective="Purchase FX required for trade settlement.",
        state_variables=["cash", "foreign"],
        information_channels={"market": ["spot"]},
        action_space=["fx_order"],
        constraints=["fx_policy"],
    )
    bank = agent(
        role="bank",
        objective="Submit one two-sided FX liquidity batch.",
        state_variables=["cash", "foreign"],
        information_channels={"market": ["spot"]},
        action_space=["fx_order_batch"],
        constraints=["fx_policy"],
    )
    world_environment = environment(
        state=state(
            variables={"spot": config.initial_spot},
            accounts={
                "household": {"cash": 100.0, "foreign": 100.0},
                "firm": {"cash": 10_000.0, "foreign": 0.0},
                "bank": {"cash": 100_000.0, "foreign": 100_000.0},
            },
        ),
        constraints=constraints(rules=["fx_policy"]),
        scheduler=scheduler(policy="submission_order"),
        mechanism=mechanism(
            type=FX_MECHANISM_KEY[0],
            participants=["household", "firm", "bank"],
            input_actions=["fx_order", "fx_order_batch"],
            pricing_rule=FX_MECHANISM_KEY[1],
            settlement_rule=FX_MECHANISM_KEY[2],
        ),
    )
    return WorldSpecification(
        name="fx-runtime",
        agents=(household, firm, bank),
        environment=world_environment,
    )


def fx_world_blueprint(config: FXSimulationConfig) -> FXWorldBlueprint:
    """Build explicit compiler inputs for the configured FX laboratory."""

    specification = _fx_specification(config)
    household_ids = specification.agents[0].instance_ids

    def initial_state(_rng: np.random.Generator) -> FXState:
        accounts = {
            **{
                agent_id: FXAccount(cash=100.0, foreign=100.0)
                for agent_id in household_ids
            },
            "firm-0": FXAccount(cash=10_000.0, foreign=0.0),
            "bank-0": FXAccount(cash=100_000.0, foreign=100_000.0),
        }
        beliefs = {agent_id: HouseholdBelief() for agent_id in household_ids}
        return FXState(
            period=0,
            spot=config.initial_spot,
            accounts=accounts,
            price_history=(config.initial_spot,),
            beliefs=beliefs,
        )

    def household_factory(
        _specification: AgentSpecification,
        agent_id: str,
    ) -> AgentPolicy:
        def policy(state: FXState, rng: np.random.Generator) -> Action:
            order = household_order(
                agent_id,
                state,
                state.beliefs[agent_id],
                fundamental=config.fundamental,
                trend_weight=config.trend_weight,
                quantity=config.household_quantity,
                rng=rng,
            )
            return Action(agent_id, "fx_order", _order_values(order))

        return FunctionalAgent(agent_id, policy)

    def firm_factory(
        _specification: AgentSpecification,
        agent_id: str,
    ) -> AgentPolicy:
        return FunctionalAgent(
            agent_id,
            lambda state, _rng: Action(
                agent_id,
                "fx_order",
                _order_values(firm_order(agent_id, state, config.firm_demand)),
            ),
        )

    def bank_factory(
        _specification: AgentSpecification,
        agent_id: str,
    ) -> AgentPolicy:
        return FunctionalAgent(
            agent_id,
            lambda state, _rng: Action(
                agent_id,
                "fx_order_batch",
                {
                    "orders": tuple(
                        _order_values(order)
                        for order in bank_orders(
                            agent_id,
                            state,
                            depth=config.bank_depth,
                            spread=config.bank_spread,
                        )
                    )
                },
            ),
        )

    bindings = WorldBindings(
        initial_state=initial_state,
        agent_factories={
            "household": household_factory,
            "firm": firm_factory,
            "bank": bank_factory,
        },
        constraints={
            "fx_policy": FunctionalConstraint(
                "fx_policy",
                lambda _state, _action: None,
            )
        },
        state_codec=FXStateCodec(),
    )
    adapters = RuntimeAdapterRegistry(
        (
            RuntimeAdapter(
                adapter_id="fx_uniform_batch_v1",
                mechanism_key=FX_MECHANISM_KEY,
                mechanism_factory=lambda _specification, _options: FXBatchMechanism(
                    adaptive_beliefs=config.adaptive_beliefs,
                    belief_memory=config.belief_memory,
                ),
            ),
        )
    )
    return FXWorldBlueprint(specification, bindings, adapters)
