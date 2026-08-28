import { useMemo } from "react";
import { BufferGeometry, Float32BufferAttribute, Quaternion, Vector3 } from "three";

import { EARTH_RADIUS, latLonToCartesian, type TaggedGeoPlacement } from "../geometry";

interface UncertaintyRingsProps {
  readonly placements: ReadonlyArray<TaggedGeoPlacement>;
}

const SEGMENTS = 24;
const EARTH_CIRCUMFERENCE_KM = 40_075;

export function UncertaintyRings({ placements }: UncertaintyRingsProps) {
  const geometry = useMemo(() => {
    const positions: number[] = [];
    for (const placement of placements) {
      const center = new Vector3(
        ...latLonToCartesian(placement.latitude, placement.longitude, 3.062),
      );
      const normal = center.clone().normalize();
      const rotation = new Quaternion().setFromUnitVectors(new Vector3(0, 0, 1), normal);
      const angularRadius = Math.max(
        0.012,
        Math.min(0.16, (placement.uncertaintyKm / EARTH_CIRCUMFERENCE_KM) * Math.PI * 2),
      );
      const localRadius = EARTH_RADIUS * angularRadius;
      const points = Array.from({ length: SEGMENTS + 1 }, (_, index) => {
        const angle = (index / SEGMENTS) * Math.PI * 2;
        return new Vector3(Math.cos(angle) * localRadius, Math.sin(angle) * localRadius, 0)
          .applyQuaternion(rotation)
          .add(center);
      });
      for (let index = 1; index < points.length; index += 1) {
        const previous = points[index - 1];
        const current = points[index];
        if (previous !== undefined && current !== undefined) {
          positions.push(...previous.toArray(), ...current.toArray());
        }
      }
    }
    const result = new BufferGeometry();
    result.setAttribute("position", new Float32BufferAttribute(positions, 3));
    return result;
  }, [placements]);
  return (
    <lineSegments geometry={geometry} raycast={() => null}>
      <lineBasicMaterial color="#f3f3eb" transparent opacity={0.62} />
    </lineSegments>
  );
}
