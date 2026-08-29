import { useEffect, useRef, useState } from "react";

import { IntegrityDataError } from "../data/ApiDataSource";
import type {
  InvestigationDataSource,
  RunSummary,
  SystemContract,
  WorkbenchStatus,
} from "../data/InvestigationDataSource";
import { useInvestigation, type InvestigationLens } from "../state/investigation";
import { TechnicalDetails } from "../visuals/provenance/TechnicalDetails";
import { runLabel } from "../visuals/shared/runLabel";
import { EvidenceInspector } from "./EvidenceInspector";
import { GuidedInvestigation } from "./GuidedInvestigation";
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

interface NavigationItem {
  readonly lens: InvestigationLens;
  readonly description: string;
}

interface NavigationGroup {
  readonly label: string;
  readonly items: ReadonlyArray<NavigationItem>;
}

const STATUS_MESSAGES: Readonly<Record<Exclude<WorkbenchStatus, "ready">, string>> = {
  partial: "Projection coverage is partial.",
  unsupported: "This projection profile is not supported by the workbench.",
  integrity_error: "Projection integrity verification failed.",
};

const NAVIGATION_GROUPS: ReadonlyArray<NavigationGroup> = [
  {
    label: "Research",
    items: [
      { lens: "overview", description: "Run health and research paths" },
      { lens: "world", description: "Agents, institutions, and mechanisms" },
      { lens: "runtime", description: "States, actions, and settlement" },
      { lens: "market", description: "Prices, volumes, and rejection" },
      { lens: "learning", description: "Data, training, and deployment" },
      { lens: "evidence", description: "Claims, sources, and limitations" },
    ],
  },
  {
    label: "Validation",
    items: [
      { lens: "ddge", description: "Fixed points and certificates" },
      { lens: "compare", description: "Compatible run differences" },
    ],
  },
  {
    label: "Ontology",
    items: [
      { lens: "lineage", description: "Directed provenance paths" },
      { lens: "scene", description: "Synchronized 2D and 3D graph" },
      { lens: "globe", description: "Explicit economic geography" },
    ],
  },
];

const TEMPORAL_LENSES: ReadonlySet<InvestigationLens> = new Set([
  "runtime",
  "market",
  "scene",
  "globe",
]);

function lensLabel(lens: InvestigationLens): string {
  if (lens === "overview") return "Overview";
  if (lens === "world") return "Economy";
  if (lens === "runtime") return "Simulation";
  if (lens === "market") return "Markets";
  if (lens === "ddge") return "DDGE";
  if (lens === "scene") return "Graph";
  if (lens === "globe") return "Globe";
  return `${lens[0]?.toUpperCase()}${lens.slice(1)}`;
}

function activeGroup(lens: InvestigationLens): string {
  return NAVIGATION_GROUPS.find((group) => group.items.some((item) => item.lens === lens))
    ?.label ?? "Research";
}

function activeDescription(lens: InvestigationLens): string {
  return NAVIGATION_GROUPS.flatMap((group) => group.items).find((item) => item.lens === lens)
    ?.description ?? "Research module";
}

