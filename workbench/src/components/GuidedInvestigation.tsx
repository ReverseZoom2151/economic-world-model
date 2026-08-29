import { FX_AUDIT_JOURNEY_LENSES, useInvestigation } from "../state/investigation";

const STEPS = [
  { label: "Scope economy", finding: "Declared actors, market, and accounting boundary" },
  { label: "Inspect execution", finding: "Ordered agent and clearing events" },
  { label: "Read outcomes", finding: "Prices, volume, residuals, and rejections" },
  { label: "Test model closure", finding: "Behavior-to-training evidence boundary" },
  { label: "Check equilibrium", finding: "Inner equilibrium versus DDGE evidence" },
  { label: "Audit claim", finding: "Classification, sources, and limitations" },
  { label: "Trace provenance", finding: "Directed evidence lineage" },
  { label: "Inspect ontology", finding: "Semantic structure and local context" },
  { label: "Bound geography", finding: "Declared anchors and uncertainty" },
  { label: "State conclusion", finding: "Supported result and explicit limits" },
] as const;

export function GuidedInvestigation() {
  const { state, dispatch } = useInvestigation();
  if (state.journey?.id !== "fx-execution-audit") return null;
  const step = Math.max(0, Math.min(STEPS.length - 1, state.journey.step));
  const current = STEPS[step]!;
  const complete = step === STEPS.length - 1;

  return (
    <section className="guided-investigation" aria-labelledby="guided-investigation-title">
      <div className="guided-investigation__coordinate">
        <span>Active investigation</span>
        <strong>{String(step + 1).padStart(2, "0")} / {STEPS.length}</strong>
      </div>
      <div className="guided-investigation__brief">
        <p id="guided-investigation-title">
          Did the FX economy clear without rejected orders or material accounting drift?
        </p>
        <strong>{current.label}</strong>
        <small>{current.finding}</small>
        <progress value={step + 1} max={STEPS.length} aria-label="Investigation progress" />
      </div>
      <div className="guided-investigation__actions">
        <button
          type="button"
          disabled={step === 0}
          onClick={() => dispatch({ type: "move-fx-audit", direction: "back" })}
        >
          Back
        </button>
        {complete ? (
          <button type="button" onClick={() => dispatch({ type: "stop-research-journey" })}>
            Close investigation
          </button>
        ) : (
          <button
            type="button"
            className="guided-investigation__next"
            onClick={() => dispatch({ type: "move-fx-audit", direction: "next" })}
          >
            Next: {STEPS[step + 1]!.label}
          </button>
        )}
      </div>
      <ol className="guided-investigation__steps" aria-label="Investigation stages">
        {FX_AUDIT_JOURNEY_LENSES.map((lens, index) => (
          <li
            key={`${lens}:${index}`}
            data-status={index < step ? "complete" : index === step ? "current" : "pending"}
          >
            <span aria-hidden="true">{index < step ? "✓" : index + 1}</span>
            <span className="visually-hidden">{STEPS[index]!.label}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
