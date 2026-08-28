import { useState } from "react";
import { createRoot } from "react-dom/client";

import "../../src/styles/global.css";
import { SceneLens } from "../../src/lenses/scene/SceneLens";
import { CANONICAL_SCENE_CAMERA } from "../../src/scene/camera";
import type { CameraState } from "../../src/state/investigation";
import { createFixtureDataSource } from "../../src/testing/fixtures";

const fallback = new URLSearchParams(window.location.search).get("fallback") === "1";

export function Harness() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [camera, setCamera] = useState<CameraState>(CANONICAL_SCENE_CAMERA);
  return (
    <main className="workbench">
      <SceneLens
        dataSource={createFixtureDataSource()}
        runId="run-a"
        selectedId={selectedId}
        camera={camera}
      onCameraChange={setCamera}
      onSelect={setSelectedId}
      {...(fallback ? { webglAvailable: () => false } : {})}
      />
    </main>
  );
}

const root = document.getElementById("root");
if (root === null) throw new Error("scene fixture root is missing");
createRoot(root).render(<Harness />);
