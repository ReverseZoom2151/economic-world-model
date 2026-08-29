import { useEffect, useState } from "react";

import type {
  InvestigationDataSource,
  OntologyObjectContract,
} from "../data/InvestigationDataSource";
import { useInvestigation } from "../state/investigation";
import { SourceLocatorList } from "../visuals/provenance/SourceLocatorList";
import { TechnicalDetails } from "../visuals/provenance/TechnicalDetails";
import { ontologyObjectLabel } from "../visuals/shared/objectLabel";

interface EvidenceInspectorProps {
  readonly dataSource: InvestigationDataSource;
}

export function EvidenceInspector({ dataSource }: EvidenceInspectorProps) {
  const { state } = useInvestigation();
  const selectionKey = `${state.runId ?? ""}|${state.objectId ?? ""}`;
  const [result, setResult] = useState<{
    readonly key: string;
    readonly object: OntologyObjectContract | null;
    readonly failed: boolean;
  }>({ key: "", object: null, failed: false });

  useEffect(() => {
    let active = true;
    if (state.runId === null || state.objectId === null) {
      return;
    }
    void dataSource
      .object(state.runId, state.objectId)
      .then((value) => {
        if (active) {
          setResult({ key: selectionKey, object: value, failed: false });
        }
      })
      .catch(() => {
        if (active) {
          setResult({ key: selectionKey, object: null, failed: true });
        }
      });
    return () => {
      active = false;
    };
  }, [dataSource, selectionKey, state.objectId, state.runId]);

  const object = result.key === selectionKey ? result.object : null;
  const failed = result.key === selectionKey && result.failed;

  return (
    <section className="workspace-panel inspector" aria-label="Evidence inspector">
      <header className="panel-heading">
        <span>03</span>
        <h2>Evidence</h2>
      </header>
      {state.objectId === null ? (
        <div className="inspector-empty">
          <p>Select an ontology object to inspect its claims, provenance, and source boundary.</p>
          <small>No evidence status is inferred from visual proximity.</small>
        </div>
      ) : null}
      {failed ? <p className="panel-note panel-note--error">Object evidence unavailable.</p> : null}
      {object !== null ? (
        <article className="object-detail">
          <p className="object-detail__kind">{object.ref.kind.replaceAll("_", " ")}</p>
          <h3>{ontologyObjectLabel(object)}</h3>
          <dl>
            <div>
              <dt>Layer</dt>
              <dd>{object.layer.replaceAll("_", " ")}</dd>
            </div>
            <div>
              <dt>Sources</dt>
              <dd>{object.sources.length}</dd>
            </div>
          </dl>
          <SourceLocatorList sources={object.sources} />
          <TechnicalDetails
            details={[
              { label: "Object identity", value: object.ref.id },
              { label: "Object kind", value: object.ref.kind },
              { label: "Ontology layer", value: object.layer },
            ]}
          />
        </article>
      ) : null}
    </section>
  );
}
