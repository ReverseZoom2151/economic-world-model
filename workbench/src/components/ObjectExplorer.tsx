import { useEffect, useState } from "react";

import type {
  InvestigationDataSource,
  OntologyObjectContract,
} from "../data/InvestigationDataSource";
import { useInvestigation } from "../state/investigation";

interface ObjectExplorerProps {
  readonly dataSource: InvestigationDataSource;
}

function objectLabel(object: OntologyObjectContract): string {
  const naturalKey = object.properties.natural_key;
  return typeof naturalKey === "string" ? naturalKey : object.ref.id;
}

export function ObjectExplorer({ dataSource }: ObjectExplorerProps) {
  const { state, dispatch } = useInvestigation();
  const requestKey = `${state.runId ?? ""}|${state.filters.kinds.join(",")}|${state.filters.layers.join(",")}`;
  const [result, setResult] = useState<{
    readonly key: string;
    readonly objects: ReadonlyArray<OntologyObjectContract>;
    readonly failed: boolean;
  }>({ key: "", objects: [], failed: false });

  useEffect(() => {
    let active = true;
    if (state.runId === null) {
      return;
    }
    void dataSource
      .objects({
        runId: state.runId,
        kinds: state.filters.kinds,
        layers: state.filters.layers,
        limit: 50,
      })
      .then((page) => {
        if (active) {
          setResult({ key: requestKey, objects: page.items, failed: false });
        }
      })
      .catch(() => {
        if (active) {
          setResult({ key: requestKey, objects: [], failed: true });
        }
      });
    return () => {
      active = false;
    };
  }, [
    dataSource,
    requestKey,
    state.filters.kinds,
    state.filters.layers,
    state.runId,
  ]);

  const loading = state.runId !== null && result.key !== requestKey;
  const failed = result.key === requestKey && result.failed;
  const objects = result.key === requestKey ? result.objects : [];

  const visible = objects.filter((object) =>
    objectLabel(object).toLowerCase().includes(state.filters.query.toLowerCase()),
  );

  return (
    <section className="workspace-panel explorer" aria-label="Object explorer">
      <header className="panel-heading">
        <span>01</span>
        <h2>Objects</h2>
        <small>{visible.length.toString().padStart(2, "0")}</small>
      </header>
      <label className="field-label" htmlFor="object-search">
        Search this projection
      </label>
      <input
        id="object-search"
        type="search"
        placeholder="Identity or natural key"
        value={state.filters.query}
        onChange={(event) =>
          dispatch({
            type: "set-filters",
            filters: { ...state.filters, query: event.currentTarget.value },
          })
        }
      />
      {loading ? <p className="panel-note">Reading projection…</p> : null}
      {failed ? <p className="panel-note panel-note--error">Objects unavailable.</p> : null}
      {!loading && !failed && visible.length === 0 ? (
        <p className="panel-note">No objects match this bounded view.</p>
      ) : null}
      <ul className="object-list">
        {visible.map((object) => (
          <li key={object.ref.id}>
            <button
              type="button"
              aria-pressed={state.objectId === object.ref.id}
              onClick={() =>
                dispatch({
                  type: "select-object",
                  objectId: object.ref.id,
                })
              }
            >
              <span>{object.ref.kind.replaceAll("_", " ")}</span>
              <strong>{objectLabel(object)}</strong>
              <small>{object.layer.replaceAll("_", " ")}</small>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
