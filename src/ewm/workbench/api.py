"""Read-only local API over approved ontology projections."""

from __future__ import annotations

import base64
import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Annotated, Any, Literal

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from ewm.core.provenance.serialization import canonical_json, content_digest
from ewm.ontology.comparison import compare_projections
from ewm.ontology.graph.identity import (
    measurement_to_data,
    ontology_object_to_data,
    ontology_record_to_data,
    ontology_ref_to_data,
    relation_assertion_to_data,
)
from ewm.ontology.graph.model import OntologyProjection
from ewm.ontology.query import (
    ClaimQuery,
    CursorError,
    EvidenceQuery,
    MeasurementQuery,
    ObjectQuery,
    OntologyQueryService,
    PathFilter,
    PathQuery,
    QueryCostError,
    RelationQuery,
)

from .contracts import (
    API_MAJOR,
    API_MINOR,
    API_PREFIX,
    API_SCHEMA,
    ComparisonRequest,
    ErrorEnvelope,
    SnapshotExportRequest,
    SuccessEnvelope,
)
from .security import SecurityPolicy, WorkbenchSecurityMiddleware, token_dependency

_STATIC_DIRECTORY = Path(__file__).with_name("static")
_EVENT_KINDS = (
    "action_event",
    "event",
    "market_event",
    "observation_event",
    "settlement_event",
)
_STATE_KINDS = ("state_observation",)
_DDGE_KINDS = ("ddge_candidate", "ddge_evaluation", "ddge_proposal")


