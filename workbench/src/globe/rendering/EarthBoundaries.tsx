import { useMemo } from "react";
import { BufferGeometry, Float32BufferAttribute } from "three";

import naturalEarth from "../../assets/natural-earth-110m.json";
import { latLonToCartesian } from "../geometry";

interface GeoJsonGeometry {
  readonly type: string;
  readonly coordinates: unknown;
}

interface GeoJsonFeature {
  readonly geometry: GeoJsonGeometry | null;
}

interface GeoJsonCollection {
  readonly features: ReadonlyArray<GeoJsonFeature>;
}

type Coordinate = readonly [number, number];

function isCoordinate(value: unknown): value is Coordinate {
  return (
    Array.isArray(value) &&
    value.length >= 2 &&
    typeof value[0] === "number" &&
    Number.isFinite(value[0]) &&
    typeof value[1] === "number" &&
    Number.isFinite(value[1])
  );
}

function rings(geometry: GeoJsonGeometry | null): ReadonlyArray<ReadonlyArray<Coordinate>> {
  if (geometry === null || !Array.isArray(geometry.coordinates)) return [];
  if (geometry.type === "Polygon") {
    return geometry.coordinates.filter(Array.isArray).map((ring) => ring.filter(isCoordinate));
  }
  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates
      .filter(Array.isArray)
      .flatMap((polygon) => polygon.filter(Array.isArray).map((ring) => ring.filter(isCoordinate)));
  }
  return [];
}

export function EarthBoundaries() {
  const geometry = useMemo(() => {
    const positions: number[] = [];
    const collection = naturalEarth as GeoJsonCollection;
    for (const feature of collection.features) {
      for (const ring of rings(feature.geometry)) {
        for (let index = 1; index < ring.length; index += 1) {
          const previous = ring[index - 1];
          const current = ring[index];
          if (previous === undefined || current === undefined) continue;
          positions.push(
            ...latLonToCartesian(previous[1], previous[0], 3.012),
            ...latLonToCartesian(current[1], current[0], 3.012),
          );
        }
      }
    }
    const result = new BufferGeometry();
    result.setAttribute("position", new Float32BufferAttribute(positions, 3));
    return result;
  }, []);
  return (
    <lineSegments geometry={geometry} raycast={() => null}>
      <lineBasicMaterial color="#9ba092" transparent opacity={0.7} />
    </lineSegments>
  );
}
