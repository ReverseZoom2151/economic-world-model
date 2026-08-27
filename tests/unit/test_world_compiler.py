from __future__ import annotations

from types import MappingProxyType
from typing import Any

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
    make_rng,
)

MECHANISM_KEY = (
    "batch_clearing",
    "uniform_clearing",
    "cash_asset_delivery",
)


def _specification(
    *,
    count: int = 2,
    scheduler_policy: str = "deterministic",
    scheduler_priority: tuple[str, ...] = (),
    violation_policy: str = "reject_and_log",
) -> WorldSpecification:
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
        constraints=ewm.constraints(
            rules=["non_negative"],
            violation_policy=violation_policy,
        ),
        scheduler=ewm.scheduler(
            policy=scheduler_policy,
            priority=scheduler_priority,
        ),
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
            return state, {
                "accepted": len(actions),
                "order": tuple(action.agent_id for action in actions),
            }

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


def test_compiled_world_requires_reset_and_rejects_stale_runtime_state() -> None:
    world = ewm.compile_world(_specification(), bindings=_bindings(), adapters=_registry())

    with pytest.raises(RuntimeError, match="reset"):
        world.run_agents({"total": 0.0})
    with pytest.raises(RuntimeError, match="reset"):
        world.evaluate()
    with pytest.raises(RuntimeError, match="reset"):
        world.log()

    original = world.reset(seed=4)
    world.step(())

    with pytest.raises(ValueError, match="current runtime state"):
        world.observe(original, "trader-0")
    with pytest.raises(ValueError, match="current runtime state"):
        world.run_agents(original)
    with pytest.raises(ValueError, match="current runtime state"):
        world.step(original, ())


@pytest.mark.parametrize(
    ("actions", "message"),
    (
        ((Action("external", "add", {"amount": 1.0}),), "unknown agent"),
        ((Action("trader-0", "withdraw", {"amount": 1.0}),), "action kind"),
        (
            (
                Action("trader-0", "add", {"amount": 1.0}),
                Action("trader-0", "hold", {"amount": 0.0}),
            ),
            "multiple actions",
        ),
    ),
)
def test_compiled_world_enforces_declared_action_contract(
    actions: tuple[Action, ...],
    message: str,
) -> None:
    world = ewm.compile_world(_specification(), bindings=_bindings(), adapters=_registry())
    world.reset(seed=8)

    with pytest.raises(ValueError, match=message):
        world.step(actions)

    assert world.state_version == 0


def test_compiled_world_rejects_an_agent_action_owned_by_another_agent() -> None:
    bindings = _bindings()

    def agent_factory(_specification, agent_id):
        return FunctionalAgent(
            agent_id,
            lambda _state, _rng: Action("trader-1", "add", {"amount": 1.0}),
        )

    wrong_owner = WorldBindings(
        initial_state=bindings.initial_state,
        agent_factories={"trader": agent_factory},
        constraints=bindings.constraints,
    )
    world = ewm.compile_world(
        _specification(),
        bindings=wrong_owner,
        adapters=_registry(),
    )
    state = world.reset(seed=3)

    with pytest.raises(ValueError, match="returned action for 'trader-1'"):
        world.run_agents(state)


def test_compiled_world_applies_submission_order_scheduler() -> None:
    world = ewm.compile_world(
        _specification(scheduler_policy="submission_order"),
        bindings=_bindings(),
        adapters=_registry(),
    )
    world.reset(seed=3)
    submitted = (
        Action("trader-1", "add", {"amount": 1.0}),
        Action("trader-0", "add", {"amount": 2.0}),
    )

    transition = world.step(submitted)

    assert transition.accepted_actions == submitted
    assert transition.outcomes["order"] == ("trader-1", "trader-0")


