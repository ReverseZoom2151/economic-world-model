from __future__ import annotations

import importlib
import math
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[2]
TARGET_REGISTRY = ROOT / "references" / "replication-targets.toml"

VALID_CLASSIFICATIONS = {"source-stated", "derived", "package-authored"}
VALID_TOLERANCE_KINDS = {"exact", "absolute", "relative", "not-applicable"}

# These names form the stable semantic interface between the registry and the
# implementations. They keep paper constants in one auditable place instead of
# allowing tests and presets to repeat anonymous numbers independently.
EXPECTED_FACTS: dict[str, tuple[Any, str]] = {
    "scalar.figure-3.kappa": (0.5, "source-stated"),
    "scalar.figure-3.gamma": (1.0, "source-stated"),
    "scalar.figure-3.learning-gain": (0.8, "source-stated"),
    "scalar.figure-3.composite-gain": (1.6, "derived"),
    "forecasting.figure-4.feedback": (1.8, "source-stated"),
    "forecasting.figure-4.noise-std": (0.5, "source-stated"),
    "forecasting.figure-4.finite-sample-size": (4_000, "source-stated"),
    "forecasting.figure-4.outer-slopes": ([-0.795, 0.0, 0.795], "source-stated"),
    "forecasting.figure-4.finite-sample-damping": (0.5, "package-authored"),
}


def _load_registry(path: Path) -> dict[str, Any]:
    assert path.is_file(), f"replication target registry is required at {path.relative_to(ROOT)}"
    with path.open("rb") as handle:
        return tomllib.load(handle)


@pytest.fixture(scope="module")
def conformance() -> dict[str, Any]:
    return _load_registry(ROOT / "references" / "conformance.toml")


@pytest.fixture(scope="module")
def sources() -> dict[str, Any]:
    return _load_registry(ROOT / "references" / "papers.toml")


@pytest.fixture(scope="module")
def registry() -> dict[str, Any]:
    return _load_registry(TARGET_REGISTRY)


@pytest.fixture(scope="module")
def targets(registry: dict[str, Any]) -> list[dict[str, Any]]:
    declared = registry.get("target")
    assert isinstance(declared, list) and declared, "registry must declare [[target]] entries"
    assert all(isinstance(target, dict) for target in declared)
    return declared


def _target_by_fact(targets: list[dict[str, Any]], fact: str) -> dict[str, Any]:
    matches = [target for target in targets if target.get("fact") == fact]
    assert len(matches) == 1, f"expected exactly one target for {fact!r}, found {len(matches)}"
    return matches[0]


def _resolve_symbol(reference: str) -> object:
    module_name, separator, qualified_name = reference.partition(":")
    assert separator and module_name and qualified_name, (
        f"implementation symbol must use 'module:qualified.name' syntax: {reference!r}"
    )
    assert module_name == "ewm" or module_name.startswith("ewm."), reference
    value: object = importlib.import_module(module_name)
    for component in qualified_name.split("."):
        value = getattr(value, component)
    return value


def _assert_same_value(actual: Any, expected: Any, fact: str) -> None:
    if isinstance(expected, float):
        assert isinstance(actual, int | float) and not isinstance(actual, bool), fact
        assert math.isclose(float(actual), expected, rel_tol=0.0, abs_tol=1e-12), fact
        return
    if isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected), fact
        for actual_item, expected_item in zip(actual, expected, strict=True):
            _assert_same_value(actual_item, expected_item, fact)
        return
    assert actual == expected, fact


def test_registry_declares_supported_schema(registry: dict[str, Any]) -> None:
    assert registry["schema_version"] == 1


def test_target_identifiers_and_facts_are_unique(
    targets: list[dict[str, Any]],
) -> None:
    identifiers = [target.get("id") for target in targets]
    facts = [target.get("fact") for target in targets]

    assert all(isinstance(identifier, str) and identifier for identifier in identifiers)
    assert len(identifiers) == len(set(identifiers))
    assert all(isinstance(fact, str) and fact for fact in facts)
    assert len(facts) == len(set(facts))


def test_targets_cover_only_every_exact_replication_claim(
    targets: list[dict[str, Any]], conformance: dict[str, Any]
) -> None:
    items = {item["id"]: item for item in conformance["item"]}
    exact_claims = {
        identifier for identifier, item in items.items() if item["claim"] == "exact-replication"
    }
    linked_claims = {
        conformance_id for target in targets for conformance_id in target.get("conformance_ids", [])
    }

    assert exact_claims == {
        "cong-eq-a.1",
        "cong-prop-a.5",
        "cong-lab-ii",
        "cong-lab-iii",
    }
    assert linked_claims == exact_claims

    credit_lab = items["cong-lab-i"]
    assert credit_lab["status"] == "blocked-external"
    assert credit_lab["claim"] == "qualitative-reconstruction"
    assert "cong-lab-i" not in linked_claims


