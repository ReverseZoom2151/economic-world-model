import { useEffect, useState } from "react";

import { IntegrityDataError } from "../data/ApiDataSource";
import type {
  InvestigationDataSource,
  RunSummary,
  SystemContract,
  WorkbenchStatus,
} from "../data/InvestigationDataSource";
import {
  INVESTIGATION_LENSES,
  useInvestigation,
  type InvestigationLens,
} from "../state/investigation";
import { EvidenceInspector } from "./EvidenceInspector";
import { LensRouter } from "./LensRouter";
import { ObjectExplorer } from "./ObjectExplorer";
import { Timeline } from "./Timeline";

interface AppShellProps {
  readonly dataSource: InvestigationDataSource;
}

type LoadState =
  | { readonly status: "loading" }
  | { readonly status: "failed"; readonly message: string }
  | {
      readonly status: "loaded";
      readonly system: SystemContract;
      readonly runs: ReadonlyArray<RunSummary>;
    };

const STATUS_MESSAGES: Readonly<Record<Exclude<WorkbenchStatus, "ready">, string>> = {
  partial: "Projection coverage is partial.",
  unsupported: "This projection profile is not supported by the workbench.",
  integrity_error: "Projection integrity verification failed.",
};

function lensLabel(lens: InvestigationLens): string {
  if (lens === "ddge") return "DDGE";
  if (lens === "scene") return "3D Scene";
  return `${lens[0]?.toUpperCase()}${lens.slice(1)}`;
}

export function AppShell({ dataSource }: AppShellProps) {
  const { state, dispatch } = useInvestigation();
  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    void Promise.all([dataSource.system(), dataSource.runs()])
      .then(([system, runs]) => {
        if (!active) {
          return;
        }
        setLoad({ status: "loaded", system, runs });
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        setLoad({
          status: "failed",
          message:
            error instanceof IntegrityDataError
              ? STATUS_MESSAGES.integrity_error
              : "The local workbench service is unavailable.",
        });
      });
    return () => {
      active = false;
    };
  }, [dataSource]);

  useEffect(() => {
    if (load.status === "loaded" && state.runId === null && load.runs[0] !== undefined) {
      dispatch({ type: "select-run", runId: load.runs[0].run_id });
    }
  }, [dispatch, load, state.runId]);

  const selectedRun =
    load.status === "loaded"
      ? load.runs.find((run) => run.run_id === state.runId) ?? null
      : null;
  const workbenchStatus = load.status === "loaded" ? load.system.status ?? "ready" : null;

  return (
    <main className="workbench" aria-labelledby="workbench-title">
      <header className="masthead">
        <div className="masthead__mark" aria-hidden="true">
          EWM
        </div>
        <div className="masthead__title">
          <p>Local research instrument</p>
          <h1 id="workbench-title">Ontology Research Workbench</h1>
        </div>
        <label className="run-selector">
          <span>Approved run</span>
          <select
            aria-label="Approved run"
            disabled={load.status !== "loaded" || load.runs.length === 0}
            value={state.runId ?? ""}
            onChange={(event) =>
              dispatch({ type: "select-run", runId: event.currentTarget.value || null })
            }
          >
            {load.status === "loaded" && load.runs.length === 0 ? (
              <option value="">No runs</option>
            ) : null}
            {load.status === "loaded"
              ? load.runs.map((run) => (
                  <option value={run.run_id} key={run.run_id}>
                    {run.run_id}
                  </option>
                ))
              : null}
          </select>
        </label>
      </header>

      <nav className="lens-nav" aria-label="Analytical lenses">
        {INVESTIGATION_LENSES.map((lens, index) => (
          <button
            type="button"
            key={lens}
            aria-pressed={state.lens === lens}
            onClick={() => dispatch({ type: "set-lens", lens })}
          >
            <span aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
            {lensLabel(lens)}
          </button>
        ))}
      </nav>

      {load.status === "loading" ? (
        <section className="system-state" aria-live="polite">
          <span className="system-state__signal" aria-hidden="true" />
          <h2>Loading approved runs…</h2>
          <p>Verifying the local investigation boundary.</p>
        </section>
      ) : null}
      {load.status === "failed" ? (
        <section className="system-state system-state--error" role="alert">
          <h2>{load.message}</h2>
          <p>No unverified data were shown.</p>
        </section>
      ) : null}
      {load.status === "loaded" && load.runs.length === 0 ? (
        <section className="system-state">
          <h2>No approved runs are available.</h2>
          <p>Start the workbench with at least one verified run.</p>
        </section>
      ) : null}
      {workbenchStatus !== null && workbenchStatus !== "ready" ? (
        <section
          className={`status-banner status-banner--${workbenchStatus}`}
          role={workbenchStatus === "integrity_error" ? "alert" : "status"}
        >
          <strong>{STATUS_MESSAGES[workbenchStatus]}</strong>
          <span>Availability is explicit; absent records are not reconstructed.</span>
        </section>
      ) : null}

      {load.status === "loaded" && load.runs.length > 0 ? (
        <>
          <div className="workspace-grid">
            <ObjectExplorer dataSource={dataSource} />
            <LensRouter dataSource={dataSource} />
            <EvidenceInspector dataSource={dataSource} />
          </div>
          <Timeline />
          <footer className="provenance-strip">
            <span className="provenance-strip__signal" aria-hidden="true" />
            <span>Active projection</span>
            <strong>{selectedRun?.run_id ?? "selection pending"}</strong>
            <span>{selectedRun?.integrity_level ?? "integrity unknown"}</span>
            <code>{selectedRun?.projection_digest.slice(0, 12) ?? "—"}</code>
          </footer>
        </>
      ) : null}
    </main>
  );
}
