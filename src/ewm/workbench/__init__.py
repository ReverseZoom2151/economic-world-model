"""Local research workbench transport and static investigation export."""

from ewm._internal.imports import register_module_aliases

register_module_aliases(
    __name__,
    {
        "api": "http.api",
        "contracts": "http.contracts",
        "export": "snapshots.export",
        "openapi": "http.openapi",
        "security": "http.security",
        "server": "http.server",
    },
)
