from __future__ import annotations

from dataclasses import replace

import pytest

from ewm.scenarios.fx import (
    FXAccount,
    FXOrder,
    FXState,
    clear_market,
    run_fx_simulation,
    smoke_config,
)


def _state() -> FXState:
    return FXState(
        period=0,
        spot=1.0,
        accounts={
            "buyer-a": FXAccount(cash=100.0, foreign=0.0),
            "buyer-b": FXAccount(cash=100.0, foreign=0.0),
            "seller-a": FXAccount(cash=0.0, foreign=100.0),
            "seller-b": FXAccount(cash=0.0, foreign=100.0),
        },
        price_history=(1.0,),
    )


def test_no_crossing_book_does_not_trade_or_move_price() -> None:
    orders = (
        FXOrder("bid", "buyer-a", "buy", quantity=3.0, limit_price=0.9),
        FXOrder("ask", "seller-a", "sell", quantity=3.0, limit_price=1.1),
    )

    result = clear_market(_state(), orders)

    assert result.volume == 0.0
    assert result.clearing_price is None
    assert result.state.spot == 1.0
    assert result.trades == ()


def test_exact_crossing_settles_at_one_price_and_conserves_assets() -> None:
    orders = (
        FXOrder("bid", "buyer-a", "buy", quantity=5.0, limit_price=1.1),
        FXOrder("ask", "seller-a", "sell", quantity=5.0, limit_price=0.9),
    )

    result = clear_market(_state(), orders)

    assert result.volume == pytest.approx(5.0)
    assert result.clearing_price is not None
    assert all(trade.price == result.clearing_price for trade in result.trades)
    assert result.cash_residual == pytest.approx(0.0, abs=1e-12)
    assert result.foreign_residual == pytest.approx(0.0, abs=1e-12)
    assert result.clearing_residual == pytest.approx(0.0, abs=1e-12)


def test_long_side_is_allocated_pro_rata() -> None:
    orders = (
        FXOrder("bid-a", "buyer-a", "buy", quantity=6.0, limit_price=1.1),
        FXOrder("bid-b", "buyer-b", "buy", quantity=4.0, limit_price=1.1),
        FXOrder("ask", "seller-a", "sell", quantity=5.0, limit_price=0.9),
    )

    result = clear_market(_state(), orders)
    bought = {
        buyer: sum(trade.quantity for trade in result.trades if trade.buyer_id == buyer)
        for buyer in ("buyer-a", "buyer-b")
    }

    assert bought == pytest.approx({"buyer-a": 3.0, "buyer-b": 2.0})
    assert result.volume == pytest.approx(5.0)


def test_infeasible_orders_are_rejected_before_clearing() -> None:
    state = FXState(
        period=0,
        spot=1.0,
        accounts={
            "poor": FXAccount(cash=1.0, foreign=0.0),
            "short": FXAccount(cash=0.0, foreign=1.0),
        },
        price_history=(1.0,),
    )
    orders = (
        FXOrder("too-expensive", "poor", "buy", quantity=2.0, limit_price=1.1),
        FXOrder("too-large", "short", "sell", quantity=2.0, limit_price=0.9),
    )

    result = clear_market(state, orders)

    assert result.volume == 0.0
    assert {rejection.reason for rejection in result.rejections} == {
        "insufficient cash",
        "insufficient foreign inventory",
    }


def test_order_input_order_does_not_change_tie_breaking_or_settlement() -> None:
    orders = (
        FXOrder("bid-b", "buyer-b", "buy", quantity=2.0, limit_price=1.1),
        FXOrder("ask-b", "seller-b", "sell", quantity=2.0, limit_price=0.9),
        FXOrder("bid-a", "buyer-a", "buy", quantity=2.0, limit_price=1.1),
        FXOrder("ask-a", "seller-a", "sell", quantity=2.0, limit_price=0.9),
    )

    forward = clear_market(_state(), orders)
    reverse = clear_market(_state(), tuple(reversed(orders)))

    assert forward.clearing_price == reverse.clearing_price
    assert forward.trades == reverse.trades
    assert forward.state == reverse.state


def test_adaptive_rollout_is_seeded_and_conserves_assets() -> None:
    config = smoke_config(periods=12)

    first = run_fx_simulation(config, seed=42)
    second = run_fx_simulation(config, seed=42)
    assert first == second
    assert len(first.prices) == config.periods + 1
    assert len(first.volumes) == config.periods
    assert first.max_cash_residual < 1e-10
    assert first.max_foreign_residual < 1e-10


def test_config_variants_remain_explicit() -> None:
    config = smoke_config()
    changed = replace(config, adaptive_beliefs=False, trend_weight=0.0)

    assert config.adaptive_beliefs is True
    assert changed.adaptive_beliefs is False
