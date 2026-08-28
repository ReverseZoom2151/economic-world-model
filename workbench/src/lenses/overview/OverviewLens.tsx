import type { RunSummary, SystemContract } from "../../data/InvestigationDataSource";
import type { InvestigationLens } from "../../state/investigation";

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

function shortIdentity(value: string): string {
  return value.length <= 20 ? value : `${value.slice(0, 12)}…${value.slice(-6)}`;
}

export function OverviewLens({ run, system, onOpen }: OverviewLensProps) {
  const coverage = run.coverage ?? [];
  const projected = coverage.filter((entry) => entry.status === "projected").length;
  const gaps = coverage.length - projected;
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
          <dt>Profile</dt>
          <dd>{run.profile_identity}</dd>
        </div>
        <div>
          <dt>Schema</dt>
          <dd>{run.ontology_schema}</dd>
        </div>
        <div>
          <dt>Coverage</dt>
          <dd>{coverage.length ? `${projected} projected · ${gaps} explicit gaps` : "No ledger entries"}</dd>
        </div>
        <div>
          <dt>Delivery</dt>
          <dd>{system.mode.replaceAll("_", " ")}</dd>
        </div>
        <div>
          <dt>Source run</dt>
          <dd title={run.source_run_hash}>{shortIdentity(run.source_run_hash)}</dd>
        </div>
        <div>
          <dt>Projection</dt>
          <dd title={run.projection_digest}>{shortIdentity(run.projection_digest)}</dd>
        </div>
      </dl>

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
