import type {
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";
import { CandidateBasins } from "../../visuals/ddge/CandidateBasins";
import { CertificatePanel } from "../../visuals/ddge/CertificatePanel";
import { objectsByKind } from "../../visuals/ddge/model";
import { ResidualHistory } from "../../visuals/ddge/ResidualHistory";

interface DdgeLensProps {
  readonly objects: ReadonlyArray<OntologyObjectContract>;
  readonly relations: ReadonlyArray<RelationContract>;
}

export function DdgeLens({ objects, relations }: DdgeLensProps) {
  const candidates = objectsByKind(objects, "ddge_candidate");
  const residuals = objectsByKind(objects, "residual");
  const certificates = objectsByKind(objects, "theorem_certificate");
  const correspondence = objectsByKind(objects, "inner_equilibrium")[0] ?? null;
  return (
    <article className="lens-surface ddge-lens">
      <header className="lens-heading">
        <div>
          <p>DDGE / assessment</p>
          <h2>DDGE diagnostics</h2>
        </div>
        <strong>{candidates.length} retained candidates</strong>
      </header>
      <dl className="ddge-summary" aria-label="DDGE evidence summary">
        <div><dt>Candidates</dt><dd>{candidates.length}</dd></div>
        <div><dt>Residuals</dt><dd>{residuals.length}</dd></div>
        <div><dt>Certificates</dt><dd>{certificates.length}</dd></div>
        <div><dt>Correspondence</dt><dd>{correspondence === null ? "unavailable" : "projected"}</dd></div>
      </dl>
      <CandidateBasins candidates={candidates} correspondence={correspondence} />
      <details className="diagnostic-disclosure" open={residuals.length > 0 && residuals.length <= 6}>
        <summary>Residual diagnostics · {residuals.length}</summary>
        <ResidualHistory residuals={residuals} relations={relations} />
      </details>
      <CertificatePanel
        candidates={candidates}
        certificates={certificates}
        relations={relations}
      />
    </article>
  );
}
