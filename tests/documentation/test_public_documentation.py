from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
README = ROOT / "README.md"
PRODUCT_VALIDATION = ROOT / "docs" / "product-validation.md"
PUBLIC_MARKDOWN = (README, *sorted((ROOT / "docs").glob("*.md")))
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_public_documentation_matches_the_current_release_contract() -> None:
    readme = _text(README)
    assert '<h1 align="center">Economic World Model</h1>' in readme
    assert (
        "Build executable economies where deployed models reshape decisions, markets, "
        "generated data, and the models trained next."
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


def test_public_markdown_links_paths_and_code_fences_are_well_formed() -> None:
    failures: list[str] = []
    for path in PUBLIC_MARKDOWN:
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