def test_compiled_world_applies_role_priority_scheduler() -> None:
    buyer = ewm.agent(
        role="buyer",
        objective="Buy first when declared by the scheduler.",
        state_variables=["balance"],
        information_channels={"public": ["total"]},
        action_space=["add"],
        constraints=["non_negative"],
    )
    seller = ewm.agent(
        role="seller",
        objective="Sell after higher-priority roles.",
        state_variables=["balance"],
        information_channels={"public": ["total"]},
        action_space=["add"],
        constraints=["non_negative"],
    )
    environment = ewm.environment(
        state=ewm.state(
            variables={"total": 0.0},
            accounts={
                "buyer": {"balance": 10.0},
                "seller": {"balance": 10.0},
            },
        ),
        constraints=ewm.constraints(rules=["non_negative"]),
        scheduler=ewm.scheduler(policy="role_priority", priority=["buyer"]),
        mechanism=ewm.mechanism(
            type=MECHANISM_KEY[0],
            participants=["buyer", "seller"],
            input_actions=["add"],
            pricing_rule=MECHANISM_KEY[1],
            settlement_rule=MECHANISM_KEY[2],
        ),
    )
    specification = ewm.make(
        "role-priority-fixture",
        agents=[buyer, seller],
        environment=environment,
    )
    assert isinstance(specification, WorldSpecification)

    def agent_factory(_specification, agent_id):
        return FunctionalAgent(
            agent_id,
            lambda _state, _rng: Action(agent_id, "add", {"amount": 1.0}),
        )

    base_bindings = _bindings()
    bindings = WorldBindings(
        initial_state=base_bindings.initial_state,
        agent_factories={"buyer": agent_factory, "seller": agent_factory},
        constraints=base_bindings.constraints,
    )
    world = ewm.compile_world(specification, bindings=bindings, adapters=_registry())
    world.reset(seed=3)

    transition = world.step(
        (
            Action("seller-0", "add", {"amount": 1.0}),
            Action("buyer-0", "add", {"amount": 2.0}),
        )
    )

    assert transition.outcomes["order"] == ("buyer-0", "seller-0")


def test_compiler_rejects_unknown_scheduler_priority_role() -> None:
    with pytest.raises(ValueError, match=r"unknown roles.*market_maker"):
        ewm.compile_world(
            _specification(
                scheduler_policy="role_priority",
                scheduler_priority=("market_maker",),
            ),
            bindings=_bindings(),
            adapters=_registry(),
        )


def test_compiled_world_applies_raise_constraint_violation_policy() -> None:
    world = ewm.compile_world(
        _specification(violation_policy="raise"),
        bindings=_bindings(),
        adapters=_registry(),
    )
    state = world.reset(seed=2)

    with pytest.raises(ValueError, match="non_negative"):
        world.step((Action("trader-0", "add", {"amount": -1.0}),))

    assert world.current_state is state
    assert world.state_version == 0
    assert tuple(event.kind for event in world.events.snapshot()) == ("reset",)


def test_compiled_step_failure_rolls_back_runtime_state_version_and_rng() -> None:
    calls = 0

    def failing_registry() -> RuntimeAdapterRegistry:
        def mechanism_factory(_specification, _options):
            def clear(state: dict[str, Any], _actions, rng):
                nonlocal calls
                state["draw"] = float(rng.normal())
                calls += 1
                if calls == 1:
                    raise RuntimeError("mechanism failed")
                return state, {"draw": state["draw"]}

            return FunctionalMechanism(clear)

        return RuntimeAdapterRegistry(
            (
                RuntimeAdapter(
                    adapter_id="failing_v1",
                    mechanism_key=MECHANISM_KEY,
                    mechanism_factory=mechanism_factory,
                ),
            )
        )

    world = ewm.compile_world(
        _specification(),
        bindings=_bindings(),
        adapters=failing_registry(),
    )
    state = world.reset(seed=17)

    with pytest.raises(RuntimeError, match="mechanism failed"):
        world.step(())

    assert world.current_state is state
    assert world.state_version == 0
    assert tuple(event.kind for event in world.events.snapshot()) == ("reset",)

    transition = world.step(())
    expected_draw = float(make_rng(17).normal())

    assert transition.outcomes["draw"] == expected_draw
