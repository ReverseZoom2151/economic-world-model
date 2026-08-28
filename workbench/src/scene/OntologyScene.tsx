import { OrbitControls } from "@react-three/drei";
import { Canvas, useThree } from "@react-three/fiber";
import { useEffect } from "react";

import type { CameraState } from "../state/investigation";
import { InstancedNodes } from "./InstancedNodes";
import type { SceneLayout } from "./layout";
import { RelationLines } from "./RelationLines";

interface OntologySceneProps {
  readonly layout: SceneLayout;
  readonly cameraState: CameraState;
  readonly selectedId: string | null;
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
  onCameraChange,
  onSelect,
}: OntologySceneProps) {
  const orthographic = cameraState.projection === "orthographic";
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
        <color attach="background" args={["#f3f3eb"]} />
        <ambientLight intensity={1.5} />
        <directionalLight position={[8, 12, 10]} intensity={1.8} />
        <gridHelper args={[42, 42, "#b9bbb1", "#d8d9d1"]} raycast={() => null} />
        <RelationLines relations={layout.relations} />
        <InstancedNodes nodes={layout.nodes} selectedId={selectedId} onSelect={onSelect} />
        <CameraRig state={cameraState} onChange={onCameraChange} />
      </Canvas>
    </div>
  );
}
