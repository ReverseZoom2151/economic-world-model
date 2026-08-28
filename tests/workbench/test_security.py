"""Loopback, bootstrap, origin, host, and token security contracts."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ewm.workbench.contracts import API_MINOR
from ewm.workbench.server import WorkbenchServerConfig, bind_workbench_server


def test_host_origin_and_header_token_are_independent_mandatory_controls(
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    invalid_host = client.get(
        "/api/v1/system",
        headers={**api_headers, "Host": "attacker.example"},
    )
    missing_origin = client.get(
        "/api/v1/system",
        headers={key: value for key, value in api_headers.items() if key != "Origin"},
    )
    invalid_origin = client.get(
        "/api/v1/system",
        headers={**api_headers, "Origin": "https://attacker.example"},
    )
    missing_token = client.get(
        "/api/v1/system",
        headers={key: value for key, value in api_headers.items() if key != "X-EWM-Token"},
    )
    invalid_token = client.get(
        "/api/v1/system",
        headers={**api_headers, "X-EWM-Token": "wrong"},
    )

    assert invalid_host.status_code == 400
    assert missing_origin.status_code == invalid_origin.status_code == 403
    assert missing_token.status_code == invalid_token.status_code == 401
    for response in (
        invalid_host,
        missing_origin,
        invalid_origin,
        missing_token,
        invalid_token,
    ):
        assert response.headers["X-EWM-API-Minor"] == str(API_MINOR)
        assert "test-session-token" not in response.text


def test_cors_is_disabled_and_oversized_bodies_fail_before_parsing(
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    preflight = client.options(
        "/api/v1/comparisons",
        headers={
            **api_headers,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-EWM-Token",
        },
    )
    oversized = client.post(
        "/api/v1/comparisons",
        content=b"x" * 4_097,
        headers={
            **api_headers,
            "Content-Type": "application/json",
            "Idempotency-Key": "oversized",
        },
    )

    assert preflight.status_code == 405
    assert "Access-Control-Allow-Origin" not in preflight.headers
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "request_too_large"


def test_bootstrap_is_top_level_no_store_and_keeps_token_out_of_persistence(
    client: TestClient,
    security_policy,
) -> None:
    response = client.get(
        "/",
        headers={
            "Host": "127.0.0.1:8123",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        },
    )

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert "Set-Cookie" not in response.headers
    assert "Content-Security-Policy" in response.headers
    assert "unsafe-inline" not in response.headers["Content-Security-Policy"]
    assert security_policy.session_token not in str(response.request.url)
    encoded = re.search(
        r'<meta name="ewm-bootstrap" content="(?P<data>[A-Za-z0-9_-]+)"',
        response.text,
    )
    assert encoded is not None
    padding = "=" * (-len(encoded.group("data")) % 4)
    bootstrap = json.loads(
        base64.urlsafe_b64decode(encoded.group("data") + padding).decode("utf-8")
    )
    assert bootstrap == {
        "api_base": "/api/v1",
        "api_minor": API_MINOR,
        "session_token": security_policy.session_token,
    }

    client_source = Path(__file__).parents[2] / "workbench" / "src"
    source_text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(client_source.rglob("*.ts*"))
    )
    assert "localStorage" not in source_text
    assert "sessionStorage" not in source_text


def test_bootstrap_rejects_non_navigation_fetches(client: TestClient) -> None:
    response = client.get("/", headers={"Host": "127.0.0.1:8123"})

    assert response.status_code == 403


def test_token_query_parameters_are_rejected_even_with_valid_header(
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    response = client.get(
        "/api/v1/system",
        params={"token": "query-secret"},
        headers=api_headers,
    )

    assert response.status_code == 400
    assert "query-secret" not in response.text


def test_server_configuration_and_socket_are_loopback_only(
    approved_registry,
) -> None:
    with pytest.raises(ValueError, match="loopback"):
        WorkbenchServerConfig(host="0.0.0.0")

    bound = bind_workbench_server(
        approved_registry,
        WorkbenchServerConfig(host="127.0.0.1", port=0),
    )
    try:
        assert bound.host == "127.0.0.1"
        assert bound.port > 0
        assert bound.origin == f"http://127.0.0.1:{bound.port}"
        assert bound.server.config.access_log is False
        assert bound.session_token not in repr(bound.server.config)
    finally:
        bound.close()
