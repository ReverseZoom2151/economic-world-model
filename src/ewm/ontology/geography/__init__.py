"""Explicit geographic ontology extension."""

from .contracts import GeoOverlayApplication, GeoOverlayError, GeoPlacement
from .overlay import GEO_OVERLAY_SCHEMA, apply_geo_overlay
from .service import geographic_placements

__all__ = [
    "GEO_OVERLAY_SCHEMA",
    "GeoOverlayApplication",
    "GeoOverlayError",
    "GeoPlacement",
    "apply_geo_overlay",
    "geographic_placements",
]
