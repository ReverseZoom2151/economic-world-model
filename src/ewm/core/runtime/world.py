"""Synchronous runtime for deterministic executable economic worlds."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from copy import deepcopy
from datetime import datetime
from typing import Any, Literal, overload

import numpy as np

from ..assurance.evaluation import EvaluationReport, evaluate_event_log
from ..domain.constraints import ConstraintSet
from ..domain.protocols import (
    AgentPolicy,
    AlignmentReportRecord,
    ExternalEvidenceRecord,
    InstitutionalEvolution,
    InstitutionChangeProposal,
    InstitutionChangeReport,
    Mechanism,
    RealWorldAlignment,
    StateReconciler,
)
from ..domain.records import (
    Action,
    CoevolutionReport,
    CoevolutionSnapshot,
    Transition,
    freeze_value,
    thaw_value,
)
from ..provenance.contracts import RuntimeContract, runtime_contract_digest
from ..provenance.randomness import make_rng
from ..provenance.serialization import (
    StateCodec,
    action_to_data,
    state_digest,
    violation_to_data,
)
from .coevolution import ControlledCoevolution
from .events import Event, EventLog, EventLogView

ProvenanceMode = Literal["full", "summary"]


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
        state_reconciler: StateReconciler | None = None,
        intervention: Any = None,
        runtime_contract: RuntimeContract | None = None,
        state_codec: StateCodec | None = None,
        provenance_mode: ProvenanceMode = "full",
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
        self._state_reconciler = state_reconciler
        self._intervention = intervention
        self._runtime_contract = runtime_contract
        self._state_codec = state_codec
        if runtime_contract is not None and state_codec is None:
            raise ValueError("compiled runtime contract requires a state codec")
        if provenance_mode not in ("full", "summary"):
            raise ValueError("provenance_mode must be 'full' or 'summary'")
        if runtime_contract is None and provenance_mode != "full":
            raise ValueError("summary provenance requires a compiled runtime contract")
        self._provenance_mode = provenance_mode
        if runtime_contract is not None and set(runtime_contract.agent_roles) != set(
            identifiers
        ):
            raise ValueError("runtime contract agents must exactly match world agents")
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
    def events(self) -> EventLogView:
        return EventLogView(self._events)

    @property
    def agent_ids(self) -> tuple[str, ...]:
        return tuple(agent.agent_id for agent in self._agents)

    @property
    def runtime_contract(self) -> RuntimeContract | None:
        """Return strict compiled-world rules, or ``None`` for a direct world."""

        return self._runtime_contract

    @property
    def state_codec(self) -> StateCodec | None:
        """Return the codec attached to a replayable compiled world."""

        return self._state_codec

    @property
    def provenance_mode(self) -> ProvenanceMode:
        """Return whether events carry replay-complete or summary provenance."""

        return self._provenance_mode

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

    def _ensure_ready(self) -> None:
        self._ensure_open()
        if self._runtime_contract is not None and self._state is None:
            raise RuntimeError("compiled world must be reset before runtime operations")

    def _ensure_current_state(self, state: Any) -> None:
        if self._runtime_contract is not None and state is not self._state:
            raise ValueError("state must be the current runtime state")

    def reset(self, seed: int | None = None) -> Any:
        self._ensure_open()
        rng = make_rng(seed)
        state = freeze_value(self._initial_state(rng))
        if self._state_reconciler is not None and not self._state_reconciler.is_feasible(
            state
        ):
            raise ValueError("initial world state is outside the feasible-state set")
        payload: dict[str, Any] = {"seed": seed, "agent_ids": self.agent_ids}
        if self._state_codec is not None and self._provenance_mode == "full":
            payload.update(
                {
                    "state": self._state_codec.encode(state),
                    "state_codec": self._state_codec.codec_id,
                    "state_digest": state_digest(self._state_codec, state),
                }
            )
        if self._runtime_contract is not None:
            payload["runtime_contract_digest"] = runtime_contract_digest(
                self._runtime_contract
            )
        events = EventLog()
        events.append("reset", payload, state_version=0)
        self._rng = rng
        self._events = events
        self._state = state
        self._state_version = 0
        return state

    def observe(self, state: Any, agent_id: str) -> Any:
        self._ensure_ready()
        self._ensure_current_state(state)
        if agent_id not in self.agent_ids:
            raise KeyError(f"unknown agent {agent_id!r}")
        return freeze_value(self._observation(state, agent_id))

    def run_agents(
        self,
        state: Any,
        *,
        parallel: bool = False,
    ) -> tuple[Action, ...]:
        self._ensure_ready()
        self._ensure_current_state(state)
        rng_state = (
            deepcopy(self._rng.bit_generator.state)
            if self._runtime_contract is not None
            else None
        )
        try:
            collected: list[Action] = []
            for agent in self._agents:
                action = agent.act(self.observe(state, agent.agent_id), self._rng)
                if self._runtime_contract is not None:
                    if not isinstance(action, Action):
                        raise TypeError("agent policies must return Action records")
                    self._runtime_contract.validate_agent_action(
                        action,
                        owner_id=agent.agent_id,
                    )
                collected.append(action)
            actions = tuple(collected)
            payload = {
                "agent_ids": tuple(action.agent_id for action in actions),
                "parallel_requested": parallel,
                "parallel_executed": False,
            }
            if self._runtime_contract is not None and self._provenance_mode == "full":
                payload["actions"] = tuple(action_to_data(action) for action in actions)
            self._events.append(
                "run_agents",
                payload,
                state_version=self._state_version if self._state_version >= 0 else None,
            )
        except Exception:
            if rng_state is not None:
                self._rng.bit_generator.state = rng_state
            raise
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
        self._ensure_ready()
        if actions is None:
            state = self._state_after_reset()
            submitted = tuple(state_or_actions)
        else:
            state = state_or_actions
            self._ensure_current_state(state)
            submitted = tuple(actions)
        if any(not isinstance(action, Action) for action in submitted):
            raise TypeError("world.step actions must contain Action records")
        if self._runtime_contract is not None:
            self._runtime_contract.validate_actions(submitted)
        working_state = thaw_value(state)
        accepted, violations = self._constraints.validate(working_state, submitted)
        if (
            self._runtime_contract is not None
            and self._runtime_contract.violation_policy == "raise"
            and violations
        ):
            details = "; ".join(
                f"{violation.constraint} for {violation.agent_id}: {violation.reason}"
                for violation in violations
            )
            raise ValueError(f"constraint violations under 'raise' policy: {details}")
        scheduled = (
            self._runtime_contract.schedule(accepted)
            if self._runtime_contract is not None
            else tuple(sorted(accepted, key=lambda action: (action.agent_id, action.kind)))
        )
        rng_state = (
            deepcopy(self._rng.bit_generator.state)
            if self._runtime_contract is not None
            else None
        )
        try:
            candidate_state, outcomes = self._mechanism.clear(
                working_state, scheduled, self._rng
            )
            next_state = candidate_state
            reconciled = self._state_reconciler is not None
            if self._state_reconciler is not None:
                next_state = self._state_reconciler.reconcile(
                    state,
                    scheduled,
                    self._intervention,
                    candidate_state,
                )
                if not self._state_reconciler.is_feasible(next_state):
                    raise RuntimeError(
                        "state reconciliation returned an infeasible next state"
                    )
            transition = Transition(
                state=next_state,
                outcomes=outcomes,
                accepted_actions=scheduled,
                violations=violations,
                diagnostics={
                    "submitted_count": len(submitted),
                    "accepted_count": len(scheduled),
                    "violation_count": len(violations),
                    "state_reconciled": reconciled,
                },
            )
            next_version = self._state_version + 1
            event_payload: dict[str, Any] = {
                "submitted_count": len(submitted),
                "accepted_count": len(scheduled),
                "violation_count": len(violations),
                "state_reconciled": reconciled,
            }
            if self._runtime_contract is not None and self._provenance_mode == "full":
                if self._state_codec is None:
                    raise RuntimeError("compiled world is missing its state codec")
                event_payload.update(
                    {
                        "accepted_actions": tuple(
                            action_to_data(action) for action in scheduled
                        ),
                        "after_state_digest": state_digest(
                            self._state_codec,
                            transition.state,
                        ),
                        "before_state_digest": state_digest(self._state_codec, state),
                        "diagnostics": transition.diagnostics,
                        "outcomes": transition.outcomes,
                        "submitted_actions": tuple(
                            action_to_data(action) for action in submitted
                        ),
                        "violations": tuple(
                            violation_to_data(violation) for violation in violations
                        ),
                    }
                )
            self._events.append(
                "step",
                event_payload,
                state_version=next_version,
            )
        except Exception:
            if rng_state is not None:
                self._rng.bit_generator.state = rng_state
            raise
        self._state = transition.state
        self._state_version = next_version
        return transition

    def evaluate(self) -> EvaluationReport:
        """Read the event trajectory without mutating economic state or components."""

        self._ensure_ready()
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

        self._ensure_ready()
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

        self._ensure_ready()
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

        self._ensure_ready()
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

        self._ensure_ready()
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

        self._ensure_ready()
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
