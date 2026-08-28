"""Orchestration for the production-economy laboratory."""

from __future__ import annotations

from ewm.equilibrium import solve_equilibrium
from ewm.scenarios.production import ProductionEconomy, ProductionEquilibrium


def solve_production_equilibrium(
    economy: ProductionEconomy,
    *,
    initial_rental_rate: float,
    initial_wage: float,
) -> ProductionEquilibrium:
    """Use the shared inner solver, then construct production-specific diagnostics."""

    initial = economy.initial_price_candidate(
        initial_rental_rate=initial_rental_rate,
        initial_wage=initial_wage,
    )
    result = solve_equilibrium(economy, initial)
    return economy.equilibrium_from_result(result)
