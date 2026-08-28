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
      <CandidateBasins candidates={candidates} correspondence={correspondence} />
      <ResidualHistory residuals={residuals} relations={relations} />
      <CertificatePanel
        candidates={candidates}
        certificates={certificates}
        relations={relations}
      />
    </article>
  );
}
