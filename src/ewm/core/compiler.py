"""Explicit compilation of declarative world specifications into runtimes."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, cast

import numpy as np

from .coevolution import ControlledCoevolution
from .constraints import ConstraintSet
from .contracts import RuntimeContract, SchedulerPolicy, ViolationPolicy
from .protocols import (
    AgentPolicy,
    Constraint,
    InstitutionalEvolution,
    Mechanism,
    RealWorldAlignment,
    StateReconciler,
)
from .records import freeze_value
from .serialization import CanonicalStateCodec, StateCodec
from .specs import AgentSpecification, WorldSpecification
from .world import World

MechanismKey = tuple[str, str, str]
InitialStateFactory = Callable[[np.random.Generator], Any]
AgentFactory = Callable[[AgentSpecification, str], AgentPolicy]
ObservationFactory = Callable[[Any, str], Any]
MechanismFactory = Callable[[WorldSpecification, Mapping[str, Any]], Mechanism]


def mechanism_key(specification: WorldSpecification) -> MechanismKey:
    """Return the executable identity of a declared mechanism."""

    mechanism = specification.environment.mechanism
    return mechanism.type, mechanism.pricing_rule, mechanism.settlement_rule


@dataclass(frozen=True, slots=True)
class RuntimeAdapter:
    """Compile one declared mechanism identity into an executable mechanism."""

    adapter_id: str
    mechanism_key: MechanismKey
    mechanism_factory: MechanismFactory

    def __post_init__(self) -> None:
        if not self.adapter_id:
            raise ValueError("runtime adapter_id must not be empty")
        key = tuple(self.mechanism_key)
        if len(key) != 3 or any(not item for item in key):
            raise ValueError("runtime mechanism_key requires three nonempty names")
        object.__setattr__(self, "mechanism_key", key)


class RuntimeAdapterRegistry:
    """Immutable mechanism-adapter catalog used by the world compiler."""

    __slots__ = ("_adapters",)

    def __init__(self, adapters: Iterable[RuntimeAdapter]) -> None:
        owned = tuple(adapters)
        keys = tuple(adapter.mechanism_key for adapter in owned)
        identifiers = tuple(adapter.adapter_id for adapter in owned)
        if len(keys) != len(set(keys)):
            raise ValueError("runtime mechanism keys must be unique")
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("runtime adapter identifiers must be unique")
        self._adapters: Mapping[MechanismKey, RuntimeAdapter] = MappingProxyType(
            dict(sorted((adapter.mechanism_key, adapter) for adapter in owned))
        )

    @property
    def adapters(self) -> Mapping[MechanismKey, RuntimeAdapter]:
        return self._adapters

    def resolve(self, specification: WorldSpecification) -> RuntimeAdapter:
        """Resolve a compiler or fail at the same explicit mechanism gate as the spec."""

        key = mechanism_key(specification)
        try:
            return self._adapters[key]
        except KeyError as error:
            mechanism = specification.environment.mechanism
            raise NotImplementedError(
                f"no runtime compiler for mechanism {mechanism.type!r} with "
                f"pricing {mechanism.pricing_rule!r} and settlement "
                f"{mechanism.settlement_rule!r}"
            ) from error


@dataclass(frozen=True, slots=True)
class WorldBindings:
    """Executable implementations for every symbolic name in a world specification."""

    initial_state: InitialStateFactory
    agent_factories: Mapping[str, AgentFactory]
    constraints: Mapping[str, Constraint]
    mechanism_options: Mapping[str, Any] = field(default_factory=dict)
    observation: ObservationFactory | None = None
    coevolution: ControlledCoevolution | None = None
    institutional_evolution: InstitutionalEvolution | None = None
    alignment: RealWorldAlignment | None = None
    state_reconciler: StateReconciler | None = None
    intervention: Any = None
    state_codec: StateCodec = field(default_factory=CanonicalStateCodec)

    def __post_init__(self) -> None:
        if not callable(self.initial_state):
            raise TypeError("initial_state must be callable")
        if not isinstance(self.state_codec, StateCodec):
            raise TypeError("state_codec must implement the StateCodec protocol")
        factories = dict(self.agent_factories)
        constraints = dict(self.constraints)
        if any(not name for name in factories):
            raise ValueError("agent factory roles must not be empty")
        if any(not name for name in constraints):
            raise ValueError("constraint binding names must not be empty")
        mismatched = sorted(
            name for name, constraint in constraints.items() if constraint.name != name
        )
        if mismatched:
            raise ValueError(f"constraint binding keys must match constraint names: {mismatched}")
        object.__setattr__(self, "agent_factories", MappingProxyType(factories))
        object.__setattr__(self, "constraints", MappingProxyType(constraints))
        object.__setattr__(
            self,
            "mechanism_options",
            cast(Mapping[str, Any], freeze_value(self.mechanism_options)),
        )
        object.__setattr__(self, "intervention", freeze_value(self.intervention))


def _validate_bindings(
    specification: WorldSpecification,
    bindings: WorldBindings,
) -> None:
    declared_roles = set(specification.roles)
    provided_roles = set(bindings.agent_factories)
    missing_roles = sorted(declared_roles.difference(provided_roles))
    if missing_roles:
        raise ValueError(f"missing agent factories: {missing_roles}")
    unknown_roles = sorted(provided_roles.difference(declared_roles))
    if unknown_roles:
        raise ValueError(f"agent factories declared for unknown roles: {unknown_roles}")

    declared_constraints = set(specification.environment.constraints.rules)
    provided_constraints = set(bindings.constraints)
    missing_constraints = sorted(declared_constraints.difference(provided_constraints))
    if missing_constraints:
        raise ValueError(f"missing constraint bindings: {missing_constraints}")
    unknown_constraints = sorted(provided_constraints.difference(declared_constraints))
    if unknown_constraints:
        raise ValueError(
            f"constraint bindings declared for unknown rules: {unknown_constraints}"
        )

    unknown_priority_roles = sorted(
        set(specification.environment.scheduler.priority).difference(declared_roles)
    )
    if unknown_priority_roles:
        raise ValueError(
            f"runtime scheduler priority has unknown roles: {unknown_priority_roles}"
        )

    if specification.coevolution is not None and bindings.coevolution is None:
        raise ValueError("world specification requires a coevolution binding")
    if specification.coevolution is None and bindings.coevolution is not None:
        raise ValueError("coevolution binding has no declarative specification")
    if specification.alignment is not None and bindings.alignment is None:
        raise ValueError("world specification requires an alignment binding")
    if specification.alignment is None and bindings.alignment is not None:
        raise ValueError("alignment binding has no declarative specification")


def compile_world(
    specification: WorldSpecification,
    *,
    bindings: WorldBindings,
    adapters: RuntimeAdapterRegistry,
) -> World:
    """Compile a validated declaration and explicit bindings into an executable world."""

    _validate_bindings(specification, bindings)
    adapter = adapters.resolve(specification)

    agents: list[AgentPolicy] = []
    agent_roles: dict[str, str] = {}
    action_kinds: dict[str, frozenset[str]] = {}
    for agent_specification in specification.agents:
        factory = bindings.agent_factories[agent_specification.role]
        for agent_id in agent_specification.instance_ids:
            agent = factory(agent_specification, agent_id)
            if agent.agent_id != agent_id:
                raise ValueError(
                    f"agent factory for role {agent_specification.role!r} returned "
                    f"agent {agent.agent_id!r} for {agent_id!r}"
                )
            agents.append(agent)
            agent_roles[agent_id] = agent_specification.role
            action_kinds[agent_id] = frozenset(agent_specification.action_space)

    scheduler = specification.environment.scheduler
    runtime_contract = RuntimeContract(
        agent_roles=agent_roles,
        action_kinds=action_kinds,
        scheduler_policy=cast(SchedulerPolicy, scheduler.policy),
        scheduler_priority=scheduler.priority,
        violation_policy=cast(
            ViolationPolicy,
            specification.environment.constraints.violation_policy,
        ),
    )

    ordered_constraints = tuple(
        bindings.constraints[name]
        for name in specification.environment.constraints.rules
    )
    executable_mechanism = adapter.mechanism_factory(
        specification,
        bindings.mechanism_options,
    )
    return World(
        initial_state=bindings.initial_state,
        agents=agents,
        mechanism=executable_mechanism,
        constraints=ConstraintSet(ordered_constraints),
        observation=bindings.observation,
        coevolution=bindings.coevolution,
        institutional_evolution=bindings.institutional_evolution,
        alignment=bindings.alignment,
        state_reconciler=bindings.state_reconciler,
        intervention=bindings.intervention,
        runtime_contract=runtime_contract,
        state_codec=bindings.state_codec,
    )
