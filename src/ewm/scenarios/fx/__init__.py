"""Heterogeneous multi-agent foreign-exchange laboratory."""

from __future__ import annotations

from ewm._internal.imports import register_module_aliases

from .economy.agents import (
    HouseholdBelief,
    bank_orders,
    firm_order,
    household_order,
    update_belief,
)
from .economy.mechanism import FXBatchMechanism, clear_market
from .economy.model import (
    FXAccount,
    FXClearingResult,
    FXOrder,
    FXRejection,
    FXSimulationResult,
    FXState,
    FXTrade,
)
from .economy.presets import FXSimulationConfig, research_config, smoke_config
from .execution.runtime import FXStateCodec, FXWorldBlueprint, fx_world_blueprint
from .execution.simulation import FXWorldRun, run_fx_simulation, run_fx_world

register_module_aliases(
    __name__,
    {
        "agents": "economy.agents",
        "mechanism": "economy.mechanism",
        "model": "economy.model",
        "presets": "economy.presets",
        "runtime": "execution.runtime",
        "simulation": "execution.simulation",
        "validation": "execution.validation",
    },
)

__all__ = [
    "FXAccount",
    "FXBatchMechanism",
    "FXClearingResult",
    "FXOrder",
    "FXRejection",
    "FXSimulationConfig",
    "FXSimulationResult",
    "FXState",
    "FXStateCodec",
    "FXTrade",
    "FXWorldBlueprint",
    "FXWorldRun",
    "HouseholdBelief",
    "bank_orders",
    "clear_market",
    "firm_order",
    "fx_world_blueprint",
    "household_order",
    "research_config",
    "run_fx_simulation",
    "run_fx_world",
    "smoke_config",
    "update_belief",
]
