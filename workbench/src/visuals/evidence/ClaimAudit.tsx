import type {
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";
import { SourceLocatorList } from "../provenance/SourceLocatorList";
import { classification, limitations, objectLabel, statusShape } from "./model";

interface ClaimAuditProps {
  readonly claims: ReadonlyArray<OntologyObjectContract>;
  readonly evidence: ReadonlyArray<OntologyObjectContract>;
  readonly relations: ReadonlyArray<RelationContract>;
}

function Classification({ value }: { readonly value: string }) {
  return (
    <span className="evidence-classification">
      <span aria-hidden="true" data-status-shape={value}>{statusShape(value)}</span>
      {value.replaceAll("_", " ")}
    </span>
  );
}

export function ClaimAudit({ claims, evidence, relations }: ClaimAuditProps) {
  if (claims.length === 0) {
    return (
      <section className="claim-audit" aria-label="Claim audit">
        <div className="sparse-fallback">
          <strong>No claims are available.</strong>
          <p>The projection does not expose a claim record for this run.</p>
        </div>
      </section>
    );
  }
  const evidenceById = new Map(evidence.map((item) => [item.ref.id, item]));
  return (
    <section className="claim-audit" aria-label="Claim audit">
      {claims.map((claim) => {
        const supportingRelations = relations.filter(
          (relation) =>
            relation.relation_type === "SUPPORTS" && relation.target.id === claim.ref.id,
        );
        const linked = supportingRelations
          .map((relation) => evidenceById.get(relation.source.id))
          .filter((item): item is OntologyObjectContract => item !== undefined);
        const claimLimitations = limitations(claim);
        return (
          <article className="claim-card" key={claim.ref.id}>
            <header>
              <div>
                <p>Claim</p>
                <h3>{objectLabel(claim)}</h3>
                <code>{claim.ref.id}</code>
              </div>
              <Classification value={classification(claim)} />
            </header>
            <div className="claim-card__section">
              <h4>Claim sources</h4>
              <SourceLocatorList sources={claim.sources} />
            </div>
            <div className="claim-card__section">
              <h4>Limitations</h4>
              {claimLimitations.length ? (
                <ul className="limitation-list">
                  {claimLimitations.map((item) => <li key={item}>{item}</li>)}
                </ul>
              ) : (
                <p className="evidence-absence">No limitations were recorded.</p>
              )}
            </div>
            <div className="claim-card__section">
              <h4>Support status: {linked.length ? "linked" : "unsupported"}</h4>
              {linked.length === 0 ? (
                <p className="evidence-absence">No supporting evidence is linked to this claim.</p>
              ) : (
                <div className="supporting-evidence">
                  {linked.map((item) => (
                    <article key={item.ref.id}>
                      <header>
                        <div>
                          <p>SUPPORTS →</p>
                          <h5>{objectLabel(item)}</h5>
                          <code>{item.ref.id}</code>
                        </div>
                        <Classification value={classification(item)} />
                      </header>
                      {item.properties.source_file_status === "missing" ? (
                        <p className="missing-source" role="status">Source file reported missing.</p>
                      ) : null}
                      <SourceLocatorList sources={item.sources} />
                    </article>
                  ))}
                </div>
              )}
            </div>
          </article>
        );
      })}
    </section>
  );
}
