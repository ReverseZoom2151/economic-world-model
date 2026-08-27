from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import ewm
from ewm.core import Action, verify_event_chain
from ewm.scenarios.fx import (
    FXSimulationResult,
    FXState,
    FXStateCodec,
    FXWorldBlueprint,
    fx_world_blueprint,
    run_fx_simulation,
    run_fx_world,
    smoke_config,
)


@pytest.mark.parametrize(
    ("payload", "message"),
    (
        ({}, "accounts"),
        (
            {
                "accounts": [],
                "beliefs": {},
                "period": 0,
                "price_history": (1.0,),
                "spot": 1.0,
            },
            "accounts",
        ),
        (
            {
                "accounts": {"bank-0": []},
                "beliefs": {},
                "period": 0,
                "price_history": (1.0,),
                "spot": 1.0,
            },
            "account record",
        ),
        (
            {
                "accounts": {"bank-0": {"cash": 1.0, "foreign": 1.0}},
                "beliefs": {
                    "household-0": {
                        "expected_return": 0.0,
                        "observations": "not-a-sequence",
                    }
                },
                "period": 0,
                "price_history": (1.0,),
                "spot": 1.0,
            },
            "observations",
        ),
    ),
)
def test_fx_state_codec_rejects_malformed_container_shapes(
    payload: object,
    message: str,
) -> None:
    with pytest.raises(TypeError, match=message):
        FXStateCodec().decode(payload)


def test_seeded_fx_outputs_are_characterized_before_runtime_migration() -> None:
    config = smoke_config(periods=5)

    adaptive = run_fx_simulation(config, seed=42)
    fixed = run_fx_simulation(replace(config, adaptive_beliefs=False), seed=42)

    assert adaptive == FXSimulationResult(
        prices=(
            1.0,
            1.002,
            1.004004,
            1.001995992,
            1.003999983984,
            1.0019919840160318,
        ),
        volumes=(6.0, 5.0, 6.0, 5.0, 6.0),
        rejected_orders=(0, 0, 0, 0, 0),
        max_cash_residual=1.4551915228366852e-11,
        max_foreign_residual=1.4551915228366852e-11,
    )
    assert fixed == FXSimulationResult(
        prices=(
            1.0,
            1.002,
            0.999996,
            1.001995992,
            0.9999920000159999,
            1.0019919840160318,
        ),
        volumes=(6.0, 6.0, 7.0, 5.0, 7.0),
        rejected_orders=(0, 0, 0, 0, 0),
        max_cash_residual=1.4551915228366852e-11,
        max_foreign_residual=0.0,
    )


def test_fx_blueprint_compiles_bank_batch_and_adaptive_belief_state() -> None:
    config = smoke_config(periods=2)
    blueprint = fx_world_blueprint(config)
    world = blueprint.compile()

    assert isinstance(blueprint, FXWorldBlueprint)
    with pytest.raises(RuntimeError, match="reset"):
        world.run_agents(FXState(0, 1.0, {}, (1.0,)))

    state = world.reset(seed=42)
    actions = world.run_agents(state)
    bank_action = next(action for action in actions if action.agent_id == "bank-0")

    assert len(actions) == config.households + 2
    assert bank_action.kind == "fx_order_batch"
    assert len(bank_action.values["orders"]) == 2

    transition = world.step(actions)
    next_state = transition.state

    assert isinstance(next_state, FXState)
    assert transition.outcomes["submitted_order_count"] == config.households + 3
    assert next_state.beliefs["household-0"].observations == pytest.approx((0.002,))
    assert verify_event_chain(world.events.snapshot()) == world.events[-1].event_hash


def test_fx_world_run_preserves_result_and_exposes_canonical_events() -> None:
    config = smoke_config(periods=4)

    run = run_fx_world(config, seed=23)

    assert run.result == run_fx_simulation(config, seed=23)
    assert tuple(event.kind for event in run.events) == (
        "reset",
        "run_agents",
        "step",
        "run_agents",
        "step",
        "run_agents",
        "step",
        "run_agents",
        "step",
    )
    assert verify_event_chain(run.events) == run.events[-1].event_hash
    assert run.events[-1].payload["outcomes"]["volume"] == run.result.volumes[-1]


def test_compiled_fx_world_supports_deterministic_replay() -> None:
    blueprint = fx_world_blueprint(smoke_config(periods=2))
    original = blueprint.compile()
    state = original.reset(seed=7)
    for _ in range(2):
        state = original.step(original.run_agents(state)).state
    bundle = ewm.export_replay(original)

    replayed = blueprint.compile()
    report = ewm.replay_world(replayed, bundle)

    assert report.matched
    assert replayed.current_state == original.current_state


def test_fx_experiment_artifact_events_are_canonical_world_events(
    tmp_path: Path,
) -> None:
    run = ewm.run_experiment(
        "fx.rollout",
        preset="smoke",
        seed=42,
        output_root=tmp_path,
    )
    events = tuple(
        json.loads(line)
        for line in (run.run_dir / "events.jsonl").read_text().splitlines()
    )

    assert events[0]["kind"] == "reset"
    assert events[0]["previous_hash"] == "0" * 64
    assert len(events[0]["event_hash"]) == 64
    step = next(event for event in events if event["kind"] == "step")
    assert step["payload"]["outcomes"]["clearing_residual"] == pytest.approx(0.0)
    assert len(step["payload"]["before_state_digest"]) == 64
    assert len(step["payload"]["after_state_digest"]) == 64


def test_fx_world_rejects_external_actions_outside_declared_contract() -> None:
    world = fx_world_blueprint(smoke_config(periods=1)).compile()
    world.reset(seed=1)

    with pytest.raises(ValueError, match="action kind"):
        world.step((Action("bank-0", "undeclared"),))
