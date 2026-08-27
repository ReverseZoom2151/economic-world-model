"""Deterministic synchronous runtime for executable economic worlds."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import datetime
from typing import Any, overload

import numpy as np

from .coevolution import ControlledCoevolution
from .constraints import ConstraintSet
from .evaluation import EvaluationReport, evaluate_event_log
from .events import Event, EventLog
from .protocols import (
    AgentPolicy,
    AlignmentReportRecord,
    ExternalEvidenceRecord,
    InstitutionalEvolution,
    InstitutionChangeProposal,
    InstitutionChangeReport,
    Mechanism,
    RealWorldAlignment,
)
from .randomness import make_rng
from .records import (
    Action,
    CoevolutionReport,
    CoevolutionSnapshot,
    Transition,
    freeze_value,
    thaw_value,
)


class World:
    """Execute typed agent actions through constraints and an economic mechanism."""

    def __init__(
        self,
        *,
        initial_state: Callable[[np.random.Generator], Any],
        agents: Iterable[AgentPolicy],
        mechanism: Mechanism,
        constraints: ConstraintSet | None = None,
        observation: Callable[[Any, str], Any] | None = None,
        coevolution: ControlledCoevolution | None = None,
        institutional_evolution: InstitutionalEvolution | None = None,
        alignment: RealWorldAlignment | None = None,
    ) -> None:
        ordered_agents = tuple(sorted(agents, key=lambda agent: agent.agent_id))
        identifiers = [agent.agent_id for agent in ordered_agents]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("agent identifiers must be unique")
        self._initial_state = initial_state
        self._agents = ordered_agents
        self._mechanism = mechanism
        self._constraints = constraints or ConstraintSet()
        self._observation = observation or (lambda state, _agent_id: state)
        self._coevolution = coevolution
        self._institutional_evolution = institutional_evolution
        self._alignment = alignment
        if coevolution is not None:
            unknown_agents = set(coevolution.agent_ids).difference(identifiers)
            if unknown_agents:
                raise ValueError(
                    f"coevolution has unknown agents: {sorted(unknown_agents)}"
                )
        self._rng = make_rng(0)
        self._events = EventLog()
        self._state: Any | None = None
        self._state_version = -1
        self._closed = False

    @property
    def events(self) -> EventLog:
        return self._events

    @property
    def agent_ids(self) -> tuple[str, ...]:
        return tuple(agent.agent_id for agent in self._agents)

    @property
    def current_state(self) -> Any:
        """Return the runtime-owned immutable state."""

        if self._state is None:
            raise RuntimeError("world must be reset before reading current_state")
        return self._state

    @property
    def state_version(self) -> int:
        """Monotone state version, starting at zero after reset."""

        return self._state_version

    @property
    def coevolution_state(self) -> CoevolutionSnapshot:
        """Return the controlled adaptive state or report missing configuration."""

        if self._coevolution is None:
            raise RuntimeError("coevolution is not configured")
        return self._coevolution.snapshot

    @property
    def institution_version(self) -> int:
        """Return the active institutional regime version."""

        if self._institutional_evolution is None:
            raise RuntimeError("institutional evolution is not configured")
        return self._institutional_evolution.version

    @property
    def alignment_version(self) -> int:
        """Return the external-alignment component version."""

        if self._alignment is None:
            raise RuntimeError("real-world alignment is not configured")
        return self._alignment.version

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("world is closed")

    def _state_after_reset(self) -> Any:
        if self._state is None:
            raise RuntimeError("world.reset must be called before stateful step")
        return self._state

    def reset(self, seed: int | None = None) -> Any:
        self._ensure_open()
        self._rng = make_rng(seed)
        self._events = EventLog()
        state = freeze_value(self._initial_state(self._rng))
        self._state = state
        self._state_version = 0
        self._events.append(
            "reset",
            {"seed": seed, "agent_ids": self.agent_ids},
            state_version=self._state_version,
        )
        return state

    def observe(self, state: Any, agent_id: str) -> Any:
        self._ensure_open()
        if agent_id not in self.agent_ids:
            raise KeyError(f"unknown agent {agent_id!r}")
        return freeze_value(self._observation(state, agent_id))

    def run_agents(
        self,
        state: Any,
        *,
        parallel: bool = False,
    ) -> tuple[Action, ...]:
        self._ensure_open()
        actions = tuple(
            agent.act(self.observe(state, agent.agent_id), self._rng) for agent in self._agents
        )
        self._events.append(
            "run_agents",
            {
                "agent_ids": tuple(action.agent_id for action in actions),
                "parallel_requested": parallel,
                "parallel_executed": False,
            },
            state_version=self._state_version if self._state_version >= 0 else None,
        )
        return actions

    @overload
    def step(self, actions: tuple[Action, ...], /) -> Transition: ...

    @overload
    def step(self, state: Any, actions: tuple[Action, ...], /) -> Transition: ...

    def step(
        self,
        state_or_actions: Any,
        actions: tuple[Action, ...] | None = None,
        /,
    ) -> Transition:
        self._ensure_open()
        if actions is None:
            state = self._state_after_reset()
            submitted = tuple(state_or_actions)
        else:
            state = state_or_actions
            submitted = tuple(actions)
        if any(not isinstance(action, Action) for action in submitted):
            raise TypeError("world.step actions must contain Action records")
        working_state = thaw_value(state)
        accepted, violations = self._constraints.validate(working_state, submitted)
        scheduled = tuple(sorted(accepted, key=lambda action: (action.agent_id, action.kind)))
        next_state, outcomes = self._mechanism.clear(working_state, scheduled, self._rng)
        transition = Transition(
            state=next_state,
            outcomes=outcomes,
            accepted_actions=scheduled,
            violations=violations,
            diagnostics={
                "submitted_count": len(submitted),
                "accepted_count": len(scheduled),
                "violation_count": len(violations),
            },
        )
        self._state = transition.state
        self._state_version += 1
        self._events.append(
            "step",
            {
                "submitted_count": len(submitted),
                "accepted_count": len(scheduled),
                "violation_count": len(violations),
            },
            state_version=self._state_version,
        )
        return transition

    def evaluate(self) -> EvaluationReport:
        """Read the event trajectory without mutating economic state or components."""

        self._ensure_open()
        self._events.append(
            "evaluate",
            {},
            state_version=self._state_version if self._state_version >= 0 else None,
        )
        return evaluate_event_log(
            self._events.snapshot(),
            state_version=self._state_version,
        )

    def coevolve(
        self,
        state: Any,
        actions: tuple[Action, ...],
        next_state: Any,
    ) -> CoevolutionReport:
        """Apply controlled agent and environment updates from realized feedback."""

        self._ensure_open()
        if self._coevolution is None:
            raise RuntimeError("coevolution is not configured")
        report = self._coevolution.evolve(state, tuple(actions), next_state)
        self._events.append(
            "coevolve",
            {
                "before_version": report.before_version,
                "after_version": report.after_version,
                "update_count": len(report.updates),
                "max_normalized_delta": report.max_normalized_delta,
                "stable": report.stable,
            },
            state_version=self._state_version if self._state_version >= 0 else None,
        )
        return report

    def evolve_institutions(
        self,
        proposal: InstitutionChangeProposal,
    ) -> InstitutionChangeReport:
        """Apply a governed institutional proposal and log its regime identity."""

        self._ensure_open()
        if self._institutional_evolution is None:
            raise RuntimeError("institutional evolution is not configured")
        report = self._institutional_evolution.evolve(proposal)
        self._record_institution_report(report)
        return report

    def rollback_institution(
        self,
        institution_id: str,
        *,
        target_version: int,
        authority: str,
    ) -> InstitutionChangeReport:
        """Roll back to an approved institution version and log the regime change."""

        self._ensure_open()
        if self._institutional_evolution is None:
            raise RuntimeError("institutional evolution is not configured")
        report = self._institutional_evolution.rollback(
            institution_id,
            target_version=target_version,
            authority=authority,
        )
        self._record_institution_report(report)
        return report

    def _record_institution_report(self, report: InstitutionChangeReport) -> None:
        self._events.append(
            "institution_evolve",
            {
                "accepted": report.accepted,
                "after_institution_version": report.after_institution_version,
                "after_regime_version": report.after_regime_version,
                "before_institution_version": report.before_institution_version,
                "before_regime_version": report.before_regime_version,
                "institution_id": report.institution_id,
                "proposal_id": report.proposal_id,
                "reasons": report.reasons,
            },
            state_version=self._state_version if self._state_version >= 0 else None,
        )

    def align(
        self,
        simulated: Mapping[str, float],
        evidence: ExternalEvidenceRecord,
        *,
        as_of: datetime,
    ) -> AlignmentReportRecord:
        """Compare runtime outputs with timestamped evidence and log corrections."""

        self._ensure_open()
        if self._alignment is None:
            raise RuntimeError("real-world alignment is not configured")
        report = self._alignment.align(simulated, evidence, as_of=as_of)
        self._events.append(
            "align",
            {
                "after_version": report.after_version,
                "before_version": report.before_version,
                "correction_count": report.correction_count,
                "evidence_reference": report.evidence_reference,
                "max_correction_magnitude": report.max_correction_magnitude,
                "max_discrepancy": report.max_discrepancy,
                "within_tolerance": report.within_tolerance,
            },
            state_version=self._state_version if self._state_version >= 0 else None,
        )
        return report

    def log(self) -> tuple[Event, ...]:
        """Return an immutable event snapshot after recording the instrumentation call."""

        self._ensure_open()
        self._events.append(
            "log",
            {},
            state_version=self._state_version if self._state_version >= 0 else None,
        )
        return self._events.snapshot()

    def close(self) -> None:
        """Release runtime access; repeated calls are no-ops."""

        if self._closed:
            return
        self._events.append(
            "close",
            {},
            state_version=self._state_version if self._state_version >= 0 else None,
        )
        self._closed = True
