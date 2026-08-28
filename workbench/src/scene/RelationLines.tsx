import { useMemo } from "react";
import { BufferGeometry, Float32BufferAttribute } from "three";

import type { SceneRelation } from "./layout";

interface RelationLinesProps {
  readonly relations: ReadonlyArray<SceneRelation>;
}

export function RelationLines({ relations }: RelationLinesProps) {
  const geometry = useMemo(() => {
    const positions = relations.flatMap((relation) => [
      ...relation.sourcePosition,
      ...relation.targetPosition,
    ]);
    const result = new BufferGeometry();
    result.setAttribute("position", new Float32BufferAttribute(positions, 3));
    return result;
  }, [relations]);
  return (
    <lineSegments geometry={geometry} raycast={() => null}>
      <lineBasicMaterial color="#6e716a" transparent opacity={0.48} />
    </lineSegments>
  );
}
