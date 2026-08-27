"""Structural interfaces for economic worlds, agents, and equilibrium problems."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol, overload

import numpy as np
from numpy.typing import NDArray

from .evaluation import EvaluationReport
from .events import Event
from .records import Action, CoevolutionReport, Transition


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


class InstitutionManifestRecord(Protocol):
    """Read-only institutional artifact identity exposed to the core runtime."""

    @property
    def institution_id(self) -> str: ...

    @property
    def kind(self) -> str: ...

    @property
    def version(self) -> int: ...

    @property
    def content_hash(self) -> str: ...


class InstitutionChangeProposal(Protocol):
    """Minimal proposal interface consumed by a governed institution engine."""

    @property
    def proposal_id(self) -> str: ...

    @property
    def proposer_id(self) -> str: ...

    @property
    def authority(self) -> str: ...

    @property
    def parent_version(self) -> int | None: ...

    @property
    def candidate(self) -> InstitutionManifestRecord: ...


class InstitutionChangeReport(Protocol):
    """Versioned institutional transition fields recorded by the runtime."""

    @property
    def proposal_id(self) -> str: ...

    @property
    def institution_id(self) -> str: ...

    @property
    def accepted(self) -> bool: ...

    @property
    def reasons(self) -> tuple[str, ...]: ...

    @property
    def before_regime_version(self) -> int: ...

    @property
    def after_regime_version(self) -> int: ...

    @property
    def before_institution_version(self) -> int | None: ...

    @property
    def after_institution_version(self) -> int | None: ...


class InstitutionalEvolution(Protocol):
    """Governed transition boundary kept independent of runtime implementation."""

    @property
    def version(self) -> int: ...

    def evolve(self, proposal: InstitutionChangeProposal) -> InstitutionChangeReport: ...

    def rollback(
        self,
        institution_id: str,
        *,
        target_version: int,
        authority: str,
    ) -> InstitutionChangeReport: ...


class ExternalEvidenceRecord(Protocol):
    """Minimal timestamped evidence identity consumed by alignment engines."""

    @property
    def reference(self) -> str: ...


class AlignmentReportRecord(Protocol):
    """Versioned external-evidence alignment result recorded by the runtime."""

    @property
    def evidence_reference(self) -> str: ...

    @property
    def before_version(self) -> int: ...

    @property
    def after_version(self) -> int: ...

    @property
    def within_tolerance(self) -> bool: ...

    @property
    def correction_count(self) -> int: ...

    @property
    def max_discrepancy(self) -> float: ...

    @property
    def max_correction_magnitude(self) -> float: ...


class RealWorldAlignment(Protocol):
    """External-evidence correction boundary independent of provider adapters."""

    @property
    def version(self) -> int: ...

    def align(
        self,
        simulated: Mapping[str, float],
        evidence: ExternalEvidenceRecord,
        *,
        as_of: datetime,
    ) -> AlignmentReportRecord: ...


class EconomicWorld(Protocol):
    """Minimal executable-world boundary."""

    def reset(self, seed: int | None = None) -> Any: ...

    def observe(self, state: Any, agent_id: str) -> Any: ...

    def run_agents(
        self, state: Any, *, parallel: bool = False
    ) -> tuple[Action, ...]: ...

    @overload
    def step(self, actions: tuple[Action, ...], /) -> Transition: ...

    @overload
    def step(self, state: Any, actions: tuple[Action, ...], /) -> Transition: ...

    def evaluate(self) -> EvaluationReport: ...

    def coevolve(
        self,
        state: Any,
        actions: tuple[Action, ...],
        next_state: Any,
    ) -> CoevolutionReport: ...

    def log(self) -> tuple[Event, ...]: ...

    def close(self) -> None: ...


class EquilibriumProblem(Protocol):
    """A fixed-environment equilibrium represented by residual equations."""

    def residual(self, candidate: NDArray[np.floating[Any]]) -> NDArray[np.floating[Any]]: ...


class DDGEProblem(Protocol):
    """A single-valued behavior-data-learning update used by the v0 solver."""

    @property
    def dimension(self) -> int: ...

    def update(self, theta: NDArray[np.floating[Any]]) -> NDArray[np.floating[Any]]: ...
