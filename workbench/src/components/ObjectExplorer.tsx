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
    readonly nextCursor: string | null;
    readonly failed: boolean;
  }>({ key: "", objects: [], nextCursor: null, failed: false });
  const [loadingMore, setLoadingMore] = useState(false);

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
          setResult({
            key: requestKey,
            objects: page.items,
            nextCursor: page.next_cursor,
            failed: false,
          });
        }
      })
      .catch(() => {
        if (active) {
          setResult({ key: requestKey, objects: [], nextCursor: null, failed: true });
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
  const nextCursor = result.key === requestKey ? result.nextCursor : null;

  const visible = objects.filter((object) =>
    objectLabel(object).toLowerCase().includes(state.filters.query.toLowerCase()),
  );
  const groups = [...new Set(visible.map((object) => object.layer))]
    .sort()
    .map((layer) => ({
      layer,
      objects: visible.filter((object) => object.layer === layer),
    }));

  const loadMore = async () => {
    if (state.runId === null || nextCursor === null || loadingMore) return;
    setLoadingMore(true);
    try {
      const page = await dataSource.objects({
        runId: state.runId,
        kinds: state.filters.kinds,
        layers: state.filters.layers,
        limit: 50,
        cursor: nextCursor,
      });
      setResult((current) =>
        current.key === requestKey
          ? {
              ...current,
              objects: [...current.objects, ...page.items],
              nextCursor: page.next_cursor,
            }
          : current,
      );
    } catch {
      setResult((current) =>
        current.key === requestKey ? { ...current, failed: true } : current,
      );
    } finally {
      setLoadingMore(false);
    }
  };

  return (
    <section className="workspace-panel explorer" aria-label="Object explorer">
      <header className="panel-heading">
        <span>01</span>
        <h2>Objects</h2>
        <small>{visible.length} loaded</small>
      </header>
      <label className="field-label" htmlFor="object-search">
        Filter loaded objects
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
      {nextCursor !== null ? (
        <p className="explorer-boundary" role="status">
          This is a bounded page, not the complete projection.
        </p>
      ) : null}
      <div className="object-groups">
        {groups.map((group) => (
          <details key={group.layer} open>
            <summary>
              <span>{group.layer.replaceAll("_", " ")}</span>
              <small>{group.objects.length}</small>
            </summary>
            <ul className="object-list">
              {group.objects.map((object) => (
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
                    <small title={object.ref.id}>{object.ref.id}</small>
                  </button>
                </li>
              ))}
            </ul>
          </details>
        ))}
      </div>
      {nextCursor !== null ? (
        <button type="button" className="explorer-more" disabled={loadingMore} onClick={loadMore}>
          {loadingMore ? "Loading next page…" : "Load next 50 objects"}
        </button>
      ) : null}
    </section>
  );
}
