"""Loopback-only socket binding for the local ontology workbench."""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass, field

import uvicorn

from .api import ApprovedRunRegistry, create_workbench_app
from .security import SecurityPolicy, create_session_token


@dataclass(frozen=True, slots=True)
class WorkbenchServerConfig:
    """Validated configuration for a single loopback server."""

    host: str = "127.0.0.1"
    port: int = 0
    max_request_body_bytes: int = 1_048_576

    def __post_init__(self) -> None:
        try:
            is_loopback = ipaddress.ip_address(self.host).is_loopback
        except ValueError:
            is_loopback = self.host == "localhost"
        if not is_loopback:
            raise ValueError("workbench host must resolve to a loopback interface")
        if not 0 <= self.port <= 65_535:
            raise ValueError("workbench port must be between 0 and 65535")
        if self.max_request_body_bytes <= 0:
            raise ValueError("request body limit must be positive")


@dataclass(slots=True)
class BoundWorkbenchServer:
    """A configured server with an already-reserved loopback socket."""

    host: str
    port: int
    origin: str
    session_token: str = field(repr=False)
    server: uvicorn.Server
    socket: socket.socket = field(repr=False)

    def close(self) -> None:
        """Release the reserved socket without starting the server."""

        self.socket.close()


def bind_workbench_server(
    registry: ApprovedRunRegistry,
    config: WorkbenchServerConfig | None = None,
) -> BoundWorkbenchServer:
    """Reserve a loopback socket and configure a no-access-log Uvicorn server."""

    selected = config or WorkbenchServerConfig()
    family = socket.AF_INET6 if ":" in selected.host else socket.AF_INET
    bound_socket = socket.socket(family, socket.SOCK_STREAM)
    try:
        bound_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        bound_socket.bind((selected.host, selected.port))
        bound_socket.listen(128)
        actual_port = int(bound_socket.getsockname()[1])
        rendered_host = f"[{selected.host}]" if family == socket.AF_INET6 else selected.host
        origin = f"http://{rendered_host}:{actual_port}"
        token = create_session_token()
        policy = SecurityPolicy(
            session_token=token,
            allowed_hosts=(selected.host,),
            allowed_origins=(origin,),
            max_request_body_bytes=selected.max_request_body_bytes,
        )
        application = create_workbench_app(registry, policy)
        server = uvicorn.Server(
            uvicorn.Config(
                application,
                host=selected.host,
                port=actual_port,
                access_log=False,
                log_level="warning",
                proxy_headers=False,
            )
        )
    except Exception:
        bound_socket.close()
        raise
    return BoundWorkbenchServer(
        host=selected.host,
        port=actual_port,
        origin=origin,
        session_token=token,
        server=server,
        socket=bound_socket,
    )
