"""Immutable value records shared across economic worlds and solvers."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from math import isfinite
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
class CoevolutionProposal:
    """One scalar adaptive update proposed from an internal feedback signal."""

    scope: str
    owner_id: str | None
    target: str
    signal: str
    signal_value: float
    delta: float

    def __post_init__(self) -> None:
        if self.scope not in {"agent", "environment"}:
            raise ValueError("coevolution scope must be 'agent' or 'environment'")
        if self.scope == "agent" and not self.owner_id:
            raise ValueError("agent coevolution proposal requires owner_id")
        if self.scope == "environment" and self.owner_id is not None:
            raise ValueError("environment coevolution proposal must not have owner_id")
        if not self.target or not self.signal:
            raise ValueError("coevolution target and signal must not be empty")
        if not isfinite(self.signal_value) or not isfinite(self.delta):
            raise ValueError("coevolution signal and delta must be finite")


@dataclass(frozen=True, slots=True)
class CoevolutionUpdate:
    """One validated and applied adaptive component update."""

    scope: str
    owner_id: str | None
    target: str
    signal: str
    before: float
    delta: float
    after: float
    bound: float
    normalized_delta: float


@dataclass(frozen=True, slots=True)
class CoevolutionSnapshot:
    """Immutable state of controlled agent and environment components."""

    version: int
    agent_components: Mapping[str, Mapping[str, float]]
    environment_components: Mapping[str, float]

    def __post_init__(self) -> None:
        if self.version < 0:
            raise ValueError("coevolution snapshot version must be non-negative")
        object.__setattr__(self, "agent_components", freeze_value(self.agent_components))
        object.__setattr__(
            self,
            "environment_components",
            freeze_value(self.environment_components),
        )


@dataclass(frozen=True, slots=True)
class CoevolutionReport:
    """Versioned result and stability diagnostics for one atomic co-evolution call."""

    before_version: int
    after_version: int
    signals: Mapping[str, float]
    updates: tuple[CoevolutionUpdate, ...]
    max_normalized_delta: float

    def __post_init__(self) -> None:
        if self.before_version < 0 or self.after_version < self.before_version:
            raise ValueError("invalid coevolution report versions")
        object.__setattr__(self, "signals", freeze_value(self.signals))
        object.__setattr__(self, "updates", tuple(self.updates))

    @property
    def stable(self) -> bool:
        """Whether all applied updates remained within declared bounds."""

        return self.max_normalized_delta <= 1.0


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
class DDGECandidate:
    """A complete behavior, belief, aggregate, and learned-parameter candidate."""

    policies: Mapping[str, Any]
    beliefs: Mapping[str, Any]
    theta: NDArray[np.floating[Any]]
    aggregates: Mapping[str, Any] = field(default_factory=dict)
    data: Any = None

    def __post_init__(self) -> None:
        theta = np.asarray(self.theta, dtype=float)
        if theta.ndim != 1 or not np.all(np.isfinite(theta)):
            raise ValueError("candidate theta must be a finite one-dimensional array")
        object.__setattr__(self, "policies", freeze_value(self.policies))
        object.__setattr__(self, "beliefs", freeze_value(self.beliefs))
        object.__setattr__(self, "theta", freeze_value(theta))
        object.__setattr__(self, "aggregates", freeze_value(self.aggregates))
        object.__setattr__(self, "data", freeze_value(self.data))


@dataclass(frozen=True, slots=True)
class ConsistencyCheck:
    """One named DDGE consistency residual and its acceptance tolerance."""

    component: str
    residual: float
    tolerance: float

    def __post_init__(self) -> None:
        if not self.component:
            raise ValueError("consistency component must not be empty")
        if not isfinite(self.residual) or self.residual < 0.0:
            raise ValueError("consistency residual must be finite and non-negative")
        if not isfinite(self.tolerance) or self.tolerance < 0.0:
            raise ValueError("consistency tolerance must be finite and non-negative")

    @property
    def passed(self) -> bool:
        """Whether this component is consistent at its declared tolerance."""

        return self.residual <= self.tolerance


@dataclass(frozen=True, slots=True)
class DDGEConsistencyCertificate:
    """Separate evidence for every condition in Cong's DDGE definition."""

    candidate: DDGECandidate
    checks: tuple[ConsistencyCheck, ...]

    def __post_init__(self) -> None:
        checks = tuple(self.checks)
        names = tuple(check.component for check in checks)
        if not checks:
            raise ValueError("a DDGE certificate must contain checks")
        if len(names) != len(set(names)):
            raise ValueError("DDGE certificate components must be unique")
        object.__setattr__(self, "checks", checks)

    @property
    def consistent(self) -> bool:
        """Whether every certified DDGE condition passes."""

        return all(check.passed for check in self.checks)

    @property
    def failed_components(self) -> tuple[str, ...]:
        """Names of conditions whose residual exceeds its tolerance."""

        return tuple(check.component for check in self.checks if not check.passed)

    @property
    def max_residual(self) -> float:
        """Largest raw component residual in this certificate."""

        return max(check.residual for check in self.checks)

    def check(self, component: str) -> ConsistencyCheck:
        """Return one named component check."""

        for check in self.checks:
            if check.component == component:
                return check
        raise KeyError(f"unknown consistency component {component!r}")


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
