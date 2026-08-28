import type { CameraState } from "../state/investigation";

export const CANONICAL_SCENE_CAMERA: CameraState = Object.freeze<CameraState>({
  projection: "perspective",
  position: [12, 8, 16] as const,
  target: [0, 0, 0] as const,
});
