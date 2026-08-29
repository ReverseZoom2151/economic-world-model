import type {
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";
import { formattedNumber, propertyNumber, propertyText } from "./model";
import { ontologyObjectLabel } from "../shared/objectLabel";

interface CertificatePanelProps {
  readonly candidates: ReadonlyArray<OntologyObjectContract>;
  readonly certificates: ReadonlyArray<OntologyObjectContract>;
  readonly relations: ReadonlyArray<RelationContract>;
}

function assumptions(certificate: OntologyObjectContract): ReadonlyArray<string> {
  const value = certificate.properties.assumptions;
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.trim() !== "")
    : [];
}

export function CertificatePanel({
  candidates,
  certificates,
  relations,
}: CertificatePanelProps) {
  return (
    <section className="certificate-panel" aria-labelledby="certificate-panel-title">
      <h3 id="certificate-panel-title">Certificates and authorized bounds</h3>
      <div>
        {candidates.map((candidate) => {
          const linkedIds = new Set(
            relations
              .filter(
                (relation) =>
                  relation.relation_type === "CERTIFIES" &&
                  relation.target.id === candidate.ref.id,
              )
              .map((relation) => relation.source.id),
          );
          const linked = certificates.filter((certificate) => linkedIds.has(certificate.ref.id));
          return (
            <article key={candidate.ref.id}>
              <h4>{ontologyObjectLabel(candidate)}</h4>
              {linked.length === 0 ? (
                <p>No linked theorem certificate authorizes a bound.</p>
              ) : (
                linked.map((certificate) => {
                  const bound = propertyNumber(certificate, "bound");
                  const requiredAssumptions = assumptions(certificate);
                  const authorized = bound !== null && requiredAssumptions.length > 0;
                  return (
                    <div key={certificate.ref.id}>
                      <strong>
                        {propertyText(certificate, "certificate_kind")?.replaceAll("_", " ")
                          ?? "theorem certificate"}
                      </strong>
                      {authorized ? (
                        <p>
                          {formattedNumber(bound)} {propertyText(certificate, "bound_unit") ?? "bound"}
                        </p>
                      ) : (
                        <p>Certificate metadata do not authorize a displayed bound.</p>
                      )}
                      <ul>
                        {requiredAssumptions.map((assumption) => (
                          <li key={assumption}>{assumption}</li>
                        ))}
                      </ul>
                    </div>
                  );
                })
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
