"""Provider-neutral cognitive economic agents with explicit reliability boundaries."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Protocol, cast

import numpy as np

from ewm.core import Action, AgentSpecification
from ewm.core.records import freeze_value


class CognitiveActionError(RuntimeError):
    """Raised when a cognitive backend cannot produce a valid economic action."""


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """One bounded, immutable decision-memory entry."""

    observation: Mapping[str, Any]
    action: Action
    beliefs: Mapping[str, Any]
    rationale: str
    request_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "observation", freeze_value(self.observation))
        object.__setattr__(self, "beliefs", freeze_value(self.beliefs))


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """Complete provider-neutral context for one model attempt."""

    agent_id: str
    role: str
    objective: str
    observation: Mapping[str, Any]
    beliefs: Mapping[str, Any]
    memory: tuple[MemoryEntry, ...]
    allowed_actions: tuple[str, ...]
    tool_results: Mapping[str, Any]
    attempt: int
    max_attempts: int
    random_seed: int
    prior_error: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "observation", freeze_value(self.observation))
        object.__setattr__(self, "beliefs", freeze_value(self.beliefs))
        object.__setattr__(self, "memory", tuple(self.memory))
        object.__setattr__(self, "allowed_actions", tuple(self.allowed_actions))
        object.__setattr__(self, "tool_results", freeze_value(self.tool_results))


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """Structured response expected from a provider adapter."""

    action_kind: str
    action_values: Mapping[str, Any]
    belief_updates: Mapping[str, Any]
    rationale: str
    request_id: str

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValueError("model response request_id must not be empty")
        object.__setattr__(self, "action_values", freeze_value(self.action_values))
        object.__setattr__(self, "belief_updates", freeze_value(self.belief_updates))


class LanguageModelBackend(Protocol):
    """Small injectable boundary implemented by deterministic fakes or provider adapters."""

    @property
    def name(self) -> str: ...

    @property
    def model(self) -> str: ...

    def complete(self, request: ModelRequest) -> ModelResponse: ...


class CognitiveTool(Protocol):
    """Declared deterministic tool available to one cognitive agent."""

    @property
    def name(self) -> str: ...

    def invoke(self, observation: Mapping[str, Any]) -> Any: ...


@dataclass(frozen=True, slots=True)
class FunctionalCognitiveTool:
    """Cognitive tool backed by an explicit callable."""

    name: str
    function: Callable[[Mapping[str, Any]], Any]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("tool name must not be empty")

    def invoke(self, observation: Mapping[str, Any]) -> Any:
        return self.function(observation)


@dataclass(frozen=True, slots=True)
class ActionSchema:
    """Required action fields and optional scalar bounds."""

    required_values: Mapping[str, tuple[str, ...]]
    numeric_bounds: Mapping[str, tuple[float, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required = {
            kind: tuple(fields) for kind, fields in self.required_values.items()
        }
        if not required or any(not kind for kind in required):
            raise ValueError("action schema requires named action kinds")
        if any(
            len(fields) != len(set(fields)) or any(not field for field in fields)
            for fields in required.values()
        ):
            raise ValueError("action schema fields must be nonempty and unique")
        bounds = {name: tuple(value) for name, value in self.numeric_bounds.items()}
        for name, value in bounds.items():
            if "." not in name or len(value) != 2:
                raise ValueError("numeric bound keys must be 'action.field' pairs")
            lower, upper = value
            if not isfinite(lower) or not isfinite(upper) or lower > upper:
                raise ValueError("numeric action bounds must be finite and ordered")
            kind, field = name.split(".", maxsplit=1)
            if kind not in required or field not in required[kind]:
                raise ValueError(f"numeric bound references unknown field {name!r}")
        object.__setattr__(self, "required_values", freeze_value(required))
        object.__setattr__(self, "numeric_bounds", freeze_value(bounds))

    @property
    def action_kinds(self) -> tuple[str, ...]:
        return tuple(self.required_values)

    def validate(self, kind: str, values: Mapping[str, Any]) -> None:
        """Reject undeclared kinds, malformed fields, and out-of-range values."""

        if kind not in self.required_values:
            raise ValueError(f"action kind {kind!r} is not declared")
        expected = set(self.required_values[kind])
        received = set(values)
        if received != expected:
            raise ValueError(
                f"action {kind!r} values must be {sorted(expected)}, got {sorted(received)}"
            )
        for value_name in expected:
            bound = self.numeric_bounds.get(f"{kind}.{value_name}")
            if bound is None:
                continue
            value = values[value_name]
            if not isinstance(value, int | float) or isinstance(value, bool):
                raise ValueError(f"action value {kind}.{value_name} must be numeric")
            number = float(value)
            if not isfinite(number) or not bound[0] <= number <= bound[1]:
                raise ValueError(
                    f"action value {kind}.{value_name} must lie in "
                    f"[{bound[0]}, {bound[1]}]"
                )


@dataclass(frozen=True, slots=True)
class DecisionProvenance:
    """Backend, attempts, requests, tools, and seed used for one accepted decision."""

    backend: str
    model: str
    attempts: int
    request_ids: tuple[str, ...]
    tools: tuple[str, ...]
    random_seed: int


@dataclass(frozen=True, slots=True)
class CognitiveDecision:
    """Accepted typed action plus post-decision belief and provenance state."""

    action: Action
    beliefs: Mapping[str, Any]
    memory_size: int
    provenance: DecisionProvenance

    def __post_init__(self) -> None:
        object.__setattr__(self, "beliefs", freeze_value(self.beliefs))


class CognitiveAgent:
    """Stateful economic agent using an injectable structured-response backend."""

    def __init__(
        self,
        *,
        agent_id: str,
        specification: AgentSpecification,
        backend: LanguageModelBackend,
        initial_beliefs: Mapping[str, Any],
        tools: Mapping[str, CognitiveTool],
        action_schema: ActionSchema,
        max_attempts: int = 2,
    ) -> None:
        if not agent_id:
            raise ValueError("cognitive agent_id must not be empty")
        if not initial_beliefs:
            raise ValueError("cognitive agent requires explicit initial beliefs")
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if set(tools) != set(specification.tools):
            raise ValueError("tool registry must exactly match declared agent tools")
        if set(action_schema.action_kinds) != set(specification.action_space):
            raise ValueError("action schema must exactly cover the declared action_space")
        self._agent_id = agent_id
        self._specification = specification
        self._backend = backend
        self._beliefs = dict(initial_beliefs)
        self._tools = dict(tools)
        self._action_schema = action_schema
        self._max_attempts = max_attempts
        self._memory: list[MemoryEntry] = []
        self._last_decision: CognitiveDecision | None = None

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def beliefs(self) -> Mapping[str, Any]:
        return cast(Mapping[str, Any], freeze_value(self._beliefs))

    @property
    def memory(self) -> tuple[MemoryEntry, ...]:
        return tuple(self._memory)

    @property
    def last_decision(self) -> CognitiveDecision | None:
        return self._last_decision

    def _observe(self, observation: Any) -> Mapping[str, Any]:
        if not isinstance(observation, Mapping):
            raise CognitiveActionError("cognitive observation must be a channel mapping")
        filtered: dict[str, dict[str, Any]] = {}
        for channel, signals in self._specification.information_channels.items():
            source = observation.get(channel)
            if not isinstance(source, Mapping):
                raise CognitiveActionError(f"missing observation channel {channel!r}")
            missing = set(signals).difference(source)
            if missing:
                raise CognitiveActionError(
                    f"channel {channel!r} is missing signals {sorted(missing)}"
                )
            filtered[channel] = {signal: source[signal] for signal in signals}
        return cast(Mapping[str, Any], freeze_value(filtered))

    def _tool_results(self, observation: Mapping[str, Any]) -> Mapping[str, Any]:
        return cast(
            Mapping[str, Any],
            freeze_value(
                {
                    name: self._tools[name].invoke(observation)
                    for name in self._specification.tools
                }
            ),
        )

    def act(self, observation: Any, rng: np.random.Generator) -> Action:
        """Generate, validate, and atomically commit one cognitive decision."""

        filtered = self._observe(observation)
        tool_results = self._tool_results(filtered)
        random_seed = int(rng.integers(0, np.iinfo(np.uint32).max))
        prior_error: str | None = None
        request_ids: list[str] = []

        for attempt in range(1, self._max_attempts + 1):
            request = ModelRequest(
                agent_id=self.agent_id,
                role=self._specification.role,
                objective=self._specification.objective,
                observation=filtered,
                beliefs=self._beliefs,
                memory=tuple(self._memory),
                allowed_actions=self._specification.action_space,
                tool_results=tool_results,
                attempt=attempt,
                max_attempts=self._max_attempts,
                random_seed=(random_seed + attempt - 1) % np.iinfo(np.uint32).max,
                prior_error=prior_error,
            )
            try:
                response = self._backend.complete(request)
                request_ids.append(response.request_id)
                self._action_schema.validate(
                    response.action_kind,
                    response.action_values,
                )
                unknown_beliefs = set(response.belief_updates).difference(self._beliefs)
                if unknown_beliefs:
                    raise ValueError(
                        f"response updates undeclared beliefs {sorted(unknown_beliefs)}"
                    )
            except Exception as error:
                prior_error = str(error)
                continue

            action = Action(
                agent_id=self.agent_id,
                kind=response.action_kind,
                values=response.action_values,
            )
            beliefs = {**self._beliefs, **response.belief_updates}
            entry = MemoryEntry(
                observation=filtered,
                action=action,
                beliefs=beliefs,
                rationale=response.rationale,
                request_id=response.request_id,
            )
            memory = [*self._memory, entry]
            if self._specification.memory_window == 0:
                memory = []
            else:
                memory = memory[-self._specification.memory_window :]
            provenance = DecisionProvenance(
                backend=self._backend.name,
                model=self._backend.model,
                attempts=attempt,
                request_ids=tuple(request_ids),
                tools=tuple(self._specification.tools),
                random_seed=random_seed,
            )
            self._beliefs = beliefs
            self._memory = memory
            self._last_decision = CognitiveDecision(
                action=action,
                beliefs=beliefs,
                memory_size=len(memory),
                provenance=provenance,
            )
            return action

        raise CognitiveActionError(
            f"backend {self._backend.name!r} failed to produce a valid action after "
            f"{self._max_attempts} attempts: {prior_error or 'unknown error'}"
        )
