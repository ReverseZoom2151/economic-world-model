import type { RunSummary, SystemContract } from "../../data/InvestigationDataSource";
import type { InvestigationLens } from "../../state/investigation";
import { TechnicalDetails } from "../../visuals/provenance/TechnicalDetails";
import { profileLabel } from "../../visuals/shared/runLabel";

interface OverviewLensProps {
  readonly run: RunSummary;
  readonly system: SystemContract;
  readonly onOpen: (lens: InvestigationLens) => void;
}

const WORKFLOWS: ReadonlyArray<{
  readonly lens: InvestigationLens;
  readonly eyebrow: string;
  readonly title: string;
  readonly description: string;
}> = [
  {
    lens: "world",
    eyebrow: "01 · Economy",
    title: "Understand the world",
    description: "Inspect declared agents, institutions, markets, constraints, data, and models.",
  },
  {
    lens: "runtime",
    eyebrow: "02 · Simulation",
    title: "Replay an episode",
    description: "Follow observed states, actions, mechanisms, settlements, and generated data.",
  },
  {
    lens: "learning",
    eyebrow: "03 · Learning",
    title: "Trace the learning loop",
    description: "Test whether behavior, data, training, learned models, and deployment form a closure.",
  },
  {
    lens: "evidence",
    eyebrow: "04 · Evidence",
    title: "Audit a claim",
    description: "Traverse classifications, source locators, limitations, and supporting artifacts.",
  },
];

export function OverviewLens({ run, system, onOpen }: OverviewLensProps) {
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

      <section className="workflow-entry" aria-labelledby="workflow-entry-title">
        <header>
          <p>Research paths</p>
          <h3 id="workflow-entry-title">What do you want to establish?</h3>
        </header>
        <div className="workflow-entry__grid">
          {WORKFLOWS.map((workflow) => (
            <button
              type="button"
              key={workflow.lens}
              aria-label={workflow.title}
              onClick={() => onOpen(workflow.lens)}
            >
              <span>{workflow.eyebrow}</span>
              <strong>{workflow.title}</strong>
              <small>{workflow.description}</small>
              <i aria-hidden="true">Open →</i>
            </button>
          ))}
        </div>
      </section>
    </article>
  );
}
