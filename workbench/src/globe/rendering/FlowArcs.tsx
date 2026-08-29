import { useMemo } from "react";
import {
  BufferGeometry,
  Float32BufferAttribute,
  QuadraticBezierCurve3,
  Vector3,
} from "three";

import { latLonToCartesian, type GeoFlow } from "../geometry";

interface FlowArcsProps {
  readonly flows: ReadonlyArray<GeoFlow>;
}

export function FlowArcs({ flows }: FlowArcsProps) {
  const geometry = useMemo(() => {
    const positions: number[] = [];
    for (const flow of flows) {
      const start = new Vector3(...latLonToCartesian(flow.source.latitude, flow.source.longitude, 3.04));
      const end = new Vector3(...latLonToCartesian(flow.target.latitude, flow.target.longitude, 3.04));
      const lift = Math.min(0.75, 0.12 + start.distanceTo(end) * 0.18);
      const midpoint = start.clone().add(end).multiplyScalar(0.5).normalize().multiplyScalar(3.04 + lift);
      const points = new QuadraticBezierCurve3(start, midpoint, end).getPoints(16);
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
  }, [flows]);
  return (
    <lineSegments geometry={geometry} raycast={() => null}>
      <lineBasicMaterial color="#c7f24a" transparent opacity={0.82} />
    </lineSegments>
  );
}
