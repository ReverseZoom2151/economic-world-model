import { Instance, Instances } from "@react-three/drei";

import type { SceneNode } from "./layout";

interface InstancedNodesProps {
  readonly nodes: ReadonlyArray<SceneNode>;
  readonly selectedId: string | null;
  readonly highlightedNodeIds: ReadonlySet<string>;
  readonly onSelect: (id: string) => void;
  readonly onHover: (id: string | null) => void;
}

function SharedGeometry({ shape }: { readonly shape: SceneNode["shape"] }) {
  switch (shape) {
    case "circle":
      return <sphereGeometry args={[0.18, 12, 8]} />;
    case "diamond":
      return <octahedronGeometry args={[0.22, 0]} />;
    case "hexagon":
      return <cylinderGeometry args={[0.2, 0.2, 0.25, 6]} />;
    case "triangle":
      return <tetrahedronGeometry args={[0.25, 0]} />;
    case "rectangle":
      return <boxGeometry args={[0.34, 0.22, 0.22]} />;
  }
}

const SHAPES: ReadonlyArray<SceneNode["shape"]> = [
  "circle",
  "diamond",
  "hexagon",
  "rectangle",
  "triangle",
];

export function InstancedNodes({
  nodes,
  selectedId,
  highlightedNodeIds,
  onSelect,
  onHover,
}: InstancedNodesProps) {
  return (
    <>
      {SHAPES.map((shape) => {
        const group = nodes.filter((node) => node.shape === shape);
        if (group.length === 0) return null;
        return (
          <Instances key={shape} limit={group.length} range={group.length}>
            <SharedGeometry shape={shape} />
            <meshBasicMaterial toneMapped={false} />
            {group.map((node) => (
              <Instance
                key={node.id}
                position={node.position}
                color={
                  selectedId === node.id
                    ? "#c7f24a"
                    : highlightedNodeIds.has(node.id)
                      ? "#f3f3eb"
                      : node.color
                }
                scale={selectedId === node.id ? 1.55 : highlightedNodeIds.has(node.id) ? 1.25 : 1}
                onClick={(event) => {
                  event.stopPropagation();
                  onSelect(node.id);
                }}
                onPointerOver={(event) => {
                  event.stopPropagation();
                  onHover(node.id);
                }}
                onPointerOut={() => onHover(null)}
              />
            ))}
          </Instances>
        );
      })}
    </>
  );
}
