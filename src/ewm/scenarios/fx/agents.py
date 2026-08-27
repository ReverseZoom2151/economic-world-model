"""Symbolic household, firm, and bank policies for the FX laboratory."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .model import FXOrder, FXState, Side


@dataclass(frozen=True, slots=True)
class HouseholdBelief:
    """Bounded-memory expected return used by one household."""

    expected_return: float = 0.0
    observations: tuple[float, ...] = ()


def update_belief(
    belief: HouseholdBelief,
    realized_return: float,
    *,
    memory: int,
) -> HouseholdBelief:
    """Update a household belief from a bounded window of realized returns."""

    if memory < 1:
        raise ValueError("memory must be positive")
    observations = (*belief.observations, realized_return)[-memory:]
    return HouseholdBelief(sum(observations) / len(observations), observations)


def household_order(
    agent_id: str,
    state: FXState,
    belief: HouseholdBelief,
    *,
    fundamental: float,
    trend_weight: float,
    quantity: float,
    rng: np.random.Generator,
) -> FXOrder:
    """Submit a feasible speculative order from trend and value signals."""

    account = state.accounts[agent_id]
    value_signal = (fundamental / state.spot) - 1.0
    signal = value_signal + trend_weight * belief.expected_return + 0.002 * rng.normal()
    side: Side
    if signal >= 0.0 and account.cash > 0.0:
        side = "buy"
        feasible = min(quantity, account.cash / (state.spot * 1.02))
        limit = state.spot * (1.005 + min(signal, 0.015))
    else:
        side = "sell"
        feasible = min(quantity, account.foreign)
        limit = state.spot * (0.995 + max(signal, -0.015))
    return FXOrder(
        order_id=f"{state.period:04d}-{agent_id}",
        agent_id=agent_id,
        side=side,
        quantity=max(feasible, 1e-12),
        limit_price=max(limit, 1e-12),
    )


def firm_order(agent_id: str, state: FXState, demand: float) -> FXOrder:
    """Submit a foreign-currency purchase required by a firm."""

    account = state.accounts[agent_id]
    quantity = min(demand, account.cash / (state.spot * 1.03))
    return FXOrder(
        order_id=f"{state.period:04d}-{agent_id}",
        agent_id=agent_id,
        side="buy",
        quantity=max(quantity, 1e-12),
        limit_price=state.spot * 1.02,
    )


def bank_orders(
    agent_id: str,
    state: FXState,
    *,
    depth: float,
    spread: float,
) -> tuple[FXOrder, FXOrder]:
    """Quote deterministic two-sided liquidity within bank balances."""

    account = state.accounts[agent_id]
    bid = state.spot * (1.0 - spread)
    ask = state.spot * (1.0 + spread)
    buy_quantity = min(depth, account.cash / bid)
    sell_quantity = min(depth, account.foreign)
    return (
        FXOrder(
            f"{state.period:04d}-{agent_id}-bid",
            agent_id,
            "buy",
            max(buy_quantity, 1e-12),
            bid,
        ),
        FXOrder(
            f"{state.period:04d}-{agent_id}-ask",
            agent_id,
            "sell",
            max(sell_quantity, 1e-12),
            ask,
        ),
    )
