"""Compatibility contracts that make internal package reorganization safe."""

from __future__ import annotations

from importlib import import_module

import ewm
from ewm.capabilities.readiness import (
    DEFAULT_HAN_L3_L6_PROTOCOL,
    load_han_l3_l6_protocol,
)
from ewm.core import World
from ewm.experiments.protocols import DEFAULT_PROTOCOL_PATH, load_protocol
from ewm.experiments.registry import ExperimentSpec, ScenarioPlugin, ScenarioRegistry
from ewm.ontology.profiles import DEFAULT_PROFILES
from ewm.scenarios.fx.validation import (
    DEFAULT_HAN_L1_L2_PROTOCOL,
    load_han_l1_l2_protocol,
)
from scripts.run_conformance import DEFAULT_SOURCE_DIR as CONFORMANCE_SOURCE_DIR
from scripts.verify_sources import DEFAULT_SOURCE_DIR as VERIFICATION_SOURCE_DIR

ROOT_EXPORTS = (
    "ExperimentRun",
    "ScenarioHandle",
    "__version__",
    "agent",
    "agent_updates",
    "alignment",
    "coevolution",
    "compile_world",
    "constraints",
    "correction",
    "data_sources",
    "describe",
    "environment",
    "environment_updates",
    "evaluation",
    "export_replay",
    "list_experiments",
    "list_scenarios",
    "make",
    "mechanism",
    "replay_world",
    "rollout",
    "run_experiment",
    "scheduler",
    "solve_ddge",
    "solve_equilibrium",
    "state",
)


def test_root_exports_remain_an_exact_ordered_compatibility_surface() -> None:
    assert tuple(ewm.__all__) == ROOT_EXPORTS
    assert all(hasattr(ewm, name) for name in ROOT_EXPORTS)


def test_historical_direct_modules_resolve_to_the_aggregate_objects() -> None:
    direct_world = import_module("ewm.core.world").World
    direct_registry = import_module("ewm.experiments.registry")

    assert direct_world is World
    assert World.__module__ == "ewm.core.world"
    assert direct_registry.ExperimentSpec is ExperimentSpec
    assert direct_registry.ScenarioPlugin is ScenarioPlugin
    assert direct_registry.ScenarioRegistry is ScenarioRegistry
    assert ExperimentSpec.__module__ == "ewm.experiments.registry"
    assert ScenarioPlugin.__module__ == "ewm.experiments.registry"
    assert ScenarioRegistry.__module__ == "ewm.experiments.registry"


def test_all_three_installed_protocol_resources_load_from_stable_paths() -> None:
    scientific = load_protocol(DEFAULT_PROTOCOL_PATH)
    lower_levels = load_han_l1_l2_protocol()
    higher_levels = load_han_l3_l6_protocol()

    assert DEFAULT_PROTOCOL_PATH.as_posix().endswith(
        "ewm/protocols/credit-mechanism-v1.toml"
    )
    assert DEFAULT_HAN_L1_L2_PROTOCOL.as_posix().endswith(
        "ewm/scenarios/fx/han-l1-l2-validation-v1.toml"
    )
    assert DEFAULT_HAN_L3_L6_PROTOCOL.as_posix().endswith(
        "ewm/capabilities/han-l3-l6-readiness-v1.toml"
    )
    assert scientific.protocol_version == 1
    assert lower_levels.schema_version == "ewm.han-l1-l2.protocol.v1"
    assert higher_levels.schema_version == "ewm.han-l3-l6-readiness.protocol.v1"


def test_ontology_profile_code_symbols_remain_identity_stable() -> None:
    assert tuple(
        f"{type(profile).__module__}.{type(profile).__qualname__}"
        for profile in DEFAULT_PROFILES
    ) == (
        "ewm.ontology.profiles.credit.CreditOntologyProfile",
        "ewm.ontology.profiles.forecasting.ForecastingOntologyProfile",
        "ewm.ontology.profiles.fx.FXOntologyProfile",
        "ewm.ontology.profiles.production.ProductionOntologyProfile",
        "ewm.ontology.profiles.scalar.ScalarOntologyProfile",
    )


def test_local_paper_sources_have_one_ignored_reference_location() -> None:
    expected = "references/local"

    assert CONFORMANCE_SOURCE_DIR.as_posix().endswith(expected)
    assert VERIFICATION_SOURCE_DIR == CONFORMANCE_SOURCE_DIR
