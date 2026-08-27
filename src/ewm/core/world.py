"""Deterministic synchronous runtime for executable economic worlds."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

import numpy as np

from .constraints import ConstraintSet
from .events import EventLog
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

    @property
    def events(self) -> EventLog:
        return self._events

    @property
    def agent_ids(self) -> tuple[str, ...]:
        return tuple(agent.agent_id for agent in self._agents)

    def reset(self, seed: int | None = None) -> Any:
        self._rng = make_rng(seed)
        self._events = EventLog()
        state = freeze_value(self._initial_state(self._rng))
        self._events.append("reset", {"seed": seed, "agent_ids": self.agent_ids})
        return state

    def observe(self, state: Any, agent_id: str) -> Any:
        if agent_id not in self.agent_ids:
            raise KeyError(f"unknown agent {agent_id!r}")
        return freeze_value(self._observation(state, agent_id))

    def run_agents(self, state: Any) -> tuple[Action, ...]:
        actions = tuple(
            agent.act(self.observe(state, agent.agent_id), self._rng) for agent in self._agents
        )
        self._events.append("actions", {"agent_ids": tuple(a.agent_id for a in actions)})
        return actions

    def step(self, state: Any, actions: tuple[Action, ...]) -> Transition:
        working_state = thaw_value(state)
        accepted, violations = self._constraints.validate(working_state, tuple(actions))
        scheduled = tuple(sorted(accepted, key=lambda action: (action.agent_id, action.kind)))
        next_state, outcomes = self._mechanism.clear(working_state, scheduled, self._rng)
        transition = Transition(
            state=next_state,
            outcomes=outcomes,
            accepted_actions=scheduled,
            violations=violations,
            diagnostics={
                "submitted_count": len(actions),
                "accepted_count": len(scheduled),
                "violation_count": len(violations),
            },
        )
        self._events.append(
            "transition",
            {
                "submitted_count": len(actions),
                "accepted_count": len(scheduled),
                "violation_count": len(violations),
            },
        )
        return transition