def test_targets_have_valid_source_and_conformance_cross_links(
    targets: list[dict[str, Any]],
    conformance: dict[str, Any],
    sources: dict[str, Any],
) -> None:
    known_sources = {source["id"] for source in sources["source"]}
    items = {item["id"]: item for item in conformance["item"]}

    for target in targets:
        source_id = target.get("source_id")
        conformance_ids = target.get("conformance_ids")
        assert source_id in known_sources, target.get("id")
        assert isinstance(conformance_ids, list) and conformance_ids, target.get("id")
        assert len(conformance_ids) == len(set(conformance_ids)), target.get("id")
        for conformance_id in conformance_ids:
            assert conformance_id in items, (target.get("id"), conformance_id)
            assert items[conformance_id]["source"] == source_id, (
                target.get("id"),
                conformance_id,
            )


def test_targets_have_typed_values_locators_and_tolerances(
    targets: list[dict[str, Any]],
) -> None:
    for target in targets:
        identifier = target.get("id")
        assert target.get("classification") in VALID_CLASSIFICATIONS, identifier

        locator = target.get("locator")
        assert isinstance(locator, Mapping) and locator, identifier
        assert set(locator) & {"pages", "section", "equation", "figure"}, identifier
        assert all(isinstance(value, str) and value.strip() for value in locator.values()), (
            identifier,
            locator,
        )

        has_value = "value" in target
        has_expectation = "expectation" in target
        assert has_value ^ has_expectation, (
            f"{identifier} must declare exactly one of value or expectation"
        )
        if has_expectation:
            assert isinstance(target["expectation"], str) and target["expectation"].strip()

        tolerance = target.get("tolerance")
        assert isinstance(tolerance, Mapping), identifier
        kind = tolerance.get("kind")
        assert kind in VALID_TOLERANCE_KINDS, identifier
        if kind in {"absolute", "relative"}:
            amount = tolerance.get("value")
            assert isinstance(amount, int | float) and not isinstance(amount, bool), identifier
            assert math.isfinite(float(amount)) and float(amount) >= 0.0, identifier
        elif kind == "not-applicable":
            assert has_expectation, identifier

        implementation_symbols = target.get("implementation_symbols")
        evidence = target.get("evidence")
        assert isinstance(implementation_symbols, list) and implementation_symbols, identifier
        assert isinstance(evidence, list) and evidence, identifier


def test_implementation_symbols_import_and_evidence_paths_resolve(
    targets: list[dict[str, Any]],
) -> None:
    root = ROOT.resolve()
    for target in targets:
        identifier = target["id"]
        for symbol in target["implementation_symbols"]:
            assert isinstance(symbol, str), identifier
            assert _resolve_symbol(symbol) is not None, (identifier, symbol)

        for relative_name in target["evidence"]:
            assert isinstance(relative_name, str), identifier
            evidence_path = (ROOT / relative_name).resolve()
            assert evidence_path.is_relative_to(root), (identifier, relative_name)
            assert evidence_path.is_file(), (identifier, relative_name)
            assert evidence_path.suffix == ".py", (identifier, relative_name)
            assert evidence_path.is_relative_to((ROOT / "tests").resolve()), (
                identifier,
                relative_name,
            )


def test_registry_locks_current_scalar_and_forecasting_source_facts(
    targets: list[dict[str, Any]],
) -> None:
    for fact, (expected_value, expected_classification) in EXPECTED_FACTS.items():
        target = _target_by_fact(targets, fact)
        assert target["classification"] == expected_classification, fact
        _assert_same_value(target.get("value"), expected_value, fact)

    from ewm.scenarios.forecasting.presets import (
        paper_config as forecasting_paper_config,
    )
    from ewm.scenarios.forecasting.presets import paper_finite_sample_config
    from ewm.scenarios.scalar.model import paper_config as scalar_paper_config

    scalar = scalar_paper_config()
    forecasting = forecasting_paper_config()
    finite_sample = paper_finite_sample_config()

    _assert_same_value(
        _target_by_fact(targets, "scalar.figure-3.kappa")["value"],
        scalar.kappa,
        "scalar.figure-3.kappa",
    )
    _assert_same_value(
        _target_by_fact(targets, "scalar.figure-3.gamma")["value"],
        scalar.gamma,
        "scalar.figure-3.gamma",
    )
    _assert_same_value(
        _target_by_fact(targets, "scalar.figure-3.learning-gain")["value"],
        scalar.learning_gain,
        "scalar.figure-3.learning-gain",
    )
    _assert_same_value(
        _target_by_fact(targets, "scalar.figure-3.composite-gain")["value"],
        scalar.composite_gain,
        "scalar.figure-3.composite-gain",
    )
    _assert_same_value(
        _target_by_fact(targets, "forecasting.figure-4.feedback")["value"],
        forecasting.feedback,
        "forecasting.figure-4.feedback",
    )
    _assert_same_value(
        _target_by_fact(targets, "forecasting.figure-4.noise-std")["value"],
        forecasting.noise_std,
        "forecasting.figure-4.noise-std",
    )
    assert (
        _target_by_fact(targets, "forecasting.figure-4.finite-sample-size")["value"]
        == finite_sample.sample_size
    )


def test_forecasting_damping_is_never_classified_as_source_stated(
    targets: list[dict[str, Any]],
) -> None:
    damping = _target_by_fact(targets, "forecasting.figure-4.finite-sample-damping")

    assert damping["classification"] == "package-authored"
    assert damping["value"] == 0.5
    assert damping["conformance_ids"] == ["cong-lab-iii"]
    assert damping.get("source_note")
    assert "omit" in damping["source_note"].lower()
