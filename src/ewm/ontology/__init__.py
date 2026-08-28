"""Typed, read-only projections of verified Economic World Model evidence."""

from ewm._internal.imports import register_module_aliases

from .graph.model import (
    COVERAGE_STATUSES,
    ONTOLOGY_LAYERS,
    CoverageEntry,
    Measurement,
    OntologyObject,
    OntologyProjection,
    OntologyRef,
    RelationAssertion,
    SourceLocator,
)
from .profiles import DEFAULT_PROFILES
from .projection.compiler import (
    ProjectionCompilation,
    ProjectionCompilationError,
    compile_run_projection,
)
from .projection.service import write_projection_bundle
from .projection.verification import (
    ProjectionVerificationError,
    ProjectionVerificationReport,
    load_projection_bundle,
    verify_projection_bundle,
)

register_module_aliases(
    __name__,
    {
        "bundles": "projection.bundles",
        "compiler": "projection.compiler",
        "identity": "graph.identity",
        "model": "graph.model",
        "schema": "graph.schema",
        "verification": "projection.verification",
    },
)

__all__ = [
    "COVERAGE_STATUSES",
    "DEFAULT_PROFILES",
    "ONTOLOGY_LAYERS",
    "CoverageEntry",
    "Measurement",
    "OntologyObject",
    "OntologyProjection",
    "OntologyRef",
    "ProjectionCompilation",
    "ProjectionCompilationError",
    "ProjectionVerificationError",
    "ProjectionVerificationReport",
    "RelationAssertion",
    "SourceLocator",
    "compile_run_projection",
    "load_projection_bundle",
    "verify_projection_bundle",
    "write_projection_bundle",
]
