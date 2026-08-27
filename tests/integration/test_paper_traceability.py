from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[2]

EXPECTED_SOURCES = {"cong-2026", "han-et-al-2026"}
EXPECTED_ITEMS = {
    # Cong: definitions, formal results, algorithm, and laboratories.
    "cong-def-2.1",
    "cong-eq-2.1-2.2",
    "cong-def-2.4",
    "cong-def-2.6",
    "cong-def-3.1",
    "cong-assumption-3.2",
    "cong-prop-3.3",
    "cong-theorem-3.4",
    "cong-eq-3.1",
    "cong-theorem-3.5",
    "cong-prop-4.1",
    "cong-theorem-a.2",
    "cong-prop-a.3",
    "cong-prop-a.4",
    "cong-eq-a.1",
    "cong-prop-a.5",
    "cong-prop-a.6",
    "cong-prop-a.8",
    "cong-corollary-a.9",
    "cong-appendix-b-algorithm",
    "cong-lab-i",
    "cong-lab-ii",
    "cong-lab-iii-population",
    "cong-lab-iii-finite-sample",
    "cong-prop-d.1",
    "cong-theorem-e.1",
    # Han: state equations, components, public protocol, levels, and evaluation.
    "han-eq-1",
    "han-eq-2",
    "han-eq-3",
    "han-eq-4",
    "han-eq-5",
    "han-eq-6",
    "han-eq-7",
    "han-component-agents",
    "han-component-environment",
    "han-component-coevolution",
    "han-component-alignment",
    "han-spec-agent",
    "han-spec-environment",
    "han-spec-coevolution",
    "han-spec-alignment",
    "han-spec-evaluation",
    "han-runtime-reset",
    "han-runtime-run-agents",
    "han-runtime-step",
    "han-runtime-coevolve",
    "han-runtime-align",
    "han-runtime-evaluate",
    "han-runtime-log",
    "han-level-l1",
    "han-level-l2",
    "han-level-l3",
    "han-level-l4",
    "han-level-l5",
    "han-level-l6",
    "han-eval-agents",
    "han-eval-environment",
    "han-eval-coevolution",
    "han-eval-alignment",
    "han-eval-efficiency",
}

VALID_STATUSES = {
    "implemented",
    "partial",
    "planned",
    "blocked-external",
    "not-applicable",
}
VALID_CLAIMS = {
    "source-definition",
    "theorem-diagnostic",
    "exact-replication",
    "conformance",
    "paper-inspired",
    "qualitative-reconstruction",
    "survey-only",
}


def _load(name: str) -> dict[str, object]:
    with (ROOT / "references" / name).open("rb") as handle:
        return tomllib.load(handle)


def test_locked_sources_have_stable_identity() -> None:
    registry = _load("papers.toml")
    sources = registry["source"]
    assert isinstance(sources, list)
    assert {source["id"] for source in sources} == EXPECTED_SOURCES

    for source in sources:
        assert re.fullmatch(r"[0-9a-f]{64}", source["sha256"])
        assert source["pages"] > 0
        assert source["preflight"] == "pass"
        assert source["public_url"].startswith("https://")
        assert source["local_pdf_tracked"] is False


def test_conformance_registry_covers_declared_paper_surface() -> None:
    registry = _load("conformance.toml")
    items = registry["item"]
    assert isinstance(items, list)
    identifiers = [item["id"] for item in items]

    assert len(identifiers) == len(set(identifiers))
    assert set(identifiers) == EXPECTED_ITEMS


def test_conformance_entries_have_valid_claims_and_evidence_paths() -> None:
    registry = _load("conformance.toml")
    items = registry["item"]

    for item in items:
        assert item["source"] in EXPECTED_SOURCES
        assert item["status"] in VALID_STATUSES
        assert item["claim"] in VALID_CLAIMS
        assert item["pages"]
        assert item["section"]
        assert item["summary"]

        if item["status"] in {"implemented", "partial"}:
            assert item["implementation"], item["id"]
            assert item["evidence"], item["id"]
            for relative_path in (*item["implementation"], *item["evidence"]):
                assert (ROOT / relative_path).exists(), (item["id"], relative_path)

        if item["status"] in {"partial", "planned", "blocked-external"}:
            assert item["limitation"], item["id"]


def test_forecasting_population_targets_are_separate_from_authored_damping() -> None:
    registry = _load("conformance.toml")
    items = {item["id"]: item for item in registry["item"]}

    population = items["cong-lab-iii-population"]
    finite_sample = items["cong-lab-iii-finite-sample"]

    assert population["status"] == "implemented"
    assert population["claim"] == "exact-replication"
    assert "{-0.795, 0, +0.795}" in population["summary"]
    assert "tests/oracles/forecasting_oracle.py" in population["evidence"]
    assert "tests/integration/test_independent_numerical_oracles.py" in population[
        "evidence"
    ]
    assert "limitation" not in population
    assert finite_sample["claim"] == "paper-inspired"
    assert "package-authored damping" in finite_sample["summary"]


