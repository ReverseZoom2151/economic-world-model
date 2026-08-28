import type {
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";
import { formattedNumber, propertyNumber, propertyText } from "./model";

interface ResidualHistoryProps {
  readonly residuals: ReadonlyArray<OntologyObjectContract>;
  readonly relations: ReadonlyArray<RelationContract>;
}

function residualValue(residual: OntologyObjectContract): string {
  const value = residual.properties.value;
  if (!Array.isArray(value) || value.some((item) => typeof item !== "number")) {
    return "vector unavailable";
  }
  return `[${value.map((item) => formattedNumber(item as number)).join(", ")}]`;
}

function candidateId(
  residual: OntologyObjectContract,
  relations: ReadonlyArray<RelationContract>,
): string {
  return (
    relations.find(
      (relation) =>
        relation.relation_type === "HAS_RESIDUAL" && relation.target.id === residual.ref.id,
    )?.source.id ?? "unlinked residual"
  );
}

export function ResidualHistory({ residuals, relations }: ResidualHistoryProps) {
  if (residuals.length === 0) {
    return <p className="sparse-fallback">No residual diagnostics were projected.</p>;
  }
  return (
    <section className="residual-history" aria-labelledby="residual-history-title">
      <h3 id="residual-history-title">Residual diagnostics</h3>
      <div className="residual-table" role="table" aria-label="Scalar and vector residuals">
        {residuals.map((residual) => (
          <article role="row" key={residual.ref.id}>
            <header>
              <span>{candidateId(residual, relations)}</span>
              <strong>{propertyText(residual, "status") ?? "status unavailable"}</strong>
            </header>
            <code>{residualValue(residual)}</code>
            <dl>
              <div>
                <dt>Norm</dt>
                <dd>
                  {propertyNumber(residual, "norm") === null
                    ? "unavailable"
                    : formattedNumber(propertyNumber(residual, "norm")!)}
                </dd>
              </div>
              <div>
                <dt>Tolerance</dt>
                <dd>
                  {propertyNumber(residual, "tolerance") === null
                    ? "unavailable"
                    : formattedNumber(propertyNumber(residual, "tolerance")!)}
                </dd>
              </div>
              <div>
                <dt>Solver</dt>
                <dd>{propertyText(residual, "solver") ?? "unavailable"}</dd>
              </div>
              <div>
                <dt>Stopping rule</dt>
                <dd>{propertyText(residual, "stopping_rule") ?? "unavailable"}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}
