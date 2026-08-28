import { OrbitControls } from "@react-three/drei";
import { Canvas, useThree } from "@react-three/fiber";

import type { GeoFlow, TaggedGeoPlacement } from "../geometry";
import { AnchoredObjects } from "./AnchoredObjects";
import { EarthBoundaries } from "./EarthBoundaries";
import { FlowArcs } from "./FlowArcs";
import { UncertaintyRings } from "./UncertaintyRings";

interface EconomicGlobeProps {
  readonly placements: ReadonlyArray<TaggedGeoPlacement>;
  readonly flows: ReadonlyArray<GeoFlow>;
  readonly selectedId: string | null;
  readonly onSelect: (id: string) => void;
  readonly showFlows?: boolean;
  readonly showUncertainty?: boolean;
}

function GlobeControls() {
  const invalidate = useThree((state) => state.invalidate);
  return (
    <OrbitControls
      makeDefault
      enableDamping={false}
      autoRotate={false}
      minDistance={4.2}
      maxDistance={13}
      enablePan={false}
      onChange={() => invalidate()}
    />
  );
}

export function EconomicGlobe({
  placements,
  flows,
  selectedId,
  onSelect,
  showFlows = true,
  showUncertainty = true,
}: EconomicGlobeProps) {
  return (
    <div className="economic-globe" role="img" aria-label="3D economic globe with explicit anchors">
      <Canvas
        frameloop="demand"
        dpr={[1, 1.5]}
        camera={{ position: [0, 1.2, 7.4], near: 0.1, far: 80, fov: 42 }}
        gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}
      >
        <color attach="background" args={["#151813"]} />
        <ambientLight intensity={1.15} />
        <directionalLight position={[5, 7, 8]} intensity={2.1} />
        <mesh raycast={() => null}>
          <sphereGeometry args={[3, 64, 36]} />
          <meshStandardMaterial color="#293027" roughness={0.9} metalness={0} />
        </mesh>
        <EarthBoundaries />
        {showFlows ? <FlowArcs flows={flows} /> : null}
        {showUncertainty ? <UncertaintyRings placements={placements} /> : null}
        <AnchoredObjects placements={placements} selectedId={selectedId} onSelect={onSelect} />
        <GlobeControls />
      </Canvas>
    </div>
  );
}