def test_executable_economic_primitives_are_registered_at_their_source_scope() -> None:
    registry = _load("conformance.toml")
    items = {item["id"]: item for item in registry["item"]}
    expected = {
        "cong-def-2.1": (
            "src/ewm/core/coherence.py",
            "tests/unit/test_coherence.py",
        ),
        "cong-eq-2.1-2.2": (
            "src/ewm/core/kernels.py",
            "tests/unit/test_kernels.py",
        ),
        "cong-def-2.4": (
            "src/ewm/core/interventions.py",
            "tests/unit/test_interventions.py",
        ),
    }

    for item_id, (implementation, evidence) in expected.items():
        item = items[item_id]
        assert item["status"] == "implemented"
        assert implementation in item["implementation"]
        assert evidence in item["evidence"]


def test_restricted_theorem_certificates_do_not_overclaim_general_kakutani() -> None:
    registry = _load("conformance.toml")
    items = {item["id"]: item for item in registry["item"]}
    assumption = items["cong-assumption-3.2"]
    proposition = items["cong-prop-3.3"]

    assert assumption["status"] == "blocked-external"
    assert proposition["status"] == "partial"
    assert "src/ewm/equilibrium/certificates.py" in proposition["implementation"]
    assert "tests/unit/test_theorem_certificates.py" in proposition["evidence"]
    assert "affine" in proposition["limitation"]
    assert "Kakutani" in proposition["limitation"]


def test_independent_production_oracle_preserves_the_paper_authored_boundary() -> None:
    registry = _load("conformance.toml")
    items = {item["id"]: item for item in registry["item"]}
    production = items["cong-prop-d.1"]

    assert production["status"] == "partial"
    assert "tests/oracles/production_oracle.py" in production["evidence"]
    assert "tests/integration/test_independent_numerical_oracles.py" in production[
        "evidence"
    ]
    assert "package-authored" in production["limitation"]
    assert "proof" in production["limitation"]


def test_locked_credit_failure_and_synthetic_han_validation_are_explicit() -> None:
    registry = _load("conformance.toml")
    items = {item["id"]: item for item in registry["item"]}
    credit = items["cong-lab-i"]
    l2 = items["han-level-l2"]

    assert credit["status"] == "blocked-external"
    assert "src/ewm/protocols/credit-mechanism-v1.toml" in credit["implementation"]
    assert "tests/integration/test_locked_protocol_smoke.py" in credit["evidence"]
    assert "fails" in credit["limitation"]
    assert "authorizes no claim" in credit["limitation"]

    assert l2["status"] == "implemented"
    assert "src/ewm/scenarios/fx/validation.py" in l2["implementation"]
    assert "tests/conformance/test_han_l1_l2_validation.py" in l2["evidence"]
    assert "synthetic" in l2["limitation"]
    assert "empirical" in l2["limitation"]


def test_compiled_fx_runtime_is_bound_to_han_runtime_claims() -> None:
    registry = _load("conformance.toml")
    items = {item["id"]: item for item in registry["item"]}

    for item_id in (
        "han-component-environment",
        "han-runtime-reset",
        "han-runtime-run-agents",
        "han-runtime-step",
        "han-runtime-log",
    ):
        item = items[item_id]
        assert "src/ewm/scenarios/fx/runtime.py" in item["implementation"]
        assert "tests/scenarios/test_fx_world.py" in item["evidence"]


def test_traceability_guide_separates_replay_engineering_from_paper_claims() -> None:
    guide = (ROOT / "docs" / "paper-traceability.md").read_text(encoding="utf-8")

    assert "Artifact v2 verification and deterministic replay" in guide
    assert "package engineering" in guide
    assert "not paper correspondence" in guide


def test_traceability_guide_is_linked_from_readme() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = ROOT / "docs" / "paper-traceability.md"

    assert guide.exists()
    assert "docs/paper-traceability.md" in readme


def test_paper_level_conformance_suite_is_registered_and_local() -> None:
    registry = _load("conformance.toml")
    suite = registry["conformance_suite"]

    assert suite["schema"] == "ewm.conformance.v1"
    assert suite["command"] == "python scripts/run_conformance.py"
    for field in (
        "cong_evidence",
        "han_evidence",
        "claim_boundary_evidence",
        "reporter",
    ):
        assert (ROOT / suite[field]).is_file()
