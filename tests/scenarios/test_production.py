from __future__ import annotations

from math import exp, log, sqrt

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from scipy.optimize import root

from ewm.experiments.production import solve_production_equilibrium
from ewm.scenarios.production import (
    DistributionState,
    ProductionEconomy,
    ProductionPrimitives,
    package_authored_example,
)


def test_firm_closed_form_demands_satisfy_both_first_order_conditions() -> None:
    economy = package_authored_example()

    decision = economy.firm_decision(rental_rate=0.08, wage=1.1)

    assert decision.capital > 0.0
    assert decision.labor > 0.0
    assert decision.capital_foc_residual == pytest.approx(0.0, abs=1e-12)
    assert decision.labor_foc_residual == pytest.approx(0.0, abs=1e-12)
    assert decision.profit > 0.0


def test_equilibrium_enforces_household_budgets_borrowing_and_both_markets() -> None:
    economy = package_authored_example()

    equilibrium = solve_production_equilibrium(
        economy,
        initial_rental_rate=0.08,
        initial_wage=1.0,
    )

    assert equilibrium.converged
    assert equilibrium.max_budget_residual < 1e-10
    assert equilibrium.max_household_foc_residual < 1e-9
    assert equilibrium.capital_clearing_residual == pytest.approx(0.0, abs=1e-9)
    assert equilibrium.labor_clearing_residual == pytest.approx(0.0, abs=1e-9)
    assert equilibrium.firm.capital_foc_residual == pytest.approx(0.0, abs=1e-10)
    assert equilibrium.firm.labor_foc_residual == pytest.approx(0.0, abs=1e-10)
    assert all(
        decision.next_assets >= economy.primitives.borrowing_bound
        for decision in equilibrium.households
    )


def test_prices_match_an_independent_log_utility_root_system() -> None:
    economy = package_authored_example()
    primitives = economy.primitives
    distribution = economy.distribution

    def independent_household_supply(rental_rate: float, wage: float) -> tuple[float, float]:
        savings_ratio = primitives.continuation_weight
        assets = 0.0
        labor = 0.0
        for asset, shock, weight in zip(
            distribution.assets,
            distribution.shocks,
            distribution.weights,
            strict=True,
        ):
            labor_weight = primitives.labor_disutility / shock
            nonlabor_resources = (
                (1.0 + rental_rate) * asset - primitives.borrowing_bound
            )
            coefficient_a = labor_weight * wage
            coefficient_b = labor_weight * nonlabor_resources
            coefficient_c = -wage * (1.0 + savings_ratio)
            supplied_labor = (
                -coefficient_b
                + sqrt(coefficient_b**2 - 4.0 * coefficient_a * coefficient_c)
            ) / (2.0 * coefficient_a)
            consumption = (
                wage * supplied_labor + nonlabor_resources
            ) / (1.0 + savings_ratio)
            next_assets = primitives.borrowing_bound + savings_ratio * consumption
            assets += weight * next_assets
            labor += weight * supplied_labor
        return assets, labor

    def independent_firm_demand(rental_rate: float, wage: float) -> tuple[float, float]:
        alpha = primitives.capital_share
        gamma = primitives.labor_share
        determinant = 1.0 - alpha - gamma
        capital_rhs = log(
            (rental_rate + primitives.depreciation)
            / (alpha * primitives.productivity)
        )
        labor_rhs = log(wage / (gamma * primitives.productivity))
        log_capital = (
            (gamma - 1.0) * capital_rhs - gamma * labor_rhs
        ) / determinant
        log_labor = (
            -alpha * capital_rhs + (alpha - 1.0) * labor_rhs
        ) / determinant
        return exp(log_capital), exp(log_labor)

    def independent_residual(log_prices: np.ndarray) -> np.ndarray:
        rental_rate = exp(float(log_prices[0])) - primitives.depreciation
        wage = exp(float(log_prices[1]))
        capital_supply, labor_supply = independent_household_supply(rental_rate, wage)
        capital_demand, labor_demand = independent_firm_demand(rental_rate, wage)
        return np.array(
            [capital_demand - capital_supply, labor_demand - labor_supply]
        )

    independent = root(
        independent_residual,
        np.log(np.array([0.08 + primitives.depreciation, 1.0])),
    )
    equilibrium = solve_production_equilibrium(
        economy,
        initial_rental_rate=0.08,
        initial_wage=1.0,
    )

    assert independent.success
    assert equilibrium.rental_rate == pytest.approx(
        exp(float(independent.x[0])) - primitives.depreciation,
        rel=1e-9,
    )
    assert equilibrium.wage == pytest.approx(exp(float(independent.x[1])), rel=1e-9)


@given(
    assets=st.lists(
        st.floats(min_value=0.05, max_value=3.0, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=3,
    ),
    shocks=st.lists(
        st.floats(min_value=0.5, max_value=2.0, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=3,
    ),
    rental_rate=st.floats(
        min_value=-0.02,
        max_value=0.2,
        allow_nan=False,
        allow_infinity=False,
    ),
    wage=st.floats(
        min_value=0.2,
        max_value=3.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_household_feasibility_over_bounded_distributional_states(
    assets: list[float],
    shocks: list[float],
    rental_rate: float,
    wage: float,
) -> None:
    economy = ProductionEconomy(
        primitives=ProductionPrimitives(),
        distribution=DistributionState(
            assets=tuple(assets),
            shocks=tuple(shocks),
            weights=(0.2, 0.3, 0.5),
        ),
    )

    decisions = economy.household_decisions(rental_rate=rental_rate, wage=wage)

    assert all(decision.consumption > 0.0 for decision in decisions)
    assert all(
        decision.next_assets >= economy.primitives.borrowing_bound
        for decision in decisions
    )
    assert max(abs(decision.budget_residual) for decision in decisions) < 1e-10
    assert max(abs(decision.savings_foc_residual) for decision in decisions) < 1e-9
    assert max(abs(decision.labor_foc_residual) for decision in decisions) < 1e-8


def test_example_discloses_every_package_authored_primitive() -> None:
    economy = package_authored_example()

    assert set(economy.package_authored_primitives) == {
        "borrowing_bound",
        "capital_share",
        "continuation_value",
        "depreciation",
        "household_distribution",
        "labor_disutility",
        "labor_share",
        "preferences",
        "productivity",
    }
    assert all(economy.package_authored_primitives.values())
