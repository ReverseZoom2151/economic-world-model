"""Adaptive FX rollout."""

from __future__ import annotations

from dataclasses import dataclass

from ewm.core import Event, ProvenanceMode

from .model import FXSimulationResult, FXState
from .presets import FXSimulationConfig
from .runtime import fx_world_blueprint


@dataclass(frozen=True, slots=True)
class FXWorldRun:
    """Public FX result paired with its canonical compiled-world provenance."""

    result: FXSimulationResult
    events: tuple[Event, ...]


def _run_fx_world(
    config: FXSimulationConfig,
    *,
    seed: int,
    provenance_mode: ProvenanceMode,
) -> FXWorldRun:
    """Run the FX scenario through one compiled-world provenance mode."""

    world = fx_world_blueprint(config).compile(provenance_mode=provenance_mode)
    state = world.reset(seed=seed)
    volumes: list[float] = []
    rejected: list[int] = []
    cash_residuals: list[float] = []
    foreign_residuals: list[float] = []

    for _ in range(config.periods):
        transition = world.step(world.run_agents(state))
        state = transition.state
        volumes.append(float(transition.outcomes["volume"]))
        rejected.append(int(transition.outcomes["rejected_count"]))
        cash_residuals.append(abs(float(transition.outcomes["cash_residual"])))
        foreign_residuals.append(abs(float(transition.outcomes["foreign_residual"])))

    if not isinstance(state, FXState):
        raise TypeError("compiled FX world returned a non-FX state")
    return FXWorldRun(
        result=FXSimulationResult(
            prices=state.price_history,
            volumes=tuple(volumes),
            rejected_orders=tuple(rejected),
            max_cash_residual=max(cash_residuals, default=0.0),
            max_foreign_residual=max(foreign_residuals, default=0.0),
        ),
        events=world.events.snapshot(),
    )


def run_fx_world(config: FXSimulationConfig, *, seed: int) -> FXWorldRun:
    """Run FX with the full replay-complete compiled-world event chain."""

    return _run_fx_world(config, seed=seed, provenance_mode="full")


def run_fx_simulation(config: FXSimulationConfig, *, seed: int) -> FXSimulationResult:
    """Return compact results from the compiled FX world without replay payloads."""

    return _run_fx_world(config, seed=seed, provenance_mode="summary").result
