import { lazy, Suspense, useEffect, useMemo, useState } from "react";

import type {
  InvestigationDataSource,
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";
import type { CameraState } from "../../state/investigation";
import { supportsWebGL } from "../../scene/capabilities";
import { CANONICAL_SCENE_CAMERA } from "../../scene/camera";
import { layoutOntologyScene } from "../../scene/layout";
import { SceneErrorBoundary } from "../../scene/SceneErrorBoundary";
import { WebGLFallback } from "../../scene/WebGLFallback";
import { GraphControls, type GraphDimension } from "../../visuals/graph/GraphControls";
import {
  deriveGraphView,
  graphClusters,
  type GraphDensity,
  type GraphLayoutMode,
} from "../../visuals/graph/model";
import { OntologyGraph2D } from "../../visuals/graph/OntologyGraph2D";

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

interface GraphRecords {
  readonly key: string;
  readonly failed: boolean;
  readonly objects: ReadonlyArray<OntologyObjectContract>;
  readonly relations: ReadonlyArray<RelationContract>;
  readonly objectCursor: string | null;
  readonly relationCursor: string | null;
}

const EMPTY_RECORDS: GraphRecords = {
  key: "",
  failed: false,
  objects: [],
  relations: [],
  objectCursor: null,
  relationCursor: null,
};

export function SceneLens({
  dataSource,
  runId,
  selectedId,
  camera,
  onCameraChange,
  onSelect,
  webglAvailable = supportsWebGL,
}: SceneLensProps) {
  const [records, setRecords] = useState<GraphRecords>(EMPTY_RECORDS);
  const [dimension, setDimension] = useState<GraphDimension>("2d");
  const [layoutMode, setLayoutMode] = useState<GraphLayoutMode>("force");
  const [density, setDensity] = useState<GraphDensity>("overview");
  const [visibleLayers, setVisibleLayers] = useState<ReadonlyArray<string>>([]);
  const [visibleRelationTypes, setVisibleRelationTypes] = useState<ReadonlyArray<string>>([]);
  const [isolate, setIsolate] = useState(false);
  const [neighborhoodDepth, setNeighborhoodDepth] = useState(1);
  const [pathTargetId, setPathTargetId] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

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
          objectCursor: objects.next_cursor,
          relationCursor: relations.next_cursor,
        });
        setVisibleLayers([...new Set(objects.items.map((object) => object.layer))].sort());
        setVisibleRelationTypes(
          [...new Set(relations.items.map((relation) => relation.relation_type))].sort(),
        );
      })
      .catch(() => {
        if (active) setRecords({ ...EMPTY_RECORDS, key: runId, failed: true });
      });
    return () => {
      active = false;
    };
  }, [dataSource, runId]);

  const layers = useMemo(
    () => [...new Set(records.objects.map((object) => object.layer))].sort(),
    [records.objects],
  );
  const relationTypes = useMemo(
    () => [...new Set(records.relations.map((relation) => relation.relation_type))].sort(),
    [records.relations],
  );
  const view = useMemo(
    () =>
      deriveGraphView(records.objects, records.relations, {
        layers: visibleLayers,
        relationTypes: visibleRelationTypes,
        selectedId,
        isolate,
        neighborhoodDepth,
        pathTargetId,
        density,
      }),
    [
      density,
      isolate,
      neighborhoodDepth,
      pathTargetId,
      records.objects,
      records.relations,
      selectedId,
      visibleLayers,
      visibleRelationTypes,
    ],
  );
  const sceneLayout = useMemo(
    () => layoutOntologyScene(view.objects, view.relations),
    [view.objects, view.relations],
  );
  const clusters = useMemo(() => graphClusters(view.objects), [view.objects]);
  const available = useMemo(() => webglAvailable(), [webglAvailable]);
  const hasMore = records.objectCursor !== null || records.relationCursor !== null;

  const loadMore = async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const [objects, relations] = await Promise.all([
        records.objectCursor === null
          ? Promise.resolve(null)
          : dataSource.objects({ runId, limit: 200, cursor: records.objectCursor }),
        records.relationCursor === null
          ? Promise.resolve(null)
          : dataSource.relations({ runId, limit: 200, cursor: records.relationCursor }),
      ]);
      setRecords((current) => ({
        ...current,
        objects: objects === null ? current.objects : [...current.objects, ...objects.items],
        relations: relations === null ? current.relations : [...current.relations, ...relations.items],
        objectCursor: objects?.next_cursor ?? null,
        relationCursor: relations?.next_cursor ?? null,
      }));
      if (objects !== null) {
        setVisibleLayers((current) => [
          ...new Set([...current, ...objects.items.map((object) => object.layer)]),
        ].sort());
      }
      if (relations !== null) {
        setVisibleRelationTypes((current) => [
          ...new Set([...current, ...relations.items.map((relation) => relation.relation_type)]),
        ].sort());
      }
    } catch {
      setRecords((current) => ({ ...current, failed: true }));
    } finally {
      setLoadingMore(false);
    }
  };

  const focusSelection = () => {
    const selected = sceneLayout.nodes.find((node) => node.id === selectedId);
    if (selected === undefined) return;
    const [x, y, z] = selected.position;
    onCameraChange({
      projection: camera.projection,
      position: [x + 7, y + 5, z + 9],
      target: selected.position,
    });
  };

  return (
    <section className="analytical-lens graph-lens scene-lens">
      <header className="analytical-lens__heading graph-lens__heading">
        <div>
          <p>Advanced / ontology graph</p>
          <h2>Ontology graph</h2>
        </div>
        <p>
          Explore typed economic relations in synchronized 2D and 3D. Every node remains linked to
          the shared evidence inspector and sealed projection.
        </p>
      </header>
      {records.key !== runId ? <p className="lens-loading">Loading the bounded ontology graph…</p> : null}
      {records.key === runId && records.failed ? (
        <p className="sparse-fallback" role="alert">The graph projection is unavailable.</p>
      ) : null}
      {records.key === runId && !records.failed ? (
        <>
          <GraphControls
            dimension={dimension}
            layoutMode={layoutMode}
            density={density}
            layers={layers}
            visibleLayers={visibleLayers}
            relationTypes={relationTypes}
            visibleRelationTypes={visibleRelationTypes}
            selectedId={selectedId}
            pathTargetId={pathTargetId}
            objects={records.objects}
            isolate={isolate}
            neighborhoodDepth={neighborhoodDepth}
            camera={camera}
            onDimensionChange={setDimension}
            onLayoutChange={setLayoutMode}
            onDensityChange={setDensity}
            onLayersChange={setVisibleLayers}
            onRelationTypesChange={setVisibleRelationTypes}
            onPathTargetChange={setPathTargetId}
            onIsolateChange={setIsolate}
            onNeighborhoodDepthChange={setNeighborhoodDepth}
            onCameraChange={onCameraChange}
            onFocus={focusSelection}
            onResetCamera={() => onCameraChange(CANONICAL_SCENE_CAMERA)}
          />
          <section className="graph-clusters" aria-label="Visible semantic clusters">
            {clusters.map((cluster) => (
              <article key={cluster.lane}>
                <span>{cluster.lane}</span>
                <strong>{cluster.count}</strong>
                <small>{cluster.kinds.join(" · ")}</small>
              </article>
            ))}
          </section>
          {view.omittedObjects > 0 ? (
            <p className="scene-budget" role="status">
              Semantic zoom withheld {view.omittedObjects} lower-priority nodes. Switch to Detail
              or isolate a selected neighborhood.
            </p>
          ) : null}
          {selectedId !== null && pathTargetId !== null && view.pathRelationIds.size === 0 ? (
            <p className="bounded-notice">No path connects the selected object to that target through the visible typed relations.</p>
          ) : null}
          {dimension === "2d" ? (
            <OntologyGraph2D
              view={view}
              layoutMode={layoutMode}
              density={density}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          ) : available ? (
            <SceneErrorBoundary
              key={`${runId}:${camera.projection}`}
              fallback={<WebGLFallback nodes={sceneLayout.nodes} selectedId={selectedId} onSelect={onSelect} />}
            >
              <Suspense fallback={<p className="lens-loading">Loading the local 3D graph renderer…</p>}>
                <LazyOntologyScene
                  layout={sceneLayout}
                  cameraState={camera}
                  selectedId={selectedId}
                  highlightedNodeIds={view.pathNodeIds}
                  highlightedRelationIds={view.pathRelationIds}
                  density={density}
                  onCameraChange={onCameraChange}
                  onSelect={onSelect}
                />
              </Suspense>
            </SceneErrorBoundary>
          ) : (
            <WebGLFallback nodes={sceneLayout.nodes} selectedId={selectedId} onSelect={onSelect} />
          )}
          <section className="graph-ledger" aria-label="Graph projection boundary">
            <div><strong>{records.objects.length}</strong><span>loaded objects</span></div>
            <div><strong>{records.relations.length}</strong><span>loaded relations</span></div>
            <div><strong>{view.objects.length}</strong><span>visible nodes</span></div>
            <div><strong>{view.relations.length}</strong><span>visible edges</span></div>
          </section>
          {hasMore ? (
            <button type="button" className="graph-load-more" disabled={loadingMore} onClick={loadMore}>
              {loadingMore ? "Loading the next verified page…" : "Load the next graph page"}
            </button>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
