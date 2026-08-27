"""Adaptive FX rollout and prespecified paired comparisons."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

import numpy as np

from .agents import (
    HouseholdBelief,
    bank_orders,
    firm_order,
    household_order,
    update_belief,
)
from .mechanism import clear_market
from .model import FXAccount, FXSimulationResult, FXState
from .presets import FXSimulationConfig


def _initial_state(config: FXSimulationConfig) -> FXState:
    accounts = {
        **{
            f"household-{index}": FXAccount(cash=100.0, foreign=100.0)
            for index in range(config.households)
        },
        "firm": FXAccount(cash=10_000.0, foreign=0.0),
        "bank": FXAccount(cash=100_000.0, foreign=100_000.0),
    }
    return FXState(0, config.initial_spot, accounts, (config.initial_spot,))


def run_fx_simulation(config: FXSimulationConfig, *, seed: int) -> FXSimulationResult:
    """Run symbolic policies, batch clearing, settlement, and belief adaptation."""

    rng = np.random.default_rng(seed)
    state = _initial_state(config)
    beliefs = {
        f"household-{index}": HouseholdBelief()
        for index in range(config.households)
    }
    volumes: list[float] = []
    rejected: list[int] = []
    cash_residuals: list[float] = []
    foreign_residuals: list[float] = []

    for _ in range(config.periods):
        household_orders = tuple(
            household_order(
                agent_id,
                state,
                belief,
                fundamental=config.fundamental,
                trend_weight=config.trend_weight,
                quantity=config.household_quantity,
                rng=rng,
            )
            for agent_id, belief in sorted(beliefs.items())
        )
        orders = (
            *household_orders,
            firm_order("firm", state, config.firm_demand),
            *bank_orders(
                "bank",
                state,
                depth=config.bank_depth,
                spread=config.bank_spread,
            ),
        )
        previous_spot = state.spot
        result = clear_market(state, orders)
        state = result.state
        realized_return = (state.spot / previous_spot) - 1.0
        if config.adaptive_beliefs:
            beliefs = {
                agent_id: update_belief(
                    belief,
                    realized_return,
                    memory=config.belief_memory,
                )
                for agent_id, belief in beliefs.items()
            }
        volumes.append(result.volume)
        rejected.append(len(result.rejections))
        cash_residuals.append(abs(result.cash_residual))
        foreign_residuals.append(abs(result.foreign_residual))

    return FXSimulationResult(
        prices=state.price_history,
        volumes=tuple(volumes),
        rejected_orders=tuple(rejected),
        max_cash_residual=max(cash_residuals, default=0.0),
        max_foreign_residual=max(foreign_residuals, default=0.0),
    )


def paired_comparisons(
    config: FXSimulationConfig, *, seed: int
) -> Mapping[str, Mapping[str, float]]:
    """Run prespecified common-seed FX comparisons and return effect differences."""

    baseline = run_fx_simulation(config, seed=seed).metrics
    variants = {
        "firm_demand_shock": replace(config, firm_demand=config.firm_demand * 1.5),
        "trend_intensity": replace(config, trend_weight=config.trend_weight * 1.5),
        "adaptive_beliefs": replace(config, adaptive_beliefs=False),
    }
    variant_metrics = {
        name: run_fx_simulation(variant, seed=seed).metrics
        for name, variant in variants.items()
    }
    return {
        name: {
            metric: metrics[metric] - baseline_value
            for metric, baseline_value in baseline.items()
        }
        for name, metrics in variant_metrics.items()
    }
