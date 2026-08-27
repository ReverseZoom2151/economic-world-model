"""Deterministic synchronous runtime for executable economic worlds."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, overload

import numpy as np

from .constraints import ConstraintSet
from .evaluation import EvaluationReport, evaluate_event_log
from .events import Event, EventLog
from .protocols import AgentPolicy, Mechanism
from .randomness import make_rng
from .records import Action, Transition, freeze_value, thaw_value


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
