import { useInvestigation, type InvestigationLens } from "../state/investigation";

const DESCRIPTIONS: Readonly<Record<InvestigationLens, string>> = {
  world: "Declared agents, institutions, markets, data, and model boundaries.",
  runtime: "Observed states, actions, transitions, settlements, and event order.",
  market: "Orders, clearing, prices, volumes, constraints, and rejections.",
  learning: "Generated datasets, training runs, learned parameters, and deployments.",
  ddge: "Candidate fixed points, residuals, stability, basins, and certificates.",
  compare: "Compatible measurements and every rejected alignment decision.",
  evidence: "Claims, evidence classifications, protocols, sources, and limitations.",
  lineage: "Derivation paths from runtime records back to artifacts and code.",
};

function title(lens: InvestigationLens): string {
  return lens === "ddge" ? "DDGE" : `${lens[0]?.toUpperCase()}${lens.slice(1)}`;
}

export function LensRouter() {
  const { state } = useInvestigation();
  return (
    <section className="active-lens" aria-label="Active analytical lens">
      <div className="active-lens__coordinate">02 / {state.lens.toUpperCase()}</div>
      <div className="active-lens__field">
        <p>Analytical surface</p>
        <h2>{title(state.lens)} lens</h2>
        <p>{DESCRIPTIONS[state.lens]}</p>
        <div className="active-lens__placeholder">
          <span aria-hidden="true">↳</span>
          <p>The shared selection boundary is ready for this lens.</p>
          <small>Scientific encodings arrive as isolated, tested visual modules.</small>
        </div>
      </div>
    </section>
  );
}
