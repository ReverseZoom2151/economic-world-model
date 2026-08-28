import { Html } from "@react-three/drei";

import type { GraphDensity } from "../visuals/graph/model";
import type { SceneNode } from "./layout";

interface SceneLabelsProps {
  readonly nodes: ReadonlyArray<SceneNode>;
  readonly selectedId: string | null;
  readonly hoveredId: string | null;
  readonly highlightedNodeIds: ReadonlySet<string>;
  readonly density: GraphDensity;
}

export function SceneLabels({
  nodes,
  selectedId,
  hoveredId,
  highlightedNodeIds,
  density,
}: SceneLabelsProps) {
  const representatives = new Map<string, SceneNode>();
  for (const node of nodes) {
    if (!representatives.has(node.lane)) representatives.set(node.lane, node);
  }
  const labelIds = new Set(
    density === "detail"
      ? nodes.slice(0, 28).map((node) => node.id)
      : [...representatives.values()].map((node) => node.id),
  );
  if (selectedId !== null) labelIds.add(selectedId);
  if (hoveredId !== null) labelIds.add(hoveredId);
  for (const id of highlightedNodeIds) labelIds.add(id);
  return (
    <>
      {nodes.filter((node) => labelIds.has(node.id)).map((node) => (
        <Html
          key={node.id}
          center
          position={[node.position[0], node.position[1] + 0.48, node.position[2]]}
          distanceFactor={12}
          zIndexRange={[30, 0]}
          style={{ pointerEvents: "none" }}
        >
          <span
            className={`scene-node-label${selectedId === node.id ? " is-selected" : ""}`}
            title={`${node.kind} · ${node.layer}`}
          >
            {node.label}
          </span>
        </Html>
      ))}
    </>
  );
}
