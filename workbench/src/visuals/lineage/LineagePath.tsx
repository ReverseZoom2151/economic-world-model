import type { PathResultContract } from "../../data/InvestigationDataSource";
import { SourceLocatorList } from "../provenance/SourceLocatorList";

interface LineagePathProps {
  readonly result: PathResultContract;
}

export function LineagePath({ result }: LineagePathProps) {
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
          return (
            <li key={`${node.id}:${index}`}>
              <article className="lineage-node">
                <span>{node.kind.replaceAll("_", " ")}</span>
                <strong>{node.id}</strong>
              </article>
              {relation === undefined ? null : (
                <article className="lineage-relation">
                  <strong>{relation.relation_type} →</strong>
                  <small>{relation.source.id} → {relation.target.id}</small>
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
