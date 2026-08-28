import { useEffect, useMemo, useState } from "react";

import type {
  ComparisonResultContract,
  InvestigationDataSource,
  RunSummary,
} from "../../data/InvestigationDataSource";
import { ComparisonPreflight } from "../../visuals/compare/ComparisonPreflight";

interface CompareLensProps {
  readonly dataSource: InvestigationDataSource;
  readonly activeRunId: string;
}

type RunLoad =
  | { readonly status: "loading" }
  | { readonly status: "failed" }
  | { readonly status: "loaded"; readonly runs: ReadonlyArray<RunSummary> };

type ComparisonLoad =
  | { readonly key: string; readonly status: "idle" | "failed" }
  | { readonly key: string; readonly status: "loaded"; readonly result: ComparisonResultContract };

export function CompareLens({ dataSource, activeRunId }: CompareLensProps) {
  const [runLoad, setRunLoad] = useState<RunLoad>({ status: "loading" });
  const [rightRunId, setRightRunId] = useState("");
  const [comparison, setComparison] = useState<ComparisonLoad>({ key: "", status: "idle" });

  useEffect(() => {
    let active = true;
    void dataSource
      .runs()
      .then((runs) => {
        if (active) {
          setRunLoad({ status: "loaded", runs });
          setRightRunId((current) =>
            runs.some((run) => run.run_id === current && current !== activeRunId)
              ? current
              : (runs.find((run) => run.run_id !== activeRunId)?.run_id ?? ""),
          );
        }
      })
      .catch(() => {
        if (active) {
          setRunLoad({ status: "failed" });
        }
      });
    return () => {
      active = false;
    };
  }, [activeRunId, dataSource]);

  const requestKey = `${activeRunId}|${rightRunId}`;
  useEffect(() => {
    let active = true;
    if (!rightRunId || rightRunId === activeRunId) {
      return;
    }
    void dataSource
      .compare({ left_run_id: activeRunId, right_run_id: rightRunId })
      .then((result) => {
        if (active) {
          setComparison({ key: requestKey, status: "loaded", result });
        }
      })
      .catch(() => {
        if (active) {
          setComparison({ key: requestKey, status: "failed" });
        }
      });
    return () => {
      active = false;
    };
  }, [activeRunId, dataSource, requestKey, rightRunId]);

  const otherRuns = useMemo(
    () =>
      runLoad.status === "loaded"
        ? runLoad.runs.filter((run) => run.run_id !== activeRunId)
        : [],
    [activeRunId, runLoad],
  );

  return (
    <section className="analytical-lens comparison-lens">
      <header className="analytical-lens__heading">
        <div>
          <p>06 / COMPARISON</p>
          <h2>Comparison lens</h2>
        </div>
        <p>Only explicit semantic keys pass the compatibility gate.</p>
      </header>
      {runLoad.status === "loading" ? <p className="lens-loading">Reading approved runs…</p> : null}
      {runLoad.status === "failed" ? (
        <p className="sparse-fallback" role="alert">Approved-run identities are unavailable.</p>
      ) : null}
      {runLoad.status === "loaded" && otherRuns.length === 0 ? (
        <div className="sparse-fallback">
          <strong>Comparison unavailable</strong>
          <p>At least two approved runs are required. No counterfactual run was inferred.</p>
        </div>
      ) : null}
      {otherRuns.length > 0 ? (
        <div className="comparison-selector">
          <div>
            <span>Left / active</span>
            <strong>{activeRunId}</strong>
          </div>
          <span aria-hidden="true">↔</span>
          <label>
            <span>Right / comparator</span>
            <select
              aria-label="Comparator run"
              value={rightRunId}
              onChange={(event) => setRightRunId(event.currentTarget.value)}
            >
              {otherRuns.map((run) => (
                <option key={run.run_id} value={run.run_id}>{run.run_id}</option>
              ))}
            </select>
          </label>
        </div>
      ) : null}
      {rightRunId && comparison.key !== requestKey ? (
        <p className="lens-loading">Running compatibility preflight…</p>
      ) : null}
      {comparison.key === requestKey && comparison.status === "failed" ? (
        <p className="sparse-fallback" role="alert">Comparison preflight failed closed.</p>
      ) : null}
      {comparison.key === requestKey && comparison.status === "loaded" ? (
        <ComparisonPreflight comparison={comparison.result} />
      ) : null}
    </section>
  );
}
