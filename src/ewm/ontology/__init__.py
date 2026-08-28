"""Typed, read-only projections of verified Economic World Model evidence."""

from ewm._internal.imports import register_module_aliases

from .geography import (
    GEO_OVERLAY_SCHEMA,
    GeoOverlayApplication,
    GeoOverlayError,
    GeoPlacement,
    apply_geo_overlay,
    geographic_placements,
)
from .graph.model import (
    COVERAGE_STATUSES,
    GEO_ANCHOR_BASES,
    GEO_COORDINATE_REFERENCE_SYSTEMS,
    GEO_EVIDENCE_CLASSIFICATIONS,
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
        "snapshot": "snapshots.contracts",
        "verification": "projection.verification",
    },
)

__all__ = [
    "COVERAGE_STATUSES",
    "DEFAULT_PROFILES",
    "GEO_ANCHOR_BASES",
    "GEO_COORDINATE_REFERENCE_SYSTEMS",
    "GEO_EVIDENCE_CLASSIFICATIONS",
    "GEO_OVERLAY_SCHEMA",
    "ONTOLOGY_LAYERS",
    "CoverageEntry",
    "GeoOverlayApplication",
    "GeoOverlayError",
    "GeoPlacement",
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
    "apply_geo_overlay",
    "compile_run_projection",
    "geographic_placements",
    "load_projection_bundle",
    "verify_projection_bundle",
    "write_projection_bundle",
]
