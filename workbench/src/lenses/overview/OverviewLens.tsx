import { useEffect, useRef, useState } from "react";

import type {
  InvestigationDataSource,
  MeasurementContract,
  RunSummary,
  SystemContract,
} from "../../data/InvestigationDataSource";
import type { InvestigationLens } from "../../state/investigation";
import { TechnicalDetails } from "../../visuals/provenance/TechnicalDetails";
import { profileLabel } from "../../visuals/shared/runLabel";

interface OverviewLensProps {
  readonly run: RunSummary;
  readonly system: SystemContract;
  readonly dataSource: InvestigationDataSource;
  readonly auditComplete: boolean;
  readonly onOpen: (lens: InvestigationLens) => void;
  readonly onStartAudit: () => void;
}

const WORKFLOWS: ReadonlyArray<{
  readonly lens: InvestigationLens | null;
  readonly art: "ledger" | "exchange" | "workshop" | "civic";
  readonly eyebrow: string;
  readonly title: string;
  readonly description: string;
}> = [
  {
    lens: null,
    art: "ledger",
    eyebrow: "01 / Featured investigation",
    title: "Audit FX execution",
    description: "Reach a bounded conclusion across economy, runtime, markets, learning, evidence, ontology, and geography.",
  },
  {
    lens: "world",
    art: "exchange",
    eyebrow: "02 / Economy",
    title: "Map the economic world",
    description: "Inspect declared agents, institutions, mechanisms, constraints, data, and models.",
  },
  {
    lens: "learning",
    art: "workshop",
    eyebrow: "03 / Learning",
    title: "Trace the learning loop",
    description: "Test whether behavior, data, training, learned models, and deployment form a closure.",
  },
  {
    lens: "evidence",
    art: "civic",
    eyebrow: "04 / Evidence",
    title: "Audit a claim",
    description: "Traverse classifications, source locators, limitations, and supporting artifacts.",
  },
];

function resultValue(measurements: ReadonlyArray<MeasurementContract>, name: string): string {
  const value = measurements.find((measurement) => measurement.name === name)?.value;
  if (typeof value !== "number") return "Unavailable";
  if (Number.isInteger(value)) return value.toLocaleString("en-US");
  if (Math.abs(value) < 0.0001) return value.toExponential(2);
  return value.toLocaleString("en-US", { maximumFractionDigits: 5 });
}

export function OverviewLens({
  run,
  system,
  dataSource,
  auditComplete,
  onOpen,
  onStartAudit,
}: OverviewLensProps) {
  const workflowRow = useRef<HTMLDivElement>(null);
  const [measurements, setMeasurements] = useState<ReadonlyArray<MeasurementContract>>([]);
  useEffect(() => {
    let active = true;
    if (!auditComplete) return undefined;
    void dataSource.measurements({ runId: run.run_id, limit: 200 }).then((page) => {
      if (active) setMeasurements(page.items);
    }).catch(() => {
      if (active) setMeasurements([]);
    });
    return () => {
      active = false;
    };
  }, [auditComplete, dataSource, run.run_id]);
  const coverage = run.coverage ?? [];
  const projected = run.coverage_summary?.projected
    ?? coverage.filter((entry) => entry.status === "projected").length;
  const gaps = run.coverage_summary?.gap_total ?? coverage.length - projected;
  const coverageTotal = run.coverage_summary?.total ?? coverage.length;
  return (
    <article className="overview-lens lens-surface">
      <header className="overview-hero">
        <div>
          <p>Verified investigation</p>
          <h2>Read the economy from evidence to consequence.</h2>
          <p>
            Begin with a research question. Every view stays synchronized to this sealed projection
            and leaves unavailable evidence visibly unavailable.
          </p>
        </div>
        <span className="integrity-seal" data-status={run.integrity_level}>
          <span aria-hidden="true" />
          {run.integrity_level.replaceAll("_", " ")}
        </span>
      </header>

      <dl className="run-facts" aria-label="Selected run facts">
        <div>
          <dt>Model</dt>
          <dd>{profileLabel(run.profile_identity)}</dd>
        </div>
        <div>
          <dt>Coverage</dt>
          <dd>{coverageTotal ? `${projected} projected · ${gaps} explicit gaps` : "No ledger entries"}</dd>
        </div>
        <div>
          <dt>Delivery</dt>
          <dd>{system.mode.replaceAll("_", " ")}</dd>
        </div>
      </dl>

      <TechnicalDetails
        className="overview-technical-details"
        details={[
          { label: "Run identity", value: run.run_id },
          { label: "Source run", value: run.source_run_hash },
          { label: "Profile", value: run.profile_identity },
          { label: "Ontology schema", value: run.ontology_schema },
          { label: "Projection digest", value: run.projection_digest },
        ]}
      />

      {auditComplete ? (
        <section className="audit-conclusion" aria-labelledby="audit-conclusion-title">
          <header>
            <p>Bounded conclusion</p>
            <h3 id="audit-conclusion-title">
              Execution passed inside the synthetic runtime. Adaptive model closure remains unproven.
            </h3>
          </header>
          <dl aria-label="FX audit result">
            <div><dt>Rejected orders</dt><dd>{resultValue(measurements, "rejected_orders")}</dd></div>
            <div><dt>Total volume</dt><dd>{resultValue(measurements, "total_volume")}</dd></div>
            <div><dt>Mean price</dt><dd>{resultValue(measurements, "mean_price")}</dd></div>
            <div><dt>Max cash residual</dt><dd>{resultValue(measurements, "max_cash_residual")}</dd></div>
          </dl>
          <div className="audit-conclusion__boundary">
            <strong>What this establishes</strong>
            <p>
              The sealed FX run records clearing, trading, zero rejected orders, and negligible
              accounting drift within its declared synthetic boundary.
            </p>
            <strong>What it does not establish</strong>
            <p>
              No dataset-to-training-to-deployment closure, DDGE certificate, empirical
              calibration, or observed real-world geography is present in this projection.
            </p>
          </div>
        </section>
      ) : null}

      <section className="workflow-entry" aria-labelledby="workflow-entry-title">
        <header>
          <div>
            <p>Research paths</p>
            <h3 id="workflow-entry-title">What do you want to establish?</h3>
          </div>
          <div className="workflow-entry__arrows" aria-label="Scroll research paths">
            <button type="button" aria-label="Previous research paths" onClick={() => workflowRow.current?.scrollBy({ left: -420, behavior: "smooth" })}>←</button>
            <button type="button" aria-label="Next research paths" onClick={() => workflowRow.current?.scrollBy({ left: 420, behavior: "smooth" })}>→</button>
          </div>
        </header>
        <div className="workflow-entry__grid" ref={workflowRow}>
          {WORKFLOWS.map((workflow) => (
            <button
              type="button"
              key={workflow.title}
              aria-label={workflow.title}
              onClick={() => workflow.lens === null ? onStartAudit() : onOpen(workflow.lens)}
            >
              <span className="workflow-entry__art" data-art={workflow.art} aria-hidden="true">
                <i>EWM</i>
              </span>
              <span className="workflow-entry__coordinate">{workflow.eyebrow}</span>
              <strong>{workflow.title}</strong>
              <small>{workflow.description}</small>
              <i aria-hidden="true">Open research path →</i>
            </button>
          ))}
        </div>
      </section>
    </article>
  );
}
