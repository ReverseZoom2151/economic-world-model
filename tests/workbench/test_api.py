"""Read-only workbench API endpoint and cost-limit contracts."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ewm.workbench.http.contracts import API_MINOR


def _assert_envelope(response, *, ok: bool = True) -> dict[str, object]:
    assert response.headers["X-EWM-API-Minor"] == str(API_MINOR)
    body = response.json()
    assert body["ok"] is ok
    assert body["schema"] == "ewm.workbench.api.v1"
    assert isinstance(body["projection_digests"], list)
    return body


def test_every_read_endpoint_returns_a_versioned_envelope(
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    requests = (
        ("/api/v1/system", {}),
        ("/api/v1/runs", {}),
        ("/api/v1/runs/left", {}),
        ("/api/v1/objects", {"run_id": "left"}),
        (
            "/api/v1/objects/ewm:workbench:world:left",
            {"run_id": "left"},
        ),
        ("/api/v1/relations", {"run_id": "left"}),
        (
            "/api/v1/paths",
            {
                "run_id": "left",
                "start_id": "ewm:workbench:evidence:left",
                "target_id": "ewm:workbench:claim:left",
                "max_depth": 1,
            },
        ),
        ("/api/v1/events", {"run_id": "left"}),
        ("/api/v1/states", {"run_id": "left"}),
        ("/api/v1/measurements", {"run_id": "left"}),
        ("/api/v1/claims", {"run_id": "left"}),
        ("/api/v1/evidence", {"run_id": "left"}),
        ("/api/v1/ddge-candidates", {"run_id": "left"}),
    )

    for path, params in requests:
        response = client.get(path, params=params, headers=api_headers)
        assert response.status_code == 200, (path, response.text)
        body = _assert_envelope(response)
        assert "data" in body


def test_query_limits_and_unknown_records_use_standard_error_envelopes(
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    over_limit = client.get(
        "/api/v1/objects",
        params={"run_id": "left", "limit": 201},
        headers=api_headers,
    )
    missing = client.get(
        "/api/v1/runs/missing",
        headers=api_headers,
    )

    assert over_limit.status_code == 422
    assert _assert_envelope(over_limit, ok=False)["error"]["code"] == "query_cost"
    assert missing.status_code == 404
    assert _assert_envelope(missing, ok=False)["error"]["code"] == "not_found"


def test_comparison_and_snapshot_commands_are_canonically_idempotent(
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    comparison_headers = {**api_headers, "Idempotency-Key": "compare-left-right"}
    comparison_request = {"left_run_id": "left", "right_run_id": "right"}
    first = client.post(
        "/api/v1/comparisons",
        json=comparison_request,
        headers=comparison_headers,
    )
    second = client.post(
        "/api/v1/comparisons",
        json=comparison_request,
        headers=comparison_headers,
    )
    export_headers = {**api_headers, "Idempotency-Key": "export-left"}
    export_request = {
        "run_id": "left",
        "object_ids": ["ewm:workbench:world:left"],
        "lens": "world",
    }
    export_first = client.post(
        "/api/v1/snapshot-exports",
        json=export_request,
        headers=export_headers,
    )
    export_second = client.post(
        "/api/v1/snapshot-exports",
        json=export_request,
        headers=export_headers,
    )

    assert first.status_code == second.status_code == 200
    assert _assert_envelope(first)["data"] == _assert_envelope(second)["data"]
    assert first.headers["Idempotency-Key"] == "compare-left-right"
    assert export_first.status_code == export_second.status_code == 200
    assert _assert_envelope(export_first)["data"] == _assert_envelope(export_second)["data"]
    assert export_first.json()["data"]["status"] == "planned"


def test_api_requests_cannot_introduce_filesystem_paths(
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    response = client.get(
        "/api/v1/runs",
        params={"run_dir": "/tmp/not-approved"},
        headers=api_headers,
    )

    assert response.status_code == 400
    assert _assert_envelope(response, ok=False)["error"]["code"] == "filesystem_selector"
