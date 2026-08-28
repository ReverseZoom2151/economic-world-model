import type { ComparisonResultContract } from "../../data/InvestigationDataSource";
import { comparisonSections, printable, record, records, text } from "./model";

interface ComparisonPreflightProps {
  readonly comparison: ComparisonResultContract;
}

function metadataRow(label: string, value: unknown) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{printable(value)}</dd>
    </div>
  );
}

export function ComparisonPreflight({ comparison }: ComparisonPreflightProps) {
  const { preflight, aligned, unaligned } = comparisonSections(comparison);
  if (preflight === null || typeof preflight.compatible !== "boolean") {
    return (
      <section className="comparison-preflight comparison-preflight--invalid" aria-label="Comparison preflight">
        <h3>Preflight unavailable</h3>
        <p>The comparison response did not contain a recognized compatibility decision.</p>
      </section>
    );
  }
  const compatible = preflight.compatible;
  const issues = records(preflight.issues);
  return (
    <>
      <section className="comparison-preflight" aria-label="Comparison preflight">
        <header>
          <div>
            <p>Compatibility gate</p>
            <h3>{compatible ? "Compatible" : "Incompatible"}</h3>
          </div>
          <span className={`comparison-verdict comparison-verdict--${compatible ? "accepted" : "rejected"}`}>
            {compatible ? "◇ accepted" : "✕ rejected"}
          </span>
        </header>
        {issues.length === 0 ? (
          <p className="comparison-note">No preflight issues were reported.</p>
        ) : (
          <ol className="comparison-issues">
            {issues.map((issue, index) => (
              <li key={`${text(issue.code)}:${index}`}>
                <div>
                  <code>{text(issue.code)}</code>
                  <span>{issue.blocking === true ? "blocking" : "non-blocking"}</span>
                </div>
                <strong>{text(issue.message)}</strong>
                <small>
                  left {printable(issue.left)} · right {printable(issue.right)}
                </small>
              </li>
            ))}
          </ol>
        )}
      </section>
      <section className="aligned-comparison" aria-label="Aligned comparison">
        <header>
          <p>Explicit semantic joins</p>
          <h3>Aligned measurements</h3>
        </header>
        {!compatible ? (
          <div className="comparison-withheld">
            <strong>Aligned values withheld</strong>
            <p>A blocking run-level incompatibility prevents scientific alignment.</p>
          </div>
        ) : aligned.length === 0 ? (
          <div className="comparison-withheld">
            <strong>No aligned measurements</strong>
            <p>This is not evidence of no measurable difference.</p>
          </div>
        ) : (
          <div className="aligned-grid">
            {aligned.map((item, index) => {
              const pairing = record(item.pairing) ?? {};
              const multiplicity = record(item.multiplicity) ?? {};
              const leftIntervention = record(item.left_intervention) ?? {};
              const rightIntervention = record(item.right_intervention) ?? {};
              return (
                <article key={`${text(item.comparison_key)}:${index}`}>
                  <div className="aligned-grid__title">
                    <span>{text(item.estimand_identity)}</span>
                    <strong>{text(item.comparison_key)}</strong>
                    <code>{text(item.unit)}</code>
                  </div>
                  <div className="aligned-values">
                    <div>
                      <small>{text(item.left_name)}</small>
                      <strong>{printable(item.left_value)}</strong>
                      <span>{text(leftIntervention.level)}</span>
                    </div>
                    <span aria-label="compared with">↔</span>
                    <div>
                      <small>{text(item.right_name)}</small>
                      <strong>{printable(item.right_value)}</strong>
                      <span>{text(rightIntervention.level)}</span>
                    </div>
                  </div>
                  <dl>
                    {metadataRow("Sample", item.sample_identity)}
                    {metadataRow("Estimator", item.estimator_identity)}
                    {metadataRow("Pairing", pairing.method)}
                    {metadataRow("Seed set", `Seeds ${printable(pairing.seeds)}`)}
                    {metadataRow(
                      "Multiplicity",
                      `${text(multiplicity.method)} · α ${printable(multiplicity.alpha)}`,
                    )}
                    {metadataRow("Hypothesis", item.hypothesis_id)}
                  </dl>
                </article>
              );
            })}
          </div>
        )}
        {unaligned.length > 0 ? (
          <details className="unaligned-records">
            <summary>{unaligned.length} unaligned measurement records</summary>
            <ul>
              {unaligned.map((item, index) => (
                <li key={`${text(item.measurement_id)}:${index}`}>
                  <code>{text(item.measurement_id)}</code>
                  <span>{text(item.reason)}</span>
                </li>
              ))}
            </ul>
          </details>
        ) : null}
      </section>
    </>
  );
}
