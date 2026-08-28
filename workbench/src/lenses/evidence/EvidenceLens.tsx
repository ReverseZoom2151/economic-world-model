import { useEffect, useState } from "react";

import type {
  InvestigationDataSource,
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";
import { ClaimAudit } from "../../visuals/evidence/ClaimAudit";

interface EvidenceLensProps {
  readonly dataSource: InvestigationDataSource;
  readonly runId: string;
}

type EvidenceLoad =
  | { readonly key: string; readonly status: "loading" | "failed" }
  | {
      readonly key: string;
      readonly status: "loaded";
      readonly claims: ReadonlyArray<OntologyObjectContract>;
      readonly evidence: ReadonlyArray<OntologyObjectContract>;
      readonly relations: ReadonlyArray<RelationContract>;
    };

export function EvidenceLens({ dataSource, runId }: EvidenceLensProps) {
  const [load, setLoad] = useState<EvidenceLoad>({ key: "", status: "loading" });
  useEffect(() => {
    let active = true;
    void Promise.all([
      dataSource.claims({ runId, limit: 200 }),
      dataSource.evidence({ runId, limit: 200 }),
      dataSource.relations({ runId, relationTypes: ["SUPPORTS"], limit: 200 }),
    ])
      .then(([claims, evidence, relations]) => {
        if (active) {
          setLoad({
            key: runId,
            status: "loaded",
            claims: claims.items,
            evidence: evidence.items,
            relations: relations.items,
          });
        }
      })
      .catch(() => {
        if (active) {
          setLoad({ key: runId, status: "failed" });
        }
      });
    return () => {
      active = false;
    };
  }, [dataSource, runId]);

  return (
    <section className="analytical-lens evidence-lens">
      <header className="analytical-lens__heading">
        <div>
          <p>07 / EVIDENCE</p>
          <h2>Evidence lens</h2>
        </div>
        <p>Claims remain separate from the artifacts and relations that support them.</p>
      </header>
      {load.key !== runId ? <p className="lens-loading">Tracing evidence relations…</p> : null}
      {load.key === runId && load.status === "failed" ? (
        <p className="sparse-fallback" role="alert">Evidence projection unavailable.</p>
      ) : null}
      {load.key === runId && load.status === "loaded" ? (
        <ClaimAudit claims={load.claims} evidence={load.evidence} relations={load.relations} />
      ) : null}
    </section>
  );
}