@dataclass(frozen=True, slots=True)
class ApprovedRun:
    """One verified projection explicitly approved before server startup."""

    run_id: str
    projection: OntologyProjection = field(repr=False)
    source_run_hash: str
    profile_identity: str
    integrity_level: str
    query: OntologyQueryService = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for value, name in (
            (self.run_id, "run ID"),
            (self.source_run_hash, "source run hash"),
            (self.profile_identity, "profile identity"),
            (self.integrity_level, "integrity level"),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be empty")
        object.__setattr__(self, "query", OntologyQueryService.from_projection(self.projection))

    def summary(self) -> dict[str, Any]:
        """Return portable provenance metadata without filesystem selectors."""

        return {
            "run_id": self.run_id,
            "source_run_hash": self.source_run_hash,
            "profile_identity": self.profile_identity,
            "integrity_level": self.integrity_level,
            "projection_digest": self.projection.projection_digest,
            "ontology_schema": self.projection.schema,
        }


class ApprovedRunRegistry:
    """Immutable lookup of projections approved before the server binds."""

    __slots__ = ("_runs",)

    def __init__(self, runs: Sequence[ApprovedRun]) -> None:
        values: dict[str, ApprovedRun] = {}
        for run in sorted(tuple(runs), key=lambda item: item.run_id):
            if run.run_id in values:
                raise ValueError(f"duplicate approved run ID {run.run_id!r}")
            values[run.run_id] = run
        self._runs: Mapping[str, ApprovedRun] = MappingProxyType(values)

    def __iter__(self) -> Iterator[ApprovedRun]:
        return iter(self._runs.values())

    def get(self, run_id: str) -> ApprovedRun:
        """Resolve an approved run by opaque ID and fail closed otherwise."""

        try:
            return self._runs[run_id]
        except KeyError as error:
            raise KeyError(f"unknown approved run {run_id!r}") from error

    @property
    def digests(self) -> tuple[str, ...]:
        """Return the stable identities of every served projection."""

        return tuple(run.projection.projection_digest for run in self._runs.values())


def _json_data(value: Any) -> Any:
    return json.loads(canonical_json(value))


def _success(data: Any, *runs: ApprovedRun) -> dict[str, Any]:
    return {
        "ok": True,
        "schema": API_SCHEMA,
        "projection_digests": [run.projection.projection_digest for run in runs],
        "data": _json_data(data),
    }


def _error(
    status_code: int,
    code: str,
    message: str,
    *,
    context: Mapping[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": False,
            "schema": API_SCHEMA,
            "projection_digests": [],
            "error": {
                "code": code,
                "message": message,
                "context": _json_data(context or {}),
            },
        },
    )


def _split_values(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _page_data(page: Any, serializer: Any) -> dict[str, Any]:
    return {
        "items": [serializer(item) for item in page.items],
        "next_cursor": page.next_cursor,
    }


def _path_data(result: Any) -> dict[str, Any]:
    return {
        "paths": [
            {
                "nodes": [ontology_ref_to_data(node) for node in path.nodes],
                "relations": [
                    relation_assertion_to_data(relation) for relation in path.relations
                ],
            }
            for path in result.paths
        ],
        "visited_records": result.visited_records,
        "truncated": result.truncated,
    }


def _bootstrap_html(policy: SecurityPolicy) -> str:
    template = (_STATIC_DIRECTORY / "index.html").read_text(encoding="utf-8")
    bootstrap = canonical_json(
        {
            "api_base": API_PREFIX,
            "api_minor": API_MINOR,
            "session_token": policy.session_token,
        }
    ).encode("utf-8")
    encoded = base64.urlsafe_b64encode(bootstrap).decode("ascii").rstrip("=")
    metadata = f'<meta name="ewm-bootstrap" content="{encoded}">' 
    return template.replace("</head>", f"    {metadata}\n  </head>", 1)


def _require_top_level_navigation(request: Request) -> None:
    if (
        request.headers.get("sec-fetch-dest") != "document"
        or request.headers.get("sec-fetch-mode") != "navigate"
        or request.headers.get("sec-fetch-site") not in {"none", "same-origin"}
    ):
        raise HTTPException(status_code=403, detail="top-level navigation required")


def create_workbench_app(
    registry: ApprovedRunRegistry,
    policy: SecurityPolicy,
) -> FastAPI:
    """Create a docs-disabled API and static shell bound to immutable projections."""

    app = FastAPI(
        title="Economic World Model Ontology Workbench API",
        version=f"{API_MAJOR}.{API_MINOR}.0",
        openapi_version="3.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        debug=False,
    )
    app.add_middleware(WorkbenchSecurityMiddleware, policy=policy)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        fields = [
            ".".join(str(part) for part in item["loc"] if part not in {"query", "body"})
            for item in error.errors()
        ]
        return _error(
            422,
            "validation_error",
            "request does not satisfy the versioned API contract",
            context={"fields": fields},
        )

    @app.exception_handler(QueryCostError)
    async def query_cost_handler(_request: Request, error: QueryCostError) -> JSONResponse:
        return _error(
            422,
            "query_cost",
            "query exceeds a declared cost bound",
            context=error.as_dict(),
        )

    @app.exception_handler(CursorError)
    async def cursor_error_handler(_request: Request, error: CursorError) -> JSONResponse:
        return _error(400, "invalid_cursor", str(error))

    @app.exception_handler(KeyError)
    async def missing_record_handler(_request: Request, _error_value: KeyError) -> JSONResponse:
        return _error(404, "not_found", "requested approved record was not found")

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        _request: Request,
        error: StarletteHTTPException,
    ) -> JSONResponse:
        if isinstance(error.detail, Mapping):
            code = str(error.detail.get("code", "request_rejected"))
            message = str(error.detail.get("message", "request was rejected"))
        else:
            code = "request_rejected"
            message = str(error.detail)
        return _error(error.status_code, code, message)

    @app.get("/", include_in_schema=False)
    async def index(request: Request) -> HTMLResponse:
        _require_top_level_navigation(request)
        return HTMLResponse(_bootstrap_html(policy))

    @app.get("/manifest.json", include_in_schema=False)
    async def manifest() -> FileResponse:
        return FileResponse(_STATIC_DIRECTORY / "manifest.json", media_type="application/json")

    app.mount("/assets", StaticFiles(directory=_STATIC_DIRECTORY / "assets"), name="assets")

    router = APIRouter(
        prefix=API_PREFIX,
        dependencies=[Depends(token_dependency(policy))],
        responses={
            status_code: {"model": ErrorEnvelope}
            for status_code in (400, 401, 403, 404, 413, 422)
        },
    )

    @router.get("/system", response_model=SuccessEnvelope)
    async def system() -> dict[str, Any]:
        return _success(
            {
                "api_major": API_MAJOR,
                "api_minor": API_MINOR,
                "run_count": sum(1 for _ in registry),
                "mode": "local-read-only",
            }
        )

    @router.get("/runs", response_model=SuccessEnvelope)
    async def runs() -> dict[str, Any]:
        return _success({"items": [run.summary() for run in registry]})

    @router.get("/runs/{run_id}", response_model=SuccessEnvelope)
    async def run(run_id: str) -> dict[str, Any]:
        approved = registry.get(run_id)
        return _success(approved.summary(), approved)

    @router.get("/objects", response_model=SuccessEnvelope)
    async def objects(
        run_id: Annotated[str, Query(min_length=1)],
        limit: Annotated[int | None, Query(gt=0)] = None,
        cursor: Annotated[str | None, Query(min_length=1)] = None,
        kinds: str | None = None,
        layers: str | None = None,
    ) -> dict[str, Any]:
        approved = registry.get(run_id)
        page = approved.query.objects(
            ObjectQuery(kinds=_split_values(kinds), layers=_split_values(layers)),
            limit=limit,
            cursor=cursor,
        )
        return _success(_page_data(page, ontology_object_to_data), approved)

    @router.get("/objects/{object_id}", response_model=SuccessEnvelope)
    async def ontology_object(object_id: str, run_id: str) -> dict[str, Any]:
        approved = registry.get(run_id)
        record = approved.query.record(object_id)
        return _success(ontology_record_to_data(record), approved)

    @router.get("/relations", response_model=SuccessEnvelope)
    async def relations(
        run_id: str,
        limit: Annotated[int | None, Query(gt=0)] = None,
        cursor: Annotated[str | None, Query(min_length=1)] = None,
        relation_types: str | None = None,
        incident_ids: str | None = None,
        direction: Literal["outgoing", "incoming", "both"] = "both",
    ) -> dict[str, Any]:
        approved = registry.get(run_id)
        page = approved.query.relations(
            RelationQuery(
                relation_types=_split_values(relation_types),
                incident_ids=_split_values(incident_ids),
                direction=direction,
            ),
            limit=limit,
            cursor=cursor,
        )
        return _success(_page_data(page, relation_assertion_to_data), approved)

    @router.get("/paths", response_model=SuccessEnvelope)
    async def paths(
        run_id: str,
        start_id: str,
        target_id: str,
        max_depth: Annotated[int, Query(ge=0)] = 1,
        limit: Annotated[int | None, Query(gt=0)] = None,
        relation_types: str | None = None,
        direction: Literal["outgoing", "incoming", "both"] = "outgoing",
    ) -> dict[str, Any]:
        approved = registry.get(run_id)
        result = approved.query.paths(
            PathQuery(
                start_id=start_id,
                target_id=target_id,
                max_depth=max_depth,
                limit=limit,
                filter=PathFilter(
                    relation_types=_split_values(relation_types),
                    direction=direction,
                ),
            )
        )
        return _success(_path_data(result), approved)

    async def object_kind_page(
        run_id: str,
        kinds: tuple[str, ...],
        limit: int | None,
        cursor: str | None,
    ) -> tuple[ApprovedRun, dict[str, Any]]:
        approved = registry.get(run_id)
        page = approved.query.objects(
            ObjectQuery(kinds=kinds),
            limit=limit,
            cursor=cursor,
        )
        return approved, _page_data(page, ontology_object_to_data)

    @router.get("/events", response_model=SuccessEnvelope)
    async def events(
        run_id: str,
        limit: Annotated[int | None, Query(gt=0)] = None,
        cursor: Annotated[str | None, Query(min_length=1)] = None,
    ) -> dict[str, Any]:
        approved, data = await object_kind_page(run_id, _EVENT_KINDS, limit, cursor)
        return _success(data, approved)

    @router.get("/states", response_model=SuccessEnvelope)
    async def states(
        run_id: str,
        limit: Annotated[int | None, Query(gt=0)] = None,
        cursor: Annotated[str | None, Query(min_length=1)] = None,
    ) -> dict[str, Any]:
        approved, data = await object_kind_page(run_id, _STATE_KINDS, limit, cursor)
        return _success(data, approved)

    @router.get("/measurements", response_model=SuccessEnvelope)
    async def measurements(
        run_id: str,
        limit: Annotated[int | None, Query(gt=0)] = None,
        cursor: Annotated[str | None, Query(min_length=1)] = None,
        names: str | None = None,
        statuses: str | None = None,
        units: str | None = None,
    ) -> dict[str, Any]:
        approved = registry.get(run_id)
        page = approved.query.measurements(
            MeasurementQuery(
                names=_split_values(names),
                statuses=_split_values(statuses),
                units=_split_values(units),
            ),
            limit=limit,
            cursor=cursor,
        )
        return _success(_page_data(page, measurement_to_data), approved)

    @router.get("/claims", response_model=SuccessEnvelope)
    async def claims(
        run_id: str,
        limit: Annotated[int | None, Query(gt=0)] = None,
        cursor: Annotated[str | None, Query(min_length=1)] = None,
        classifications: str | None = None,
    ) -> dict[str, Any]:
        approved = registry.get(run_id)
        page = approved.query.claims(
            ClaimQuery(classifications=_split_values(classifications)),
            limit=limit,
            cursor=cursor,
        )
        return _success(_page_data(page, ontology_object_to_data), approved)

    @router.get("/evidence", response_model=SuccessEnvelope)
    async def evidence(
        run_id: str,
        limit: Annotated[int | None, Query(gt=0)] = None,
        cursor: Annotated[str | None, Query(min_length=1)] = None,
        classifications: str | None = None,
    ) -> dict[str, Any]:
        approved = registry.get(run_id)
        page = approved.query.evidence(
            EvidenceQuery(classifications=_split_values(classifications)),
            limit=limit,
            cursor=cursor,
        )
        return _success(_page_data(page, ontology_object_to_data), approved)

    @router.get("/ddge-candidates", response_model=SuccessEnvelope)
    async def ddge_candidates(
        run_id: str,
        limit: Annotated[int | None, Query(gt=0)] = None,
        cursor: Annotated[str | None, Query(min_length=1)] = None,
    ) -> dict[str, Any]:
        approved, data = await object_kind_page(run_id, _DDGE_KINDS, limit, cursor)
        return _success(data, approved)

    @router.post("/comparisons", response_model=SuccessEnvelope)
    async def comparisons(
        request: ComparisonRequest,
        response: Response,
        idempotency_key: Annotated[
            str,
            Header(alias="Idempotency-Key", min_length=1, max_length=200),
        ],
    ) -> dict[str, Any]:
        left = registry.get(request.left_run_id)
        right = registry.get(request.right_run_id)
        result = compare_projections(left.projection, right.projection)
        request_data = request.model_dump(mode="json")
        result_data = _json_data(asdict(result))
        response.headers["Idempotency-Key"] = idempotency_key
        return _success(
            {
                "comparison_id": content_digest(
                    {
                        "request": request_data,
                        "projections": [
                            left.projection.projection_digest,
                            right.projection.projection_digest,
                        ],
                    }
                ),
                "request": request_data,
                "result": result_data,
            },
            left,
            right,
        )

    @router.post("/snapshot-exports", response_model=SuccessEnvelope)
    async def snapshot_exports(
        request: SnapshotExportRequest,
        response: Response,
        idempotency_key: Annotated[
            str,
            Header(alias="Idempotency-Key", min_length=1, max_length=200),
        ],
    ) -> dict[str, Any]:
        approved = registry.get(request.run_id)
        request_data = request.model_dump(mode="json")
        response.headers["Idempotency-Key"] = idempotency_key
        return _success(
            {
                "export_id": content_digest(
                    {
                        "request": request_data,
                        "projection_digest": approved.projection.projection_digest,
                    }
                ),
                "status": "planned",
                "request": request_data,
            },
            approved,
        )

    app.include_router(router)
    return app
