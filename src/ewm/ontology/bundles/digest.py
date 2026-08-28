"""Canonical semantic identity for ontology projections."""

from __future__ import annotations

from typing import Any

from ewm.core.serialization import content_digest

from ..identity import projection_to_data
from ..model import OntologyProjection


def _semantic_projection_data(projection: OntologyProjection) -> dict[str, Any]:
    data = projection_to_data(projection)
    return {
        key: value
        for key, value in data.items()
        if key not in {"record_type", "projection_digest"}
    }


def compute_projection_digest(projection: OntologyProjection) -> str:
    """Return graph and coverage identity without circular self-inclusion."""

    return content_digest(_semantic_projection_data(projection))
