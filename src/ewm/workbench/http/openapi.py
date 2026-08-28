"""Deterministic OpenAPI assembly for the secured HTTP transport."""

from __future__ import annotations

import json
from typing import Any, cast

from .api import ApprovedRunRegistry, create_workbench_app
from .security import SecurityPolicy


def build_openapi_document() -> dict[str, Any]:
    """Build the complete local workbench OpenAPI 3.1 document."""

    policy = SecurityPolicy(
        session_token="contract-generation-token-with-adequate-entropy",
        allowed_hosts=("127.0.0.1",),
        allowed_origins=("http://127.0.0.1:8123",),
    )
    document = create_workbench_app(ApprovedRunRegistry(()), policy).openapi()
    return cast(
        dict[str, Any],
        json.loads(json.dumps(document, sort_keys=True, separators=(",", ":"))),
    )
