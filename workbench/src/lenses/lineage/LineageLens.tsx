import { useEffect, useMemo, useState } from "react";

import type {
  InvestigationDataSource,
  OntologyObjectContract,
  PathResultContract,
} from "../../data/InvestigationDataSource";
import { LineagePath } from "../../visuals/lineage/LineagePath";

interface LineageLensProps {
  readonly dataSource: InvestigationDataSource;
  readonly runId: string;
  readonly selectedId: string | null;
}

type ObjectLoad =
  | { readonly key: string; readonly status: "loading" | "failed" }
  | { readonly key: string; readonly status: "loaded"; readonly objects: ReadonlyArray<OntologyObjectContract> };

type PathLoad =
  | { readonly key: string; readonly status: "idle" | "failed" }
  | { readonly key: string; readonly status: "loaded"; readonly result: PathResultContract };

function label(object: OntologyObjectContract): string {
  const naturalKey = object.properties.natural_key;
  return typeof naturalKey === "string" ? naturalKey : object.ref.id;
}

export function LineageLens({ dataSource, runId, selectedId }: LineageLensProps) {
  const [objectsLoad, setObjectsLoad] = useState<ObjectLoad>({ key: "", status: "loading" });
  const [startId, setStartId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [pathLoad, setPathLoad] = useState<PathLoad>({ key: "", status: "idle" });

  useEffect(() => {
    let active = true;
    void dataSource
      .objects({ runId, limit: 200 })
      .then((page) => {
        if (!active) return;
        setObjectsLoad({ key: runId, status: "loaded", objects: page.items });
        const preferred = page.items.some((item) => item.ref.id === selectedId)
          ? (selectedId ?? "")
          : "";
        setStartId(preferred);
        setTargetId("");
      })
      .catch(() => {
        if (active) setObjectsLoad({ key: runId, status: "failed" });
      });
    return () => {
      active = false;
    };
  }, [dataSource, runId, selectedId]);

  const pathKey = `${runId}|${startId}|${targetId}`;
  useEffect(() => {
    let active = true;
    if (!startId || !targetId || startId === targetId) return;
    void dataSource
      .paths({
        runId,
        startId,
        targetId,
        direction: "outgoing",
        maxDepth: 8,
        limit: 32,
      })
      .then((result) => {
        if (active) setPathLoad({ key: pathKey, status: "loaded", result });
      })
      .catch(() => {
        if (active) setPathLoad({ key: pathKey, status: "failed" });
      });
    return () => {
      active = false;
    };
  }, [dataSource, pathKey, runId, startId, targetId]);

  const objects = useMemo(
    () => (objectsLoad.key === runId && objectsLoad.status === "loaded" ? objectsLoad.objects : []),
    [objectsLoad, runId],
  );

  return (
    <section className="analytical-lens lineage-lens">
      <header className="analytical-lens__heading">
        <div>
          <p>08 / LINEAGE</p>
          <h2>Lineage lens</h2>
        </div>
        <p>Directed relation paths retain ontology identities and source locators.</p>
      </header>
      {objectsLoad.key !== runId ? <p className="lens-loading">Reading lineage identities…</p> : null}
      {objectsLoad.key === runId && objectsLoad.status === "failed" ? (
        <p className="sparse-fallback" role="alert">Lineage identities are unavailable.</p>
      ) : null}
      {objectsLoad.key === runId && objectsLoad.status === "loaded" && objects.length < 2 ? (
        <div className="sparse-fallback">
          <strong>Lineage unavailable</strong>
          <p>At least two explicit ontology identities are required.</p>
        </div>
      ) : null}
      {objects.length >= 2 ? (
        <div className="lineage-controls">
          <label>
            <span>Start identity</span>
            <select aria-label="Lineage start" value={startId} onChange={(event) => setStartId(event.currentTarget.value)}>
              <option value="">Choose a starting object</option>
              {objects.map((object) => <option key={object.ref.id} value={object.ref.id}>{label(object)}</option>)}
            </select>
          </label>
          <span aria-hidden="true">→</span>
          <label>
            <span>Target identity</span>
            <select aria-label="Lineage target" value={targetId} onChange={(event) => setTargetId(event.currentTarget.value)}>
              <option value="">Choose a target object</option>
              {objects.filter((object) => object.ref.id !== startId).map((object) => (
                <option key={object.ref.id} value={object.ref.id}>{label(object)}</option>
              ))}
            </select>
          </label>
        </div>
      ) : null}
      {objects.length >= 2 && (!startId || !targetId) ? (
        <p className="lineage-prompt">
          {selectedId === null
            ? "Select a meaningful starting object, then choose the lineage target. No arbitrary path is drawn."
            : "The selected object is the start. Choose a target to run the bounded path query."}
        </p>
      ) : null}
      {startId && targetId && pathLoad.key !== pathKey ? <p className="lens-loading">Traversing bounded graph…</p> : null}
      {pathLoad.key === pathKey && pathLoad.status === "failed" ? (
        <p className="sparse-fallback" role="alert">The bounded path query failed.</p>
      ) : null}
      {pathLoad.key === pathKey && pathLoad.status === "loaded" ? <LineagePath result={pathLoad.result} /> : null}
    </section>
  );
}
