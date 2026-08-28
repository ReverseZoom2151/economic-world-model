import type { CameraState } from "../state/investigation";
import { CANONICAL_SCENE_CAMERA } from "./camera";

interface SceneControlsProps {
  readonly camera: CameraState;
  readonly layers: ReadonlyArray<string>;
  readonly visibleLayers: ReadonlyArray<string>;
  readonly selectedId: string | null;
  readonly onCameraChange: (camera: CameraState) => void;
  readonly onLayersChange: (layers: ReadonlyArray<string>) => void;
  readonly onFocus: () => void;
}

export function SceneControls({
  camera,
  layers,
  visibleLayers,
  selectedId,
  onCameraChange,
  onLayersChange,
  onFocus,
}: SceneControlsProps) {
  return (
    <section className="scene-controls" aria-label="3D scene controls">
      <div className="scene-controls__projection" role="group" aria-label="Camera projection">
        {(["perspective", "orthographic"] as const).map((projection) => (
          <button
            type="button"
            key={projection}
            aria-pressed={camera.projection === projection}
            onClick={() => onCameraChange({ ...camera, projection })}
          >
            {projection[0]?.toUpperCase()}{projection.slice(1)}
          </button>
        ))}
      </div>
      <fieldset>
        <legend>Visible ontology layers</legend>
        {layers.map((layer) => (
          <label key={layer}>
            <input
              type="checkbox"
              checked={visibleLayers.includes(layer)}
              onChange={(event) =>
                onLayersChange(
                  event.currentTarget.checked
                    ? [...new Set([...visibleLayers, layer])].sort()
                    : visibleLayers.filter((item) => item !== layer),
                )
              }
            />
            {layer.replaceAll("_", " ")}
          </label>
        ))}
      </fieldset>
      <div className="scene-controls__actions">
        <button type="button" disabled={selectedId === null} onClick={onFocus}>
          Focus selection
        </button>
        <button type="button" onClick={() => onCameraChange(CANONICAL_SCENE_CAMERA)}>
          Reset camera
        </button>
      </div>
    </section>
  );
}
