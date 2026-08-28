import { useEffect, useMemo } from "react";
import { BufferGeometry, Float32BufferAttribute } from "three";

import type { SceneRelation } from "./layout";

interface RelationLinesProps {
  readonly relations: ReadonlyArray<SceneRelation>;
  readonly highlightedRelationIds: ReadonlySet<string>;
}

function relationColor(type: string): string {
  const colors = ["#286f6c", "#805c14", "#6b4c7a", "#8b4438", "#496584", "#51613b"];
  let hash = 0;
  for (let index = 0; index < type.length; index += 1) hash = (hash * 31 + type.charCodeAt(index)) | 0;
  return colors[Math.abs(hash) % colors.length]!;
}

function LineGroup({ relations, color, opacity }: {
  readonly relations: ReadonlyArray<SceneRelation>;
  readonly color: string;
  readonly opacity: number;
}) {
  const geometry = useMemo(() => {
    const positions = relations.flatMap((relation) => [
      ...relation.sourcePosition,
      ...relation.targetPosition,
    ]);
    const result = new BufferGeometry();
    result.setAttribute("position", new Float32BufferAttribute(positions, 3));
    return result;
  }, [relations]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return (
    <lineSegments geometry={geometry} raycast={() => null}>
      <lineBasicMaterial color={color} transparent opacity={opacity} />
    </lineSegments>
  );
}

export function RelationLines({ relations, highlightedRelationIds }: RelationLinesProps) {
  const groups = useMemo(() => {
    const result = new Map<string, SceneRelation[]>();
    for (const relation of relations) {
      const key = highlightedRelationIds.has(relation.id)
        ? "path"
        : relation.relationType;
      result.set(key, [...(result.get(key) ?? []), relation]);
    }
    return [...result].sort(([left], [right]) => left.localeCompare(right));
  }, [highlightedRelationIds, relations]);
  return (
    <>
      {groups.map(([type, grouped]) => (
        <LineGroup
          key={type}
          relations={grouped}
          color={type === "path" ? "#c7f24a" : relationColor(type)}
          opacity={type === "path" ? 1 : 0.48}
        />
      ))}
    </>
  );
}
