"""Versioned workbench API contract tests."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from ewm.workbench.contracts import (
    API_MAJOR,
    API_MINOR,
    API_PATHS,
    ComparisonRequest,
    SnapshotExportRequest,
    openapi_document,
)


def test_contract_models_reject_unknown_fields_and_mutation() -> None:
    request = ComparisonRequest(left_run_id="left", right_run_id="right")

    with pytest.raises(ValidationError, match="extra_forbidden"):
        ComparisonRequest(
            left_run_id="left",
            right_run_id="right",
            run_dir="/not/approved",  # type: ignore[call-arg]
        )
    with pytest.raises(ValidationError, match="frozen"):
        request.left_run_id = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        SnapshotExportRequest(run_id="left", object_ids=tuple(str(i) for i in range(10_001)))


def test_openapi_document_is_versioned_complete_and_deterministic() -> None:
    first = openapi_document()
    second = openapi_document()

    assert first == second
    assert first["openapi"].startswith("3.1.")
    assert first["info"]["version"] == f"{API_MAJOR}.{API_MINOR}.0"
    assert set(first["paths"]) == set(API_PATHS)
    assert "/docs" not in first["paths"]
    assert "X-EWM-Token" in json.dumps(first, sort_keys=True)
