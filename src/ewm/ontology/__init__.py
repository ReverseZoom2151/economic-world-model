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
    "ONTOLOGY_LAYERS",
    "CoverageEntry",
    "Measurement",
    "OntologyObject",
    "OntologyProjection",
    "OntologyRef",
    "RelationAssertion",
    "SourceLocator",
]
