import type {
  OntologyObjectContract,
  PathResultContract,
} from "../../data/InvestigationDataSource";
import { SourceLocatorList } from "../provenance/SourceLocatorList";
import { TechnicalDetails } from "../provenance/TechnicalDetails";
import { ontologyKindLabel, ontologyObjectLabel } from "../shared/objectLabel";

interface LineagePathProps {
  readonly result: PathResultContract;
  readonly objects: ReadonlyArray<OntologyObjectContract>;
}

export function LineagePath({ result, objects }: LineagePathProps) {
  const objectsById = new Map(objects.map((object) => [object.ref.id, object]));
  const path = result.paths[0];
  if (path === undefined) {
    return (
      <section className="lineage-path lineage-path--empty" aria-label="Lineage path">
        <strong>No directed lineage path was found.</strong>
        <p>
          {result.truncated
            ? "Search stopped at the configured record limit."
            : "No relation sequence connects the selected identities in this direction."}
        </p>
        <small>{result.visited_records} records visited</small>
      </section>
    );
  }
  return (
    <section className="lineage-path" aria-label="Lineage path">
      <ol>
        {path.nodes.map((node, index) => {
          const relation = path.relations[index];
          const object = objectsById.get(node.id);
          return (
            <li key={`${node.id}:${index}`}>
              <article className="lineage-node">
                <span>{ontologyKindLabel(node.kind)}</span>
                <strong>{object === undefined ? `${ontologyKindLabel(node.kind)} record` : ontologyObjectLabel(object)}</strong>
                <TechnicalDetails details={[{ label: "Record ID", value: node.id }]} />
              </article>
              {relation === undefined ? null : (
                <article className="lineage-relation">
                  <strong>{relation.relation_type} →</strong>
                  <small>Directed provenance relation</small>
                  <TechnicalDetails
                    details={[
                      { label: "Relation ID", value: relation.ref.id },
                      { label: "Source record", value: relation.source.id },
                      { label: "Target record", value: relation.target.id },
                    ]}
                  />
                  <SourceLocatorList sources={relation.sources} />
                </article>
              )}
            </li>
          );
        })}
      </ol>
      <footer>
        <span>{result.visited_records} records visited</span>
        <span>{result.paths.length} bounded path{result.paths.length === 1 ? "" : "s"}</span>
        {result.truncated ? <strong>Results truncated</strong> : <span>Search complete</span>}
      </footer>
    </section>
  );
}
