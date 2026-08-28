"""Read explicit geographic placements without spatial inference."""

from __future__ import annotations

from ..graph.model import OntologyProjection
from .contracts import GeoPlacement


def geographic_placements(projection: OntologyProjection) -> tuple[GeoPlacement, ...]:
    """Return subjects with a stored ``GEO_ANCHORED_AT`` relation only."""

    objects = {item.ref: item for item in projection.objects}
    placements: list[GeoPlacement] = []
    for relation in sorted(projection.relations, key=lambda item: item.ref.id):
        if relation.relation_type != "GEO_ANCHORED_AT":
            continue
        subject = objects.get(relation.source)
        anchor = objects.get(relation.target)
        if subject is None or anchor is None or anchor.ref.kind != "geo_anchor":
            continue
        placements.append(GeoPlacement(subject, anchor, relation))
    return tuple(sorted(placements, key=lambda item: item.subject.ref.id))
