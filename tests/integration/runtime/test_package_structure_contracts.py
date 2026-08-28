"""Compatibility contracts for safe internal package reorganization."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pytest
from ewm.capabilities.readiness import (
    DEFAULT_HAN_L3_L6_PROTOCOL,
    load_han_l3_l6_protocol,
)
from ewm.experiments.protocols import DEFAULT_PROTOCOL_PATH, load_protocol

import ewm
from ewm.conformance import build_report as build_package_conformance_report
from ewm.core import World
from ewm.experiments.registry import ExperimentSpec, ScenarioPlugin, ScenarioRegistry
from ewm.ontology.profiles import DEFAULT_PROFILES
from ewm.scenarios.fx.validation import (
    DEFAULT_HAN_L1_L2_PROTOCOL,
    load_han_l1_l2_protocol,
)
from scripts.run_conformance import (
    DEFAULT_SOURCE_DIR as CONFORMANCE_SOURCE_DIR,
)
from scripts.run_conformance import (
    build_report as build_script_conformance_report,
)
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


def test_conformance_script_is_a_compatibility_entry_point_for_package_logic() -> None:
    assert build_package_conformance_report.__module__ == "ewm.conformance.report"
    assert build_script_conformance_report.__module__ == "scripts.run_conformance"


@pytest.mark.parametrize(
    ("legacy_module", "canonical_module", "symbol"),
    (
        (
            "ewm.capabilities.alignment",
            "ewm.capabilities.engineering.alignment",
            "BoundedAlignment",
        ),
        (
            "ewm.capabilities.cognition",
            "ewm.capabilities.engineering.cognition",
            "CognitiveAgent",
        ),
        (
            "ewm.capabilities.evolution",
            "ewm.capabilities.engineering.evolution",
            "EvolutionRegistry",
        ),
        (
            "ewm.capabilities.institutions",
            "ewm.capabilities.engineering.institutions",
            "GovernedInstitutions",
        ),
        (
            "ewm.capabilities.levels",
            "ewm.capabilities.assessment.levels",
            "CapabilityLevel",
        ),
        (
            "ewm.capabilities.readiness",
            "ewm.capabilities.assessment.readiness",
            "HanReadinessProtocol",
        ),
        (
            "ewm.core.runtime.coevolution",
            "ewm.core.runtime.dynamics.coevolution",
            "ControlledCoevolution",
        ),
        (
            "ewm.core.runtime.interventions",
            "ewm.core.runtime.dynamics.interventions",
            "apply_intervention",
        ),
        (
            "ewm.core.runtime.compiler",
            "ewm.core.runtime.execution.compiler",
            "compile_world",
        ),
        (
            "ewm.core.runtime.kernels",
            "ewm.core.runtime.execution.kernels",
            "CategoricalKernel",
        ),
        (
            "ewm.core.runtime.world",
            "ewm.core.runtime.execution.world",
            "World",
        ),
        (
            "ewm.core.runtime.events",
            "ewm.core.runtime.records.events",
            "Event",
        ),
        (
            "ewm.core.runtime.updates",
            "ewm.core.runtime.records.updates",
            "convex_update",
        ),
        ("ewm.core.world", "ewm.core.runtime.execution.world", "World"),
        (
            "ewm.equilibrium.fixed_point",
            "ewm.equilibrium.solvers.fixed_point",
            "FixedPointConfig",
        ),
        ("ewm.experiments.runner", "ewm.experiments.runs.runner", "ExperimentRun"),
        ("ewm.ontology.model", "ewm.ontology.graph.model", "OntologyProjection"),
    ),
)
def test_legacy_modules_alias_the_single_canonical_implementation(
    legacy_module: str,
    canonical_module: str,
    symbol: str,
) -> None:
    legacy = import_module(legacy_module)
    canonical = import_module(canonical_module)

    assert legacy is canonical
    assert getattr(legacy, symbol) is getattr(canonical, symbol)


@pytest.mark.parametrize(
    ("package_name", "expected"),
    (
        ("ewm.capabilities", {"__init__.py"}),
        ("ewm.core", {"__init__.py"}),
        ("ewm.core.runtime", {"__init__.py"}),
        ("ewm.equilibrium", {"__init__.py"}),
        ("ewm.experiments", {"__init__.py", "registry.py"}),
        ("ewm.ontology", {"__init__.py"}),
    ),
)
def test_large_packages_keep_only_true_entry_points_loose(
    package_name: str,
    expected: set[str],
) -> None:
    package = import_module(package_name)
    package_path = Path(package.__file__).parent

    assert {path.name for path in package_path.glob("*.py")} == expected
