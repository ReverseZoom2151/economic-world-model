"""Immutable contracts for explicit geographic placement and overlays."""

from __future__ import annotations

from dataclasses import dataclass

from ..graph.model import OntologyObject, OntologyProjection, RelationAssertion


@dataclass(frozen=True, slots=True)
class GeoPlacement:
    """One ontology object placed only by an explicit geographic relation."""

    subject: OntologyObject
    anchor: OntologyObject
    relation: RelationAssertion


@dataclass(frozen=True, slots=True)
class GeoOverlayApplication:
    """A resealed projection and the external overlay identity applied to it."""

    projection: OntologyProjection
    overlay_digest: str
    anchor_count: int


class GeoOverlayError(ValueError):
    """Raised when a geographic sidecar is unsafe, ambiguous, or invalid."""
