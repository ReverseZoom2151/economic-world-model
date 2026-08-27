from __future__ import annotations

from types import MappingProxyType

import pytest

import ewm
from ewm.core import (
    Action,
    FunctionalAgent,
    FunctionalConstraint,
    FunctionalMechanism,
    RuntimeAdapter,
    RuntimeAdapterRegistry,
    World,
    WorldBindings,
    WorldSpecification,
)

MECHANISM_KEY = (
    "batch_clearing",
    "uniform_clearing",
    "cash_asset_delivery",
)


def _specification(*, count: int = 2) -> WorldSpecification:
    participant = ewm.agent(
        role="trader",
        objective="Add a feasible amount to the aggregate.",
        state_variables=["balance"],
        information_channels={"public": ["total"]},
        action_space=["add", "hold"],
        constraints=["non_negative"],
        count=count,
    )
    environment = ewm.environment(
        state=ewm.state(
            variables={"total": 0.0},
            accounts={"trader": {"balance": 10.0}},
        ),
        constraints=ewm.constraints(rules=["non_negative"]),
        scheduler=ewm.scheduler(policy="deterministic"),
        mechanism=ewm.mechanism(
            type=MECHANISM_KEY[0],
            participants=["trader"],
            input_actions=["add"],
            pricing_rule=MECHANISM_KEY[1],
            settlement_rule=MECHANISM_KEY[2],
        ),
    )
    declared = ewm.make("compiler-fixture", agents=[participant], environment=environment)
    assert isinstance(declared, WorldSpecification)
    return declared


def _bindings() -> WorldBindings:
    def agent_factory(_specification, agent_id):
        return FunctionalAgent(
            agent_id,
            lambda _state, _rng: Action(agent_id, "add", {"amount": 1.5}),
        )

    return WorldBindings(
        initial_state=lambda _rng: {"total": 0.0},
        agent_factories={"trader": agent_factory},
        constraints={
            "non_negative": FunctionalConstraint(
                "non_negative",
                lambda _state, action: (
                    "amount must be non-negative"
                    if float(action.values["amount"]) < 0.0
                    else None
                ),
            )
        },
    )


def _registry() -> RuntimeAdapterRegistry:
    def mechanism_factory(_specification, options):
        increment = float(options.get("increment", 0.0))

        def clear(state, actions, _rng):
            state["total"] += increment + sum(
                float(action.values["amount"]) for action in actions
            )
            return state, {"accepted": len(actions)}

        return FunctionalMechanism(clear)

    return RuntimeAdapterRegistry(
        (
            RuntimeAdapter(
                adapter_id="fx_uniform_batch_v1",
                mechanism_key=MECHANISM_KEY,
                mechanism_factory=mechanism_factory,
            ),
        )
    )


def test_compile_world_expands_roles_and_executes_the_declared_runtime() -> None:
    bindings = _bindings()
    bindings = WorldBindings(
        initial_state=bindings.initial_state,
        agent_factories=bindings.agent_factories,
        constraints=bindings.constraints,
        mechanism_options={"increment": 0.5},
    )

    world = ewm.compile_world(_specification(), bindings=bindings, adapters=_registry())
    state = world.reset(seed=7)
    actions = world.run_agents(state)
    transition = world.step(actions)

    assert isinstance(world, World)
    assert world.agent_ids == ("trader-0", "trader-1")
    assert tuple(action.agent_id for action in actions) == world.agent_ids
    assert transition.state["total"] == pytest.approx(3.5)
    assert transition.outcomes["accepted"] == 2


def test_world_bindings_and_adapter_registry_take_immutable_ownership() -> None:
    factories = dict(_bindings().agent_factories)
    adapters = list(_registry().adapters.values())

    bindings = WorldBindings(
        initial_state=lambda _rng: {"total": 0.0},
        agent_factories=factories,
        constraints=_bindings().constraints,
    )
    registry = RuntimeAdapterRegistry(adapters)
    factories.clear()
    adapters.clear()

    assert isinstance(bindings.agent_factories, MappingProxyType)
    assert isinstance(registry.adapters, MappingProxyType)
    assert tuple(bindings.agent_factories) == ("trader",)
    assert tuple(registry.adapters) == (MECHANISM_KEY,)


def test_compile_world_rejects_incomplete_or_mismatched_bindings_before_execution() -> None:
    bindings = _bindings()
    incomplete = WorldBindings(
        initial_state=bindings.initial_state,
        agent_factories={},
        constraints={},
    )

    with pytest.raises(ValueError, match=r"missing agent factories: \['trader'\]"):
        ewm.compile_world(_specification(), bindings=incomplete, adapters=_registry())

    bad_factory = WorldBindings(
        initial_state=bindings.initial_state,
        agent_factories={
            "trader": lambda _specification, _agent_id: FunctionalAgent(
                "wrong-id",
                lambda _state, _rng: Action("wrong-id", "hold"),
            )
        },
        constraints=bindings.constraints,
    )
    with pytest.raises(ValueError, match="returned agent 'wrong-id' for 'trader-0'"):
        ewm.compile_world(_specification(), bindings=bad_factory, adapters=_registry())


def test_compile_world_uses_the_same_explicit_unsupported_mechanism_gate() -> None:
    empty_registry = RuntimeAdapterRegistry(())

    with pytest.raises(NotImplementedError, match="batch_clearing"):
        ewm.compile_world(
            _specification(),
            bindings=_bindings(),
            adapters=empty_registry,
        )


def test_compiler_rejects_runtime_semantics_not_yet_implemented_by_world() -> None:
    specification = _specification()
    submission_order = ewm.environment(
        state=specification.environment.state,
        constraints=specification.environment.constraints,
        scheduler=ewm.scheduler(policy="submission_order"),
        mechanism=specification.environment.mechanism,
    )
    declared = ewm.make(
        "unsupported-scheduler",
        agents=specification.agents,
        environment=submission_order,
    )
    assert isinstance(declared, WorldSpecification)

    with pytest.raises(NotImplementedError, match="scheduler policy 'submission_order'"):
        ewm.compile_world(declared, bindings=_bindings(), adapters=_registry())
