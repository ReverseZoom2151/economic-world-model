import { lazy, Suspense, useEffect, useMemo, useState } from "react";

import type {
  InvestigationDataSource,
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";
import type { CameraState } from "../../state/investigation";
import { supportsWebGL } from "../../scene/capabilities";
import { layoutOntologyScene, type SceneLayout } from "../../scene/layout";
import { SceneControls } from "../../scene/SceneControls";
import { SceneErrorBoundary } from "../../scene/SceneErrorBoundary";
import { WebGLFallback } from "../../scene/WebGLFallback";

const LazyOntologyScene = lazy(() =>
  import("../../scene/OntologyScene").then((module) => ({ default: module.OntologyScene })),
);

interface SceneLensProps {
  readonly dataSource: InvestigationDataSource;
  readonly runId: string;
  readonly selectedId: string | null;
  readonly camera: CameraState;
  readonly onCameraChange: (camera: CameraState) => void;
  readonly onSelect: (id: string) => void;
  readonly webglAvailable?: () => boolean;
}

interface SceneRecords {
  readonly key: string;
  readonly failed: boolean;
  readonly objects: ReadonlyArray<OntologyObjectContract>;
  readonly relations: ReadonlyArray<RelationContract>;
}

function visibleLayout(layout: SceneLayout, layers: ReadonlyArray<string>): SceneLayout {
  const nodes = layout.nodes.filter((node) => layers.includes(node.layer));
  const ids = new Set(nodes.map((node) => node.id));
  return {
    ...layout,
    nodes,
    relations: layout.relations.filter(
      (relation) => ids.has(relation.sourceId) && ids.has(relation.targetId),
    ),
  };
}

export function SceneLens({
  dataSource,
  runId,
  selectedId,
  camera,
  onCameraChange,
  onSelect,
  webglAvailable = supportsWebGL,
}: SceneLensProps) {
  const [records, setRecords] = useState<SceneRecords>({
    key: "",
    failed: false,
    objects: [],
    relations: [],
  });
  const [visibleLayers, setVisibleLayers] = useState<ReadonlyArray<string>>([]);
  useEffect(() => {
    let active = true;
    void Promise.all([
      dataSource.objects({ runId, limit: 200 }),
      dataSource.relations({ runId, limit: 200 }),
    ])
      .then(([objects, relations]) => {
        if (!active) return;
        setRecords({
          key: runId,
          failed: false,
          objects: objects.items,
          relations: relations.items,
        });
        setVisibleLayers([...new Set(objects.items.map((object) => object.layer))].sort());
      })
      .catch(() => {
        if (active) {
          setRecords({ key: runId, failed: true, objects: [], relations: [] });
        }
      });
    return () => {
      active = false;
    };
  }, [dataSource, runId]);

  const fullLayout = useMemo(
    () => layoutOntologyScene(records.objects, records.relations),
    [records.objects, records.relations],
  );
  const layout = useMemo(
    () => visibleLayout(fullLayout, visibleLayers),
    [fullLayout, visibleLayers],
  );
  const layers = useMemo(
    () => [...new Set(records.objects.map((object) => object.layer))].sort(),
    [records.objects],
  );
  const available = useMemo(() => webglAvailable(), [webglAvailable]);
  const focusSelection = () => {
    const selected = fullLayout.nodes.find((node) => node.id === selectedId);
    if (selected === undefined) return;
    const [x, y, z] = selected.position;
    onCameraChange({
      projection: camera.projection,
      position: [x + 7, y + 5, z + 9],
      target: selected.position,
    });
  };

  return (
    <section className="analytical-lens scene-lens">
      <header className="analytical-lens__heading">
        <div>
          <p>09 / 3D SCENE</p>
          <h2>Deterministic ontology scene</h2>
        </div>
        <p>X is semantic lane. Y is ontology layer. Z is declared time, version, or reference plane.</p>
      </header>
      {records.key !== runId ? <p className="lens-loading">Building bounded scene projection…</p> : null}
      {records.key === runId && records.failed ? (
        <p className="sparse-fallback" role="alert">The scene projection is unavailable.</p>
      ) : null}
      {records.key === runId && !records.failed ? (
        <>
          <SceneControls
            camera={camera}
            layers={layers}
            visibleLayers={visibleLayers}
            selectedId={selectedId}
            onCameraChange={onCameraChange}
            onLayersChange={setVisibleLayers}
            onFocus={focusSelection}
          />
          {fullLayout.omittedNodes || fullLayout.omittedRelations ? (
            <p className="scene-budget" role="status">
              Progressive boundary: {fullLayout.omittedNodes} nodes and {fullLayout.omittedRelations} relations withheld.
            </p>
          ) : null}
          {available ? (
            <SceneErrorBoundary
              key={`${runId}:${camera.projection}`}
              fallback={<WebGLFallback nodes={layout.nodes} selectedId={selectedId} onSelect={onSelect} />}
            >
              <Suspense fallback={<p className="lens-loading">Loading local 3D renderer…</p>}>
                <LazyOntologyScene
                  layout={layout}
                  cameraState={camera}
                  selectedId={selectedId}
                  onCameraChange={onCameraChange}
                  onSelect={onSelect}
                />
              </Suspense>
            </SceneErrorBoundary>
          ) : (
            <WebGLFallback nodes={layout.nodes} selectedId={selectedId} onSelect={onSelect} />
          )}
          <section className="scene-legend" aria-label="3D coordinate legend">
            <div><strong>X</strong><span>semantic lane</span></div>
            <div><strong>Y</strong><span>ontology layer</span></div>
            <div><strong>Z</strong><span>event sequence, version index, or 0 reference plane</span></div>
            <div><strong>{layout.nodes.length}</strong><span>visible instanced nodes</span></div>
            <div><strong>{layout.relations.length}</strong><span>visible batched relations</span></div>
          </section>
        </>
      ) : null}
    </section>
  );
}