export function AppShell({ dataSource }: AppShellProps) {
  const { state, dispatch } = useInvestigation();
  const [load, setLoad] = useState<LoadState>({ status: "loading" });
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [explorerOpen, setExplorerOpen] = useState(true);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const navigationCloseRef = useRef<HTMLButtonElement>(null);
  const navigationToggleRef = useRef<HTMLButtonElement>(null);
  const navigationWasOpen = useRef(false);

  useEffect(() => {
    let active = true;
    void Promise.all([dataSource.system(), dataSource.runs()])
      .then(([system, runs]) => {
        if (active) setLoad({ status: "loaded", system, runs });
      })
      .catch((error: unknown) => {
        if (!active) return;
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

  useEffect(() => {
    if (navigationOpen) {
      navigationCloseRef.current?.focus();
    } else if (navigationWasOpen.current) {
      navigationToggleRef.current?.focus();
    }
    navigationWasOpen.current = navigationOpen;
  }, [navigationOpen]);

  useEffect(() => {
    if (!navigationOpen) return undefined;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setNavigationOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [navigationOpen]);

  const selectedRun =
    load.status === "loaded"
      ? load.runs.find((run) => run.run_id === state.runId) ?? null
      : null;
  const workbenchStatus = load.status === "loaded" ? load.system.status ?? "ready" : null;
  const showExplorer = state.lens !== "overview";
  const showInspector = showExplorer && state.objectId !== null;
  const explorerVisible = showExplorer && explorerOpen;
  const inspectorVisible = showInspector && inspectorOpen;
  const currentRunLabel = selectedRun === null
    ? "Selection pending"
    : runLabel(selectedRun, Math.max(0, load.status === "loaded"
      ? load.runs.findIndex((run) => run.run_id === selectedRun.run_id)
      : 0));

  return (
    <div className={`workbench${navigationOpen ? " workbench--navigation-open" : ""}`}>
      <a className="skip-link" href="#active-analysis" tabIndex={navigationOpen ? -1 : undefined}>
        Skip to active analysis
      </a>
      <aside id="platform-navigation" className="platform-sidebar" aria-label="EWM platform navigation">
        <header className="platform-brand">
          <button
            type="button"
            className="platform-brand__close"
            aria-label="Close navigation"
            ref={navigationCloseRef}
            onClick={() => setNavigationOpen(false)}
          >
            <span aria-hidden="true">×</span>
          </button>
          <span>Research Workbench</span>
          <strong aria-label="EWM">EWM</strong>
          <small>Economic World Model</small>
        </header>
        <nav className="platform-nav" aria-label="Primary research workflows">
          {NAVIGATION_GROUPS.map((group) => (
            <section key={group.label} aria-labelledby={`navigation-${group.label.toLowerCase()}`}>
              <h2 id={`navigation-${group.label.toLowerCase()}`}>{group.label}</h2>
              {group.items.map((item, index) => (
                <button
                  type="button"
                  key={item.lens}
                  aria-label={lensLabel(item.lens)}
                  aria-current={state.lens === item.lens ? "page" : undefined}
                  onClick={() => {
                    setNavigationOpen(false);
                    dispatch({ type: "set-lens", lens: item.lens });
                  }}
                >
                  <span aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
                  <span>
                    <strong>{lensLabel(item.lens)}</strong>
                    <small>{item.description}</small>
                  </span>
                </button>
              ))}
            </section>
          ))}
        </nav>
        <section className="run-dock" aria-label="Run context">
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
                ? load.runs.map((run, index) => (
                    <option value={run.run_id} key={run.run_id}>
                      {runLabel(run, index)}
                    </option>
                  ))
                : null}
            </select>
          </label>
          <p className="run-dock__status">
            <span aria-hidden="true" />
            {selectedRun?.integrity_level.replaceAll("_", " ") ?? "Awaiting verification"}
          </p>
          {selectedRun === null ? null : (
            <TechnicalDetails
              className="run-dock__details"
              details={[
                { label: "Run identity", value: selectedRun.run_id },
                { label: "Source run", value: selectedRun.source_run_hash },
                { label: "Profile", value: selectedRun.profile_identity },
                { label: "Schema", value: selectedRun.ontology_schema },
                { label: "Projection digest", value: selectedRun.projection_digest },
              ]}
            />
          )}
        </section>
      </aside>
      <button
        type="button"
        className="navigation-scrim"
        aria-label="Dismiss navigation"
        onClick={() => setNavigationOpen(false)}
      />

      <main
        className="workbench__main"
        aria-labelledby="workbench-title"
        inert={navigationOpen ? true : undefined}
      >
        <header className="masthead">
          <button
            type="button"
            className="navigation-toggle"
            aria-label={navigationOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={navigationOpen}
            aria-controls="platform-navigation"
            ref={navigationToggleRef}
            onClick={() => setNavigationOpen((open) => !open)}
          >
            <span aria-hidden="true" />
            <span aria-hidden="true" />
            <span aria-hidden="true" />
          </button>
          <div className="masthead__title">
            <p>Research Workbench</p>
            <h1 id="workbench-title">Economic World Model</h1>
          </div>
          <div className="masthead__context">
            <span>Active module</span>
            <strong>{lensLabel(state.lens)}</strong>
            <small>{activeDescription(state.lens)}</small>
          </div>
        </header>

        <section className="context-bar" aria-label="Workspace context and commands">
          <ol className="context-breadcrumb" aria-label="Breadcrumb">
            <li>Research Workbench</li>
            <li>{activeGroup(state.lens)}</li>
            <li aria-current="page">{lensLabel(state.lens)}</li>
          </ol>
          <div className="context-commands" aria-label="Context panels">
            {showExplorer ? (
              <button
                type="button"
                aria-expanded={explorerVisible}
                aria-controls="object-explorer-panel"
                onClick={() => setExplorerOpen((open) => !open)}
              >
                <span aria-hidden="true">⌕</span>
                Objects
              </button>
            ) : null}
            {showExplorer ? (
              <button
                type="button"
                disabled={!showInspector}
                aria-expanded={inspectorVisible}
                aria-controls="evidence-inspector-panel"
                onClick={() => setInspectorOpen((open) => !open)}
              >
                <span aria-hidden="true">◎</span>
                Evidence
              </button>
            ) : null}
            <span className="context-status">
              <span aria-hidden="true" />
              {selectedRun?.integrity_level.replaceAll("_", " ") ?? "not ready"}
            </span>
          </div>
        </section>

        <GuidedInvestigation />

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
            <div
              className={`workspace-grid${explorerVisible ? "" : " workspace-grid--no-explorer"}${inspectorVisible ? "" : " workspace-grid--no-inspector"}${showExplorer ? "" : " workspace-grid--analysis-only"}`}
            >
              {explorerVisible ? (
                <div id="object-explorer-panel" className="context-panel context-panel--explorer">
                  <ObjectExplorer dataSource={dataSource} />
                </div>
              ) : null}
              <div id="active-analysis" className="active-analysis" tabIndex={-1}>
                <LensRouter dataSource={dataSource} selectedRun={selectedRun} system={load.system} />
              </div>
              {inspectorVisible ? (
                <div id="evidence-inspector-panel" className="context-panel context-panel--inspector">
                  <EvidenceInspector dataSource={dataSource} />
                </div>
              ) : null}
            </div>
            {TEMPORAL_LENSES.has(state.lens) ? <Timeline /> : null}
            <footer className="provenance-strip">
              <span className="provenance-strip__signal" aria-hidden="true" />
              <span>Active projection</span>
              <strong>{currentRunLabel}</strong>
              <span>{selectedRun?.integrity_level.replaceAll("_", " ") ?? "integrity unknown"}</span>
            </footer>
          </>
        ) : null}
      </main>
    </div>
  );
}
