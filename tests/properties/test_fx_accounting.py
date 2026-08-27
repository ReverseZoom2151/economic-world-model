from __future__ import annotations

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from ewm.scenarios.fx import FXAccount, FXOrder, FXState, clear_market

positive_quantities = st.lists(
    st.floats(min_value=0.01, max_value=20.0, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=6,
)


@given(buy_quantities=positive_quantities, sell_quantities=positive_quantities)
@settings(max_examples=50, deadline=None)
def test_every_feasible_crossing_book_conserves_cash_and_foreign(
    buy_quantities: list[float], sell_quantities: list[float]
) -> None:
    accounts = {
        **{
            f"buyer-{index}": FXAccount(cash=quantity * 1.1 + 1.0, foreign=0.0)
            for index, quantity in enumerate(buy_quantities)
        },
        **{
            f"seller-{index}": FXAccount(cash=0.0, foreign=quantity + 1.0)
            for index, quantity in enumerate(sell_quantities)
        },
    }
    state = FXState(0, 1.0, accounts, (1.0,))
    orders = tuple(
        FXOrder(f"bid-{index}", f"buyer-{index}", "buy", quantity, 1.1)
        for index, quantity in enumerate(buy_quantities)
    ) + tuple(
        FXOrder(f"ask-{index}", f"seller-{index}", "sell", quantity, 0.9)
        for index, quantity in enumerate(sell_quantities)
    )

    result = clear_market(state, orders)

    assert math.isclose(result.cash_residual, 0.0, abs_tol=1e-10)
    assert math.isclose(result.foreign_residual, 0.0, abs_tol=1e-10)
    assert math.isclose(result.clearing_residual, 0.0, abs_tol=1e-10)
    assert math.isclose(
        result.volume,
        min(sum(buy_quantities), sum(sell_quantities)),
        rel_tol=1e-10,
        abs_tol=1e-10,
    )
    assert all(account.cash >= -1e-10 for account in result.state.accounts.values())
    assert all(account.foreign >= -1e-10 for account in result.state.accounts.values())
