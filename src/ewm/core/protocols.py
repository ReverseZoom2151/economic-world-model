"""Structural interfaces for economic worlds, agents, and equilibrium problems."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

from .records import Action, Transition


class AgentPolicy(Protocol):
    """A model-independent policy backend for one economic agent."""

    @property
    def agent_id(self) -> str: ...

    def act(self, observation: Any, rng: np.random.Generator) -> Action: ...


class Constraint(Protocol):
    """A feasibility predicate returning a rejection reason when violated."""

    @property
    def name(self) -> str: ...

    def check(self, state: Any, action: Action) -> str | None: ...


class Mechanism(Protocol):
    """An institution that clears feasible actions into an economic state."""

    def clear(
        self,
        state: Any,
        actions: tuple[Action, ...],
        rng: np.random.Generator,
    ) -> tuple[Any, Mapping[str, Any]]: ...


class EconomicWorld(Protocol):
    """Minimal executable-world boundary."""

    def reset(self, seed: int | None = None) -> Any: ...

    def observe(self, state: Any, agent_id: str) -> Any: ...

    def run_agents(self, state: Any) -> tuple[Action, ...]: ...

    def step(self, state: Any, actions: tuple[Action, ...]) -> Transition: ...


class EquilibriumProblem(Protocol):
    """A fixed-environment equilibrium represented by residual equations."""

    def residual(self, candidate: NDArray[np.floating[Any]]) -> NDArray[np.floating[Any]]: ...


class DDGEProblem(Protocol):
    """A single-valued behavior-data-learning update used by the v0 solver."""

    @property
    def dimension(self) -> int: ...

    def update(self, theta: NDArray[np.floating[Any]]) -> NDArray[np.floating[Any]]: ...

