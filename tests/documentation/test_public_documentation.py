from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
README = ROOT / "README.md"
PRODUCT_VALIDATION = ROOT / "docs" / "product-validation.md"
ONTOLOGY_GUIDE = ROOT / "docs" / "ontology.md"
WORKBENCH_GUIDE = ROOT / "docs" / "workbench.md"
SNAPSHOT_GUIDE = ROOT / "docs" / "snapshots.md"
EXTENSION_GUIDE = ROOT / "docs" / "ontology-extension-guide.md"
WORKBENCH_AUDIT = ROOT / "docs" / "workbench-release-audit.md"
PUBLIC_MARKDOWN = (README, *sorted((ROOT / "docs").glob("*.md")))
ALL_MARKDOWN = (README, *sorted((ROOT / "docs").rglob("*.md")))
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_public_documentation_matches_the_current_release_contract() -> None:
    readme = _text(README)
    assert '<h1 align="center">Economic World Model</h1>' in readme
    assert (
        "Build and solve economies where agents, markets, data, and learned models "
        "co-evolve."
    ) in readme
    assert "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6559940" in readme
    assert "https://arxiv.org/abs/2608.06020v1" in readme
    assert r"E_i(\theta)" in readme
    assert r"E_i(\theta)=\lbrace" in readme
    assert r"\rbrace." in readme
    assert r"\left\{" not in readme
    assert r"\begin{array}" not in readme
    assert r"F_i(\theta)" in readme
    assert r"\theta^{\star}=F_i(\theta^{\star})" in readme
    population_notation = (
        r"\lbrace(\mathcal{I}_{t}^{n},\Pi^{n},\mu_{t}^{n})\rbrace_{n=1}^{N}."
    )
    assert f"```math\n{population_notation}\n```" in readme
    assert "ewm.run.v2" in readme
    assert "ewm verify-run" in readme
    assert "ewm replay-run" in readme
    for guide in (
        "docs/ontology.md",
        "docs/workbench.md",
        "docs/snapshots.md",
        "docs/ontology-extension-guide.md",
        "docs/workbench-release-audit.md",
    ):
        assert guide in readme

    current_docs = tuple(path for path in PUBLIC_MARKDOWN if path != PRODUCT_VALIDATION)
    for path in current_docs:
        content = _text(path)
        assert "0.1.0" not in content, path
        assert "Version 0.1" not in content, path
        assert "version 0.1" not in content, path
    historical_audit = _text(PRODUCT_VALIDATION)
    assert "Current 0.2.0 audit" in historical_audit
    assert "Historical 0.1.0 audit" in historical_audit

    public_text = "\n".join(_text(path) for path in PUBLIC_MARKDOWN)
    assert "\N{EM DASH}" not in public_text


def test_ontology_workbench_guides_state_the_scientific_and_operational_contracts() -> None:
    ontology = _text(ONTOLOGY_GUIDE)
    for layer in (
        "Schema",
        "Economic declaration",
        "Runtime occurrence",
        "Learning and equilibrium",
        "Research and evidence",
        "Provenance",
    ):
        assert layer in ontology
    assert "fourteen invariants" in ontology
    assert "verified `ewm.run.v2`" in ontology
    for status in ("observed", "candidate", "numerically validated", "certified"):
        assert status in ontology

    workbench = _text(WORKBENCH_GUIDE)
    for workflow in (
        "Verify and open",
        "Understand the world",
        "Trace an episode",
        "Follow behavior to learning",
        "Assess DDGE",
        "Compare runs",
        "Audit a claim",
        "Export an investigation",
    ):
        assert workflow in workbench
    for rule in ("X axis", "Y axis", "Z axis", "GeoAnchor"):
        assert rule in workbench
    assert 'python -m pip install -e ".[workbench]"' in workbench
    assert "no remote requests" in workbench

    snapshots = _text(SNAPSHOT_GUIDE)
    for bound in ("10,000 objects", "30,000 relations", "100,000 events", "50 MiB"):
        assert bound in snapshots
    assert "Corruption detection" in snapshots
    assert "Authenticity" in snapshots
    assert "not a digital signature" in snapshots

    extension = _text(EXTENSION_GUIDE)
    for requirement in (
        "profile identity",
        "source digest",
        "coverage ledger",
        "unknown versions fail closed",
    ):
        assert requirement in extension

    audit = _text(WORKBENCH_AUDIT)
    assert "Requirement-by-requirement evidence" in audit
    assert "tests/ontology/graph/test_schema.py" in audit
    assert "workbench/e2e/investigation-workflows.spec.ts" in audit
    assert "scripts/check_frontend_build.py" in audit
    assert "Incomplete" not in audit

    limitations = _text(ROOT / "docs" / "limitations.md")
    assert "Ontology and workbench limits" in limitations
    assert "Reference performance environment" in limitations

    traceability = _text(ROOT / "docs" / "paper-traceability.md")
    assert "Ontology and workbench claim boundary" in traceability

    replication = _text(ROOT / "docs" / "replication.md")
    assert "Ontology and workbench reproduction" in replication


def test_public_markdown_links_paths_and_code_fences_are_well_formed() -> None:
    failures: list[str] = []
    for path in ALL_MARKDOWN:
        content = _text(path)
        if sum(line.startswith("```") for line in content.splitlines()) % 2:
            failures.append(f"{path.relative_to(ROOT)} has an unclosed code fence")
        for raw_target in MARKDOWN_LINK.findall(content):
            target = raw_target.split("#", maxsplit=1)[0].split("?", maxsplit=1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                failures.append(
                    f"{path.relative_to(ROOT)} links to missing path {raw_target!r}"
                )
    assert not failures, "\n".join(failures)


def test_large_repository_directories_have_ownership_indexes() -> None:
    indexes = {
        ROOT / "docs" / "README.md": ("Guides", "Architecture", "Plans"),
        ROOT / "examples" / "README.md": ("Runnable examples", "extensions/"),
        ROOT / "references" / "README.md": ("Machine-readable", "conformance.toml"),
        ROOT / "scripts" / "README.md": ("Stable entry points", "run_conformance.py"),
        ROOT / "src" / "ewm" / "README.md": ("Package map", "experiments/catalog/"),
        ROOT / "tests" / "README.md": ("Evidence intent", "conformance/"),
    }

    for path, required_text in indexes.items():
        assert path.is_file(), path
        content = _text(path)
        for text in required_text:
            assert text in content, (path, text)
