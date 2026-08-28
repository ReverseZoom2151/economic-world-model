import { OrbitControls } from "@react-three/drei";
import { Canvas, useThree } from "@react-three/fiber";
import { useEffect, useState } from "react";

import type { CameraState } from "../state/investigation";
import type { GraphDensity } from "../visuals/graph/model";
import { InstancedNodes } from "./InstancedNodes";
import type { SceneLayout } from "./layout";
import { RelationLines } from "./RelationLines";
import { SceneLabels } from "./SceneLabels";

interface OntologySceneProps {
  readonly layout: SceneLayout;
  readonly cameraState: CameraState;
  readonly selectedId: string | null;
  readonly highlightedNodeIds: ReadonlySet<string>;
  readonly highlightedRelationIds: ReadonlySet<string>;
  readonly density: GraphDensity;
  readonly onCameraChange: (camera: CameraState) => void;
  readonly onSelect: (id: string) => void;
}

interface CameraRigProps {
  readonly state: CameraState;
  readonly onChange: (camera: CameraState) => void;
}

function CameraRig({ state, onChange }: CameraRigProps) {
  const camera = useThree((current) => current.camera);
  const invalidate = useThree((current) => current.invalidate);
  useEffect(() => {
    camera.position.set(...state.position);
    camera.lookAt(...state.target);
    camera.updateProjectionMatrix();
    invalidate();
  }, [camera, invalidate, state.position, state.target]);
  return (
    <OrbitControls
      makeDefault
      enableDamping={false}
      autoRotate={false}
      target={state.target}
      minDistance={2}
      maxDistance={80}
      onChange={() => invalidate()}
      onEnd={() => {
        const [x, y, z] = camera.position.toArray();
        onChange({ ...state, position: [x, y, z] });
      }}
    />
  );
}

export function OntologyScene({
  layout,
  cameraState,
  selectedId,
  highlightedNodeIds,
  highlightedRelationIds,
  density,
  onCameraChange,
  onSelect,
}: OntologySceneProps) {
  const orthographic = cameraState.projection === "orthographic";
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  return (
    <div className="ontology-scene" role="img" aria-label="3D ontology scene">
      <Canvas
        key={cameraState.projection}
        frameloop="demand"
        dpr={[1, 1.5]}
        orthographic={orthographic}
        camera={{
          position: [...cameraState.position],
          near: 0.1,
          far: 500,
          ...(orthographic ? { zoom: 42 } : { fov: 48 }),
        }}
        gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}
      >
        <color attach="background" args={["#171a16"]} />
        <ambientLight intensity={1.8} />
        <directionalLight position={[8, 12, 10]} intensity={2.1} />
        <gridHelper args={[42, 42, "#454b40", "#282d26"]} raycast={() => null} />
        <RelationLines
          relations={layout.relations}
          highlightedRelationIds={highlightedRelationIds}
        />
        <InstancedNodes
          nodes={layout.nodes}
          selectedId={selectedId}
          highlightedNodeIds={highlightedNodeIds}
          onSelect={onSelect}
          onHover={setHoveredId}
        />
        <SceneLabels
          nodes={layout.nodes}
          selectedId={selectedId}
          hoveredId={hoveredId}
          highlightedNodeIds={highlightedNodeIds}
          density={density}
        />
        <CameraRig state={cameraState} onChange={onCameraChange} />
      </Canvas>
    </div>
  );
}
