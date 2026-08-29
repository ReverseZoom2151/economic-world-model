import type {
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";
import { formattedNumber, propertyNumber, propertyText } from "./model";
import { TechnicalDetails } from "../provenance/TechnicalDetails";

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

function candidateIdentity(
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

function candidateLabel(identity: string): string {
  if (identity === "unlinked residual") return "Unlinked residual";
  return "Linked DDGE candidate";
}

export function ResidualHistory({ residuals, relations }: ResidualHistoryProps) {
  if (residuals.length === 0) {
    return <p className="sparse-fallback">No residual diagnostics were projected.</p>;
  }
  return (
    <section className="residual-history" aria-labelledby="residual-history-title">
      <h3 id="residual-history-title">Residual diagnostics</h3>
      <ol className="residual-table" aria-label="Scalar and vector residuals">
        {residuals.map((residual) => {
          const candidate = candidateIdentity(residual, relations);
          return (
            <li key={residual.ref.id}>
              <article>
              <header>
                <span>{candidateLabel(candidate)}</span>
                <strong>
                  {propertyText(residual, "status")?.replaceAll("_", " ")
                    ?? "status unavailable"}
                </strong>
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
                  <dd>{propertyText(residual, "solver")?.replaceAll("_", " ") ?? "unavailable"}</dd>
                </div>
                <div>
                  <dt>Stopping rule</dt>
                  <dd>{propertyText(residual, "stopping_rule") ?? "unavailable"}</dd>
                </div>
              </dl>
              <TechnicalDetails
                details={[
                  { label: "Residual identity", value: residual.ref.id },
                  { label: "Candidate identity", value: candidate },
                ]}
              />
              </article>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
