from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[2]
PYPROJECT = ROOT / "pyproject.toml"
VERSION_FILE = ROOT / "src" / "ewm" / "_version.py"


def _project_configuration() -> dict[str, object]:
    with PYPROJECT.open("rb") as stream:
        return tomllib.load(stream)


def test_release_version_has_one_static_source() -> None:
    configuration = _project_configuration()
    project = configuration["project"]
    hatch_version = configuration["tool"]["hatch"]["version"]

    assert "version" not in project
    assert project["dynamic"] == ["version"]
    assert hatch_version["path"] == "src/ewm/_version.py"
    assert re.search(
        r'^__version__ = "0\.2\.0"$',
        VERSION_FILE.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )


def test_release_metadata_exposes_maintainer_and_project_links() -> None:
    project = _project_configuration()["project"]

    assert project["maintainers"] == [{"name": "ReverseZoom2151"}]
    assert project["urls"]["Changelog"].endswith("/blob/main/CHANGELOG.md")
    assert project["urls"]["Security"].endswith("/security/policy")
    assert project["urls"]["Documentation"].endswith("#readme")


def test_repository_has_complete_community_health_surface() -> None:
    required_paths = (
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "GOVERNANCE.md",
        "MAINTAINERS.md",
        "SUPPORT.md",
        "CHANGELOG.md",
        "CITATION.cff",
        ".github/CODEOWNERS",
        ".github/dependabot.yml",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/config.yml",
        ".github/pull_request_template.md",
    )

    missing = [path for path in required_paths if not (ROOT / path).is_file()]
    assert not missing, f"missing community files: {missing}"

    security_policy = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert (
        "https://github.com/ReverseZoom2151/economic-world-model/security/advisories/new"
        in security_policy
    )
    assert "@ReverseZoom2151" in (ROOT / ".github/CODEOWNERS").read_text(
        encoding="utf-8"
    )


def test_all_workflows_pin_actions_and_bound_execution() -> None:
    workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    assert {path.name for path in workflows} >= {
        "ci.yml",
        "mutation.yml",
        "property-fuzz.yml",
        "release.yml",
        "security.yml",
    }

    unpinned: list[str] = []
    unbounded: list[str] = []
    for workflow in workflows:
        content = workflow.read_text(encoding="utf-8")
        if "permissions:" not in content or "concurrency:" not in content:
            unbounded.append(workflow.name)
        if "timeout-minutes:" not in content:
            unbounded.append(workflow.name)
        for line in content.splitlines():
            match = re.search(r"\buses:\s+[^@\s]+@([^\s#]+)", line)
            if match is not None and re.fullmatch(r"[0-9a-f]{40}", match.group(1)) is None:
                unpinned.append(f"{workflow.name}: {line.strip()}")

    assert not unbounded, f"workflows lack explicit bounds: {sorted(set(unbounded))}"
    assert not unpinned, f"actions are not commit-pinned: {unpinned}"


def test_release_automation_cannot_publish_to_pypi() -> None:
    release_workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert "gh release create" in release_workflow
    assert "--verify-tag" in release_workflow
    assert "pypa/gh-action-pypi-publish" not in release_workflow
    assert "twine upload" not in release_workflow
    assert "id-token: write" not in release_workflow
