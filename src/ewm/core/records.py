"""Immutable value records shared across economic worlds and solvers."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray


def freeze_value(value: Any) -> Any:
    """Return an owned, recursively immutable representation of ``value``."""

    if isinstance(value, np.ndarray):
        frozen = np.array(value, copy=True)
        frozen.setflags(write=False)
        return frozen
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): freeze_value(item) for key, item in value.items()})
    if isinstance(value, tuple):
        return tuple(freeze_value(item) for item in value)
    if isinstance(value, list):
        return tuple(freeze_value(item) for item in value)
    if isinstance(value, set | frozenset):
        return frozenset(freeze_value(item) for item in value)
    return value


def thaw_value(value: Any) -> Any:
    """Return an owned mutable copy suitable for a transition implementation."""

    if isinstance(value, np.ndarray):
        return np.array(value, copy=True)
    if isinstance(value, Mapping):
        return {key: thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(thaw_value(item) for item in value)
    if isinstance(value, frozenset):
        return {thaw_value(item) for item in value}
    return deepcopy(value)


@dataclass(frozen=True, slots=True)
class RunMetadata:
    """Identity and provenance for a stochastic run."""

    scenario: str
    seed: int | None
    run_id: str
    intervention: str | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", freeze_value(self.parameters))


@dataclass(frozen=True, slots=True)
class Action:
    """A typed economic action submitted by one agent."""

    agent_id: str
    kind: str
    values: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", freeze_value(self.values))


@dataclass(frozen=True, slots=True)
class ConstraintViolation:
    """A rejected action and the feasibility rule that rejected it."""

    agent_id: str
    constraint: str
    reason: str


@dataclass(frozen=True, slots=True)
class Transition:
    """Immutable result of one economic-world transition."""

    state: Any
    outcomes: Mapping[str, Any] = field(default_factory=dict)
    accepted_actions: tuple[Action, ...] = ()
    violations: tuple[ConstraintViolation, ...] = ()
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", freeze_value(self.state))
        object.__setattr__(self, "outcomes", freeze_value(self.outcomes))
        object.__setattr__(self, "accepted_actions", tuple(self.accepted_actions))
        object.__setattr__(self, "violations", tuple(self.violations))
        object.__setattr__(self, "diagnostics", freeze_value(self.diagnostics))


@dataclass(frozen=True, slots=True)
class GeneratedDataset:
    """A learner-ready dataset generated inside an economic world."""

    features: NDArray[np.floating[Any]]
    targets: NDArray[Any]
    observed: NDArray[np.bool_] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "features", freeze_value(self.features))
        object.__setattr__(self, "targets", freeze_value(self.targets))
        if self.observed is not None:
            object.__setattr__(self, "observed", freeze_value(self.observed))
        object.__setattr__(self, "metadata", freeze_value(self.metadata))


@dataclass(frozen=True, slots=True)
class EquilibriumResult:
    """Result of a fixed-environment equilibrium solve."""

    solution: NDArray[np.floating[Any]]
    residual_norm: float
    converged: bool
    iterations: int
    message: str = ""
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "solution", freeze_value(self.solution))
        object.__setattr__(self, "diagnostics", freeze_value(self.diagnostics))


@dataclass(frozen=True, slots=True)
class FixedPoint:
    """One candidate fixed point and the initialization that selected it."""

    theta: NDArray[np.floating[Any]]
    initial_theta: NDArray[np.floating[Any]]
    residual_norm: float
    iterations: int
    converged: bool
    stable: bool | None = None
    spectral_radius: float | None = None
    residual_history: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "theta", freeze_value(self.theta))
        object.__setattr__(self, "initial_theta", freeze_value(self.initial_theta))
        object.__setattr__(self, "residual_history", tuple(self.residual_history))


@dataclass(frozen=True, slots=True)
class DDGEResult:
    """All distinct fixed points found for one DDGE problem."""

    fixed_points: tuple[FixedPoint, ...]
    selected_index: int | None = None
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        points = tuple(self.fixed_points)
        if self.selected_index is not None and not 0 <= self.selected_index < len(points):
            raise ValueError("selected_index must identify a fixed point")
        object.__setattr__(self, "fixed_points", points)
        object.__setattr__(self, "diagnostics", freeze_value(self.diagnostics))


@dataclass(frozen=True, slots=True)
class ExperimentResult:
    """Scenario-produced measurements before artifact serialization."""

    scenario: str
    experiment: str
    metrics: Mapping[str, Any]
    records: tuple[Mapping[str, Any], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metrics", freeze_value(self.metrics))
        object.__setattr__(self, "records", tuple(freeze_value(row) for row in self.records))
        object.__setattr__(self, "metadata", freeze_value(self.metadata))
