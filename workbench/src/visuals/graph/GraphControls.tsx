import type { OntologyObjectContract } from "../../data/InvestigationDataSource";
import type { CameraState } from "../../state/investigation";
import { ontologyObjectLabel } from "../shared/objectLabel";
import type { GraphDensity, GraphLayoutMode } from "./model";

export type GraphDimension = "2d" | "3d";

interface GraphControlsProps {
  readonly dimension: GraphDimension;
  readonly layoutMode: GraphLayoutMode;
  readonly density: GraphDensity;
  readonly layers: ReadonlyArray<string>;
  readonly visibleLayers: ReadonlyArray<string>;
  readonly relationTypes: ReadonlyArray<string>;
  readonly visibleRelationTypes: ReadonlyArray<string>;
  readonly selectedId: string | null;
  readonly pathTargetId: string | null;
  readonly objects: ReadonlyArray<OntologyObjectContract>;
  readonly isolate: boolean;
  readonly neighborhoodDepth: number;
  readonly camera: CameraState;
  readonly onDimensionChange: (dimension: GraphDimension) => void;
  readonly onLayoutChange: (layout: GraphLayoutMode) => void;
  readonly onDensityChange: (density: GraphDensity) => void;
  readonly onLayersChange: (layers: ReadonlyArray<string>) => void;
  readonly onRelationTypesChange: (types: ReadonlyArray<string>) => void;
  readonly onPathTargetChange: (id: string | null) => void;
  readonly onIsolateChange: (isolate: boolean) => void;
  readonly onNeighborhoodDepthChange: (depth: number) => void;
  readonly onCameraChange: (camera: CameraState) => void;
  readonly onFocus: () => void;
  readonly onResetCamera: () => void;
}

function toggled(values: ReadonlyArray<string>, value: string, checked: boolean): ReadonlyArray<string> {
  return checked ? [...new Set([...values, value])].sort() : values.filter((item) => item !== value);
}

export function GraphControls(props: GraphControlsProps) {
  return (
    <section className="graph-controls" aria-label="Ontology graph controls">
      <div className="graph-controls__primary">
        <div role="group" aria-label="Graph dimension">
          {(["2d", "3d"] as const).map((dimension) => (
            <button key={dimension} type="button" aria-pressed={props.dimension === dimension} onClick={() => props.onDimensionChange(dimension)}>
              {dimension.toUpperCase()}
            </button>
          ))}
        </div>
        {props.dimension === "2d" ? (
          <div role="group" aria-label="Graph layout">
            {(["semantic", "force", "hierarchy"] as const).map((layout) => (
              <button key={layout} type="button" aria-pressed={props.layoutMode === layout} onClick={() => props.onLayoutChange(layout)}>
                {layout[0]?.toUpperCase()}{layout.slice(1)}
              </button>
            ))}
          </div>
        ) : (
          <div role="group" aria-label="Camera projection">
            {(["perspective", "orthographic"] as const).map((projection) => (
              <button key={projection} type="button" aria-pressed={props.camera.projection === projection} onClick={() => props.onCameraChange({ ...props.camera, projection })}>
                {projection[0]?.toUpperCase()}{projection.slice(1)}
              </button>
            ))}
          </div>
        )}
        <div role="group" aria-label="Semantic zoom">
          {(["overview", "detail"] as const).map((density) => (
            <button key={density} type="button" aria-pressed={props.density === density} onClick={() => props.onDensityChange(density)}>
              {density[0]?.toUpperCase()}{density.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="graph-controls__investigate">
        <label>
          <span>Trace from selection to</span>
          <select
            aria-label="Graph path target"
            value={props.pathTargetId ?? ""}
            disabled={props.selectedId === null}
            onChange={(event) => props.onPathTargetChange(event.currentTarget.value || null)}
          >
            <option value="">No target</option>
            {props.objects.filter((object) => object.ref.id !== props.selectedId).map((object) => (
              <option key={object.ref.id} value={object.ref.id}>{ontologyObjectLabel(object)}</option>
            ))}
          </select>
        </label>
        <label className="check-control">
          <input type="checkbox" checked={props.isolate} disabled={props.selectedId === null} onChange={(event) => props.onIsolateChange(event.currentTarget.checked)} />
          Isolate neighborhood
        </label>
        <label>
          <span>Neighborhood depth</span>
          <select aria-label="Neighborhood depth" value={props.neighborhoodDepth} disabled={props.selectedId === null} onChange={(event) => props.onNeighborhoodDepthChange(Number(event.currentTarget.value))}>
            <option value="1">1 hop</option>
            <option value="2">2 hops</option>
            <option value="3">3 hops</option>
          </select>
        </label>
        {props.dimension === "3d" ? (
          <div className="graph-controls__camera">
            <button type="button" disabled={props.selectedId === null} onClick={props.onFocus}>Focus selection</button>
            <button type="button" onClick={props.onResetCamera}>Reset camera</button>
          </div>
        ) : null}
      </div>

      <div className="graph-controls__filters">
        <details>
          <summary>Ontology layers · {props.visibleLayers.length}/{props.layers.length}</summary>
          <fieldset>
            <legend>Visible ontology layers</legend>
            {props.layers.map((layer) => (
              <label key={layer}>
                <input type="checkbox" checked={props.visibleLayers.includes(layer)} onChange={(event) => props.onLayersChange(toggled(props.visibleLayers, layer, event.currentTarget.checked))} />
                {layer.replaceAll("_", " ")}
              </label>
            ))}
          </fieldset>
        </details>
        <details>
          <summary>Relation types · {props.visibleRelationTypes.length}/{props.relationTypes.length}</summary>
          <fieldset>
            <legend>Visible relation types</legend>
            {props.relationTypes.map((type) => (
              <label key={type}>
                <input type="checkbox" checked={props.visibleRelationTypes.includes(type)} onChange={(event) => props.onRelationTypesChange(toggled(props.visibleRelationTypes, type, event.currentTarget.checked))} />
                {type.replaceAll("_", " ").toLowerCase()}
              </label>
            ))}
          </fieldset>
        </details>
      </div>
    </section>
  );
}
