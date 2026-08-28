"""Versioned transport contracts for the local ontology workbench."""

from __future__ import annotations

import json
from collections.abc import Callable
from importlib import import_module
from typing import Any, ClassVar, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

API_MAJOR = 1
API_MINOR = 0
API_SCHEMA = "ewm.workbench.api.v1"
API_PREFIX = f"/api/v{API_MAJOR}"
TOKEN_HEADER = "X-EWM-Token"
API_MINOR_HEADER = "X-EWM-API-Minor"

API_PATHS = (
    f"{API_PREFIX}/system",
    f"{API_PREFIX}/runs",
    f"{API_PREFIX}/runs/{{run_id}}",
    f"{API_PREFIX}/objects",
    f"{API_PREFIX}/objects/{{object_id}}",
    f"{API_PREFIX}/relations",
    f"{API_PREFIX}/paths",
    f"{API_PREFIX}/events",
    f"{API_PREFIX}/states",
    f"{API_PREFIX}/measurements",
    f"{API_PREFIX}/claims",
    f"{API_PREFIX}/evidence",
    f"{API_PREFIX}/ddge-candidates",
    f"{API_PREFIX}/comparisons",
    f"{API_PREFIX}/snapshot-exports",
)


class ContractModel(BaseModel):
    """Strict immutable base for externally visible contracts."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)


class ComparisonRequest(ContractModel):
    """Request an explicit scientific comparison between two approved runs."""

    left_run_id: str = Field(min_length=1, max_length=200)
    right_run_id: str = Field(min_length=1, max_length=200)


class SnapshotExportRequest(ContractModel):
    """Plan an immutable, explicitly selected investigation snapshot."""

    run_id: str = Field(min_length=1, max_length=200)
    object_ids: tuple[str, ...] = Field(default=(), max_length=10_000)
    relation_ids: tuple[str, ...] = Field(default=(), max_length=30_000)
    event_ids: tuple[str, ...] = Field(default=(), max_length=100_000)
    lens: str | None = Field(default=None, min_length=1, max_length=100)


class ErrorDetail(ContractModel):
    """Stable machine-readable API failure."""

    code: str
    message: str
    context: dict[str, Any] = Field(default_factory=dict)


class SuccessEnvelope(ContractModel):
    """Versioned successful response envelope."""

    ok: Literal[True] = True
    schema_: str = Field(default=API_SCHEMA, alias="schema", serialization_alias="schema")
    projection_digests: tuple[str, ...] = ()
    data: Any


class ErrorEnvelope(ContractModel):
    """Versioned error response envelope."""

    ok: Literal[False] = False
    schema_: str = Field(default=API_SCHEMA, alias="schema", serialization_alias="schema")
    projection_digests: tuple[str, ...] = ()
    error: ErrorDetail


def openapi_document() -> dict[str, Any]:
    """Return the deterministic OpenAPI 3.1 contract used for client generation."""

    builder = cast(
        Callable[[], dict[str, Any]],
        import_module("ewm.workbench.openapi").build_openapi_document,
    )
    return builder()


def _main() -> int:
    print(json.dumps(openapi_document(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
