"""Loopback HTTP transport controls for the local ontology workbench."""

from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import parse_qsl

from fastapi import HTTPException, Security, status
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .contracts import API_MINOR, API_MINOR_HEADER, API_SCHEMA, TOKEN_HEADER

_FILESYSTEM_QUERY_FIELDS = frozenset(
    {"bundle", "file", "path", "projection", "root", "run_dir", "source_dir"}
)
_SECRET_QUERY_FIELDS = frozenset({"api_key", "key", "session_token", "token"})
_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'self'; base-uri 'none'; connect-src 'self'; frame-ancestors 'none'; "
        "form-action 'none'; img-src 'self' data:; object-src 'none'; script-src 'self'; "
        "style-src 'self'"
    ),
    "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


@dataclass(frozen=True, slots=True)
class SecurityPolicy:
    """Exact hosts, origins, token, and request-size cap for one server."""

    session_token: str
    allowed_hosts: tuple[str, ...]
    allowed_origins: tuple[str, ...]
    max_request_body_bytes: int = 1_048_576

    def __post_init__(self) -> None:
        if len(self.session_token) < 32:
            raise ValueError("session token must contain at least 32 characters")
        if not self.allowed_hosts or any(not host.strip() for host in self.allowed_hosts):
            raise ValueError("allowed hosts must contain non-empty values")
        if not self.allowed_origins or any(
            not origin.startswith("http://") for origin in self.allowed_origins
        ):
            raise ValueError("allowed origins must contain explicit local HTTP origins")
        if self.max_request_body_bytes <= 0:
            raise ValueError("request body limit must be positive")
        object.__setattr__(self, "allowed_hosts", tuple(sorted(set(self.allowed_hosts))))
        object.__setattr__(self, "allowed_origins", tuple(sorted(set(self.allowed_origins))))


def create_session_token() -> str:
    """Create a high-entropy token intended only for process memory."""

    return secrets.token_urlsafe(32)


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": False,
            "schema": API_SCHEMA,
            "projection_digests": [],
            "error": {"code": code, "message": message, "context": {}},
        },
    )


def _hostname(host_header: str) -> str:
    if host_header.startswith("["):
        end = host_header.find("]")
        return host_header[1:end] if end >= 0 else host_header
    return host_header.rsplit(":", 1)[0] if host_header.count(":") == 1 else host_header


class WorkbenchSecurityMiddleware:
    """Reject untrusted transport inputs before request parsing or routing."""

    def __init__(self, app: ASGIApp, *, policy: SecurityPolicy) -> None:
        self.app = app
        self.policy = policy

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        path = str(scope.get("path", ""))
        response: JSONResponse | None = None
        if _hostname(headers.get("host", "")) not in self.policy.allowed_hosts:
            response = _error_response(400, "invalid_host", "request host is not approved")
        else:
            query_fields = {
                key.lower()
                for key, _ in parse_qsl(
                    scope.get("query_string", b"").decode("utf-8", errors="replace"),
                    keep_blank_values=True,
                )
            }
            if query_fields & _FILESYSTEM_QUERY_FIELDS:
                response = _error_response(
                    400,
                    "filesystem_selector",
                    "filesystem selectors are not accepted by the API",
                )
            elif query_fields & _SECRET_QUERY_FIELDS:
                response = _error_response(
                    400,
                    "secret_in_query",
                    "credentials are not accepted in URLs",
                )

        downstream_receive = receive
        if response is None and path.startswith("/api/"):
            origin = headers.get("origin")
            safe_same_origin_fetch = (
                origin is None
                and scope.get("method") in {"GET", "HEAD"}
                and headers.get("sec-fetch-site") == "same-origin"
                and headers.get("sec-fetch-mode") in {"cors", "same-origin"}
                and headers.get("sec-fetch-dest") == "empty"
            )
            if origin not in self.policy.allowed_origins and not safe_same_origin_fetch:
                response = _error_response(403, "invalid_origin", "request origin is not approved")
            else:
                content_length = headers.get("content-length")
                if content_length is not None:
                    try:
                        too_large = int(content_length) > self.policy.max_request_body_bytes
                    except ValueError:
                        too_large = True
                    if too_large:
                        response = _error_response(
                            413,
                            "request_too_large",
                            "request body exceeds the configured limit",
                        )

        if (
            response is None
            and path.startswith("/api/")
            and scope.get("method") in {"PATCH", "POST", "PUT"}
        ):
            buffered: list[Message] = []
            observed = 0
            while True:
                message = await receive()
                buffered.append(message)
                if message["type"] == "http.disconnect":
                    response = _error_response(
                        400,
                        "request_disconnected",
                        "request body ended before it could be validated",
                    )
                    break
                observed += len(message.get("body", b""))
                if observed > self.policy.max_request_body_bytes:
                    response = _error_response(
                        413,
                        "request_too_large",
                        "request body exceeds the configured limit",
                    )
                    break
                if not message.get("more_body", False):
                    break

            position = 0

            async def replay_receive() -> Message:
                nonlocal position
                if position < len(buffered):
                    message = buffered[position]
                    position += 1
                    return message
                return await receive()

            downstream_receive = replay_receive

        async def secure_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", ()))
                names = {name.lower() for name, _ in response_headers}
                additions = {API_MINOR_HEADER: str(API_MINOR), **_SECURITY_HEADERS}
                for name, value in additions.items():
                    if name.lower().encode("latin-1") not in names:
                        response_headers.append(
                            (name.lower().encode("latin-1"), value.encode("latin-1"))
                        )
                message = {**message, "headers": response_headers}
            await send(message)

        if response is not None:
            await response(scope, downstream_receive, secure_send)
            return
        await self.app(scope, downstream_receive, secure_send)


def token_dependency(policy: SecurityPolicy) -> Callable[..., Awaitable[None]]:
    """Build an OpenAPI-visible exact-match header authentication dependency."""

    header = APIKeyHeader(name=TOKEN_HEADER, auto_error=False)

    async def require_token(provided: str | None = Security(header)) -> None:
        if provided is None or not secrets.compare_digest(provided, policy.session_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "unauthorized", "message": "valid session token required"},
            )

    return require_token
