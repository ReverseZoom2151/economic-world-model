import type {
  OntologyObjectContract,
  RelationContract,
} from "../data/InvestigationDataSource";

export const EARTH_RADIUS = 3;
export const MAX_GLOBE_FLOWS = 500;

type ValidityValue = number | string | null;

export interface GeoValidity {
  readonly start: ValidityValue;
  readonly end: ValidityValue;
}

export interface GeoPlacement {
  readonly subject: OntologyObjectContract;
  readonly anchor: OntologyObjectContract;
  readonly relation: RelationContract;
  readonly latitude: number;
  readonly longitude: number;
  readonly crs: "EPSG:4326";
  readonly basis: "observed" | "declared" | "externally_supplied";
  readonly evidenceClassification: "researcher_declared";
  readonly validity: GeoValidity;
  readonly uncertaintyKm: number;
}

export interface TaggedGeoPlacement extends GeoPlacement {
  readonly runId: string;
  readonly runRole: "active" | "comparison";
}

export interface GeoFlow {
  readonly relation: RelationContract;
  readonly source: TaggedGeoPlacement;
  readonly target: TaggedGeoPlacement;
}

function record(value: unknown): Readonly<Record<string, unknown>> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Readonly<Record<string, unknown>>)
    : null;
}

function finite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function validityValue(value: unknown): value is ValidityValue {
  return value === null || typeof value === "string" || finite(value);
}

function parseAnchor(anchor: OntologyObjectContract): Omit<GeoPlacement, "subject" | "relation" | "anchor"> | null {
  const { properties } = anchor;
  const validity = record(properties.validity);
  const basis = properties.anchor_basis;
  if (
    anchor.ref.kind !== "geo_anchor" ||
    properties.crs !== "EPSG:4326" ||
    !finite(properties.latitude) ||
    properties.latitude < -90 ||
    properties.latitude > 90 ||
    !finite(properties.longitude) ||
    properties.longitude < -180 ||
    properties.longitude > 180 ||
    (basis !== "observed" && basis !== "declared" && basis !== "externally_supplied") ||
    properties.evidence_classification !== "researcher_declared" ||
    validity === null ||
    !validityValue(validity.start) ||
    !validityValue(validity.end) ||
    !finite(properties.uncertainty_km) ||
    properties.uncertainty_km < 0
  ) {
    return null;
  }
  return {
    crs: "EPSG:4326",
    latitude: properties.latitude,
    longitude: properties.longitude,
    basis,
    evidenceClassification: "researcher_declared",
    validity: { start: validity.start, end: validity.end },
    uncertaintyKm: properties.uncertainty_km,
  };
}

function activeAt(validity: GeoValidity, time: number | null): boolean {
  if (time === null) return true;
  if (typeof validity.start !== "number" || typeof validity.end !== "number") return true;
  return validity.start <= time && time <= validity.end;
}

export function eligibleGeoPlacements(
  objects: ReadonlyArray<OntologyObjectContract>,
  relations: ReadonlyArray<RelationContract>,
  time: number | null,
): ReadonlyArray<GeoPlacement> {
  const objectsById = new Map(objects.map((object) => [object.ref.id, object]));
  const placements: GeoPlacement[] = [];
  for (const relation of relations) {
    if (relation.relation_type !== "GEO_ANCHORED_AT") continue;
    const subject = objectsById.get(relation.source.id);
    const anchor = objectsById.get(relation.target.id);
    if (subject === undefined || anchor === undefined) continue;
    const parsed = parseAnchor(anchor);
    if (parsed === null || !activeAt(parsed.validity, time)) continue;
    placements.push({ subject, anchor, relation, ...parsed });
  }
  return placements.sort((left, right) => left.subject.ref.id.localeCompare(right.subject.ref.id));
}

export function boundedGeoFlows(
  placements: ReadonlyArray<TaggedGeoPlacement>,
  relations: ReadonlyArray<RelationContract>,
  limit = MAX_GLOBE_FLOWS,
): ReadonlyArray<GeoFlow> {
  const bySubject = new Map(placements.map((placement) => [placement.subject.ref.id, placement]));
  return relations
    .filter((relation) => relation.relation_type !== "GEO_ANCHORED_AT")
    .flatMap((relation) => {
      const source = bySubject.get(relation.source.id);
      const target = bySubject.get(relation.target.id);
      return source === undefined || target === undefined ? [] : [{ relation, source, target }];
    })
    .sort((left, right) => left.relation.ref.id.localeCompare(right.relation.ref.id))
    .slice(0, Math.max(0, limit));
}

export function latLonToCartesian(
  latitude: number,
  longitude: number,
  radius = EARTH_RADIUS,
): readonly [number, number, number] {
  const latitudeRadians = (latitude * Math.PI) / 180;
  const longitudeRadians = (longitude * Math.PI) / 180;
  const cosine = Math.cos(latitudeRadians);
  return [
    radius * cosine * Math.cos(longitudeRadians),
    radius * Math.sin(latitudeRadians),
    -radius * cosine * Math.sin(longitudeRadians),
  ];
}

export function geoLabel(placement: GeoPlacement): string {
  const naturalKey = placement.subject.properties.natural_key;
  return typeof naturalKey === "string" && naturalKey.trim()
    ? naturalKey
    : placement.subject.ref.id;
}
