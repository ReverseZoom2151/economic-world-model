from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType

import pytest

from ewm.experiments.registry import (
    EXPERIMENTS,
    SCENARIO_DESCRIPTIONS,
    SCENARIO_REGISTRY,
    ScenarioPlugin,
    ScenarioRegistry,
)


def test_default_registry_is_the_single_immutable_scenario_and_experiment_catalog() -> None:
    assert tuple(SCENARIO_REGISTRY.scenarios) == (
        "credit",
        "forecasting",
        "fx",
        "scalar",
    )
    assert tuple(SCENARIO_REGISTRY.experiments) == (
        "credit.regimes",
        "forecasting.ddge",
        "fx.comparative_statics",
        "fx.rollout",
    )
    assert isinstance(SCENARIO_REGISTRY.scenarios, MappingProxyType)
    assert isinstance(SCENARIO_REGISTRY.experiments, MappingProxyType)
    assert {
        name: plugin.description for name, plugin in SCENARIO_REGISTRY.scenarios.items()
    } == SCENARIO_DESCRIPTIONS
    assert SCENARIO_REGISTRY.experiments == EXPERIMENTS

    with pytest.raises(TypeError):
        SCENARIO_DESCRIPTIONS["new"] = "mutable"  # type: ignore[index]
    with pytest.raises(TypeError):
        EXPERIMENTS["new"] = EXPERIMENTS["fx.rollout"]  # type: ignore[index]


def test_plugins_own_all_and_only_their_scenario_experiments() -> None:
    owned = {
        plugin.name: tuple(spec.name for spec in plugin.experiments)
        for plugin in SCENARIO_REGISTRY.scenarios.values()
    }

    assert owned == {
        "credit": ("credit.regimes",),
        "forecasting": ("forecasting.ddge",),
        "fx": ("fx.comparative_statics", "fx.rollout"),
        "scalar": (),
    }
    assert all(
        plugin.name == experiment.scenario
        for plugin in SCENARIO_REGISTRY.scenarios.values()
        for experiment in plugin.experiments
    )


def test_registry_rejects_duplicate_scenarios_and_misowned_experiments() -> None:
    credit = SCENARIO_REGISTRY.scenario("credit")

    with pytest.raises(ValueError, match="scenario names must be unique"):
        ScenarioRegistry((credit, credit))
    with pytest.raises(ValueError, match="belongs to scenario 'credit'"):
        ScenarioRegistry((replace(credit, name="renamed-credit"),))


def test_a_custom_registry_does_not_mutate_the_default_registry() -> None:
    plugin = ScenarioPlugin(
        name="fixture",
        description="A registry isolation fixture.",
        config_factory=lambda _preset, seed, overrides: {"seed": seed, **overrides},
    )

    custom = ScenarioRegistry((plugin,))

    assert custom.scenario("fixture").configure("smoke", 7, {"value": 2}) == {
        "seed": 7,
        "value": 2,
    }
    assert tuple(custom.scenarios) == ("fixture",)
    assert "fixture" not in SCENARIO_REGISTRY.scenarios


def test_registry_errors_list_stable_sorted_choices() -> None:
    with pytest.raises(
        ValueError,
        match=r"unknown scenario 'missing'; choose from: credit, forecasting, fx, scalar",
    ):
        SCENARIO_REGISTRY.scenario("missing")
    with pytest.raises(
        ValueError,
        match=(
            r"unknown experiment 'missing'; choose from: credit.regimes, "
            r"forecasting.ddge, fx.comparative_statics, fx.rollout"
        ),
    ):
        SCENARIO_REGISTRY.experiment("missing")
