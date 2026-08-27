"""Preset configurations for heterogeneous FX experiments."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FXSimulationConfig:
    """Population, policy, and mechanism settings for an FX rollout."""

    periods: int = 24
    households: int = 6
    initial_spot: float = 1.0
    fundamental: float = 1.0
    firm_demand: float = 3.0
    household_quantity: float = 1.0
    trend_weight: float = 0.8
    adaptive_beliefs: bool = True
    belief_memory: int = 4
    bank_depth: float = 30.0
    bank_spread: float = 0.002

    def __post_init__(self) -> None:
        if self.periods < 1 or self.households < 1 or self.belief_memory < 1:
            raise ValueError("periods, households, and belief_memory must be positive")
        if self.initial_spot <= 0.0 or self.fundamental <= 0.0:
            raise ValueError("prices must be positive")
        if self.firm_demand <= 0.0 or self.household_quantity <= 0.0:
            raise ValueError("order quantities must be positive")
        if self.bank_depth <= 0.0:
            raise ValueError("bank_depth must be positive")
        if not 0.0 < self.bank_spread < 1.0:
            raise ValueError("bank_spread must lie in (0, 1)")


def smoke_config(*, periods: int = 24) -> FXSimulationConfig:
    """Return a small deterministic FX configuration for CI and examples."""

    return FXSimulationConfig(periods=periods)


def research_config(*, periods: int = 500) -> FXSimulationConfig:
    """Return the longer baseline used for research comparisons."""

    return FXSimulationConfig(periods=periods, households=40, bank_depth=150.0)
