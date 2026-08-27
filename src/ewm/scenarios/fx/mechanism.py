"""Uniform-price batch clearing with pre-trade balance reservation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from ewm.core import Action

from .agents import update_belief
from .model import (
    FXAccount,
    FXClearingResult,
    FXOrder,
    FXRejection,
    FXState,
    FXTrade,
    Side,
)

_TOLERANCE = 1e-12


def _reserve_feasible_orders(
    state: FXState, orders: tuple[FXOrder, ...]
) -> tuple[tuple[FXOrder, ...], tuple[FXRejection, ...]]:
    identifiers = [order.order_id for order in orders]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("order identifiers must be unique")

    cash = {agent_id: account.cash for agent_id, account in state.accounts.items()}
    foreign = {agent_id: account.foreign for agent_id, account in state.accounts.items()}
    accepted: list[FXOrder] = []
    rejected: list[FXRejection] = []
    for order in sorted(orders, key=lambda candidate: candidate.order_id):
        if order.agent_id not in state.accounts:
            rejected.append(FXRejection(order, "unknown account"))
        elif order.side == "buy":
            commitment = order.quantity * order.limit_price
            if commitment > cash[order.agent_id] + _TOLERANCE:
                rejected.append(FXRejection(order, "insufficient cash"))
            else:
                cash[order.agent_id] -= commitment
                accepted.append(order)
        elif order.quantity > foreign[order.agent_id] + _TOLERANCE:
            rejected.append(FXRejection(order, "insufficient foreign inventory"))
        else:
            foreign[order.agent_id] -= order.quantity
            accepted.append(order)
    return tuple(accepted), tuple(rejected)


def _clearing_price(state: FXState, orders: tuple[FXOrder, ...]) -> float | None:
    bids = tuple(order for order in orders if order.side == "buy")
    asks = tuple(order for order in orders if order.side == "sell")
    if not bids or not asks:
        return None
    if max(order.limit_price for order in bids) + _TOLERANCE < min(
        order.limit_price for order in asks
    ):
        return None

    candidates = sorted({order.limit_price for order in orders})
    ranked: list[tuple[float, float, float, float]] = []
    for price in candidates:
        demand = sum(
            order.quantity
            for order in bids
            if order.limit_price + _TOLERANCE >= price
        )
        supply = sum(
            order.quantity
            for order in asks
            if order.limit_price <= price + _TOLERANCE
        )
        volume = min(demand, supply)
        if volume > _TOLERANCE:
            ranked.append(
                (
                    -volume,
                    abs(demand - supply),
                    round(abs(price - state.spot), 12),
                    price,
                )
            )
    return min(ranked)[-1] if ranked else None


@dataclass(slots=True)
class _Fill:
    order: FXOrder
    remaining: float


def _fills(orders: tuple[FXOrder, ...], target: float) -> list[_Fill]:
    total = sum(order.quantity for order in orders)
    if total <= _TOLERANCE:
        return []
    factor = min(1.0, target / total)
    return [
        _Fill(order, order.quantity * factor)
        for order in sorted(orders, key=lambda candidate: candidate.order_id)
    ]


def _match(
    buys: tuple[FXOrder, ...], sells: tuple[FXOrder, ...], price: float
) -> tuple[FXTrade, ...]:
    target = min(
        sum(order.quantity for order in buys),
        sum(order.quantity for order in sells),
    )
    buy_fills = _fills(buys, target)
    sell_fills = _fills(sells, target)
    trades: list[FXTrade] = []
    buy_index = 0
    sell_index = 0
    while buy_index < len(buy_fills) and sell_index < len(sell_fills):
        buy_fill = buy_fills[buy_index]
        sell_fill = sell_fills[sell_index]
        quantity = min(buy_fill.remaining, sell_fill.remaining)
        if quantity > _TOLERANCE:
            trades.append(
                FXTrade(
                    buyer_id=buy_fill.order.agent_id,
                    seller_id=sell_fill.order.agent_id,
                    quantity=quantity,
                    price=price,
                    buy_order_id=buy_fill.order.order_id,
                    sell_order_id=sell_fill.order.order_id,
                )
            )
        buy_fill.remaining -= quantity
        sell_fill.remaining -= quantity
        if buy_fill.remaining <= _TOLERANCE:
            buy_index += 1
        if sell_fill.remaining <= _TOLERANCE:
            sell_index += 1
    return tuple(trades)


def _settle(state: FXState, trades: tuple[FXTrade, ...], price: float | None) -> FXState:
    balances = {
        agent_id: [account.cash, account.foreign]
        for agent_id, account in state.accounts.items()
    }
    for trade in trades:
        notional = trade.quantity * trade.price
        balances[trade.buyer_id][0] -= notional
        balances[trade.buyer_id][1] += trade.quantity
        balances[trade.seller_id][0] += notional
        balances[trade.seller_id][1] -= trade.quantity

    accounts = {
        agent_id: FXAccount(
            cash=0.0 if abs(values[0]) <= _TOLERANCE else values[0],
            foreign=0.0 if abs(values[1]) <= _TOLERANCE else values[1],
        )
        for agent_id, values in balances.items()
    }
    next_spot = state.spot if price is None else price
    return FXState(
        period=state.period + 1,
        spot=next_spot,
        accounts=accounts,
        price_history=(*state.price_history, next_spot),
        beliefs=state.beliefs,
    )


def clear_market(state: FXState, orders: tuple[FXOrder, ...]) -> FXClearingResult:
    """Validate, uniformly clear, and settle one FX order batch."""

    initial_cash = sum(account.cash for account in state.accounts.values())
    initial_foreign = sum(account.foreign for account in state.accounts.values())
    accepted, rejections = _reserve_feasible_orders(state, orders)
    price = _clearing_price(state, accepted)
    if price is None:
        trades: tuple[FXTrade, ...] = ()
    else:
        eligible_buys = tuple(
            order
            for order in accepted
            if order.side == "buy" and order.limit_price + _TOLERANCE >= price
        )
        eligible_sells = tuple(
            order
            for order in accepted
            if order.side == "sell" and order.limit_price <= price + _TOLERANCE
        )
        trades = _match(eligible_buys, eligible_sells, price)

    next_state = _settle(state, trades, price)
    final_cash = sum(account.cash for account in next_state.accounts.values())
    final_foreign = sum(account.foreign for account in next_state.accounts.values())
    bought = sum(trade.quantity for trade in trades)
    sold = sum(trade.quantity for trade in trades)
    return FXClearingResult(
        state=next_state,
        clearing_price=price,
        volume=bought,
        trades=trades,
        accepted_orders=accepted,
        rejections=rejections,
        cash_residual=final_cash - initial_cash,
        foreign_residual=final_foreign - initial_foreign,
        clearing_residual=bought - sold,
    )


@dataclass(frozen=True, slots=True)
class FXBatchMechanism:
    """Adapter from shared EWM actions to the typed FX clearing function."""

    adaptive_beliefs: bool = False
    belief_memory: int = 4

    def clear(
        self,
        state: FXState,
        actions: tuple[Action, ...],
        rng: np.random.Generator,
    ) -> tuple[FXState, Mapping[str, Any]]:
        del rng
        orders = tuple(
            order
            for action in actions
            for order in _orders_from_action(action)
        )
        result = clear_market(state, orders)
        next_state = result.state
        realized_return = (next_state.spot / state.spot) - 1.0
        if self.adaptive_beliefs:
            next_state = replace(
                next_state,
                beliefs={
                    agent_id: update_belief(
                        belief,
                        realized_return,
                        memory=self.belief_memory,
                    )
                    for agent_id, belief in state.beliefs.items()
                },
            )
        return next_state, {
            "clearing_price": result.clearing_price,
            "volume": result.volume,
            "cash_residual": result.cash_residual,
            "foreign_residual": result.foreign_residual,
            "clearing_residual": result.clearing_residual,
            "rejected_count": len(result.rejections),
            "submitted_order_count": len(orders),
            "accepted_order_count": len(result.accepted_orders),
        }


def _order_from_values(agent_id: str, values: Mapping[str, Any]) -> FXOrder:
    side_value = values["side"]
    if side_value not in ("buy", "sell"):
        raise ValueError("FX action side must be 'buy' or 'sell'")
    side: Side = side_value
    return FXOrder(
        order_id=str(values["order_id"]),
        agent_id=agent_id,
        side=side,
        quantity=float(values["quantity"]),
        limit_price=float(values["limit_price"]),
    )


def _orders_from_action(action: Action) -> tuple[FXOrder, ...]:
    if action.kind == "fx_order":
        return (_order_from_values(action.agent_id, action.values),)
    if action.kind == "fx_order_batch":
        records = action.values["orders"]
        if not isinstance(records, tuple):
            raise TypeError("FX order batch must contain immutable order records")
        return tuple(_order_from_values(action.agent_id, record) for record in records)
    return ()
