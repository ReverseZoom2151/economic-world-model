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
    "cong-lab-iii",
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


def test_traceability_guide_is_linked_from_readme() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = ROOT / "docs" / "paper-traceability.md"

    assert guide.exists()
    assert "docs/paper-traceability.md" in readme
