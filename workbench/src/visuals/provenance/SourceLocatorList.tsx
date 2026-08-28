import type { SourceLocatorContract } from "../../data/InvestigationDataSource";
import { portableArtifactPath } from "./path";

interface SourceLocatorListProps {
  readonly sources: ReadonlyArray<SourceLocatorContract>;
}

export function SourceLocatorList({ sources }: SourceLocatorListProps) {
  if (sources.length === 0) {
    return <p className="source-locator-empty">No source locator recorded.</p>;
  }
  return (
    <ul className="source-locators" aria-label="Source locators">
      {sources.map((source, index) => (
        <li
          key={`${source.source_kind}:${source.source_id}:${source.record_selector ?? ""}:${index}`}
        >
          <div>
            <span>{source.source_kind.replaceAll("_", " ")}</span>
            <strong>{source.source_id}</strong>
          </div>
          <code>{portableArtifactPath(source.artifact_path)}</code>
          {source.record_selector === null ? null : <small>{source.record_selector}</small>}
          {source.code_symbol === null ? null : <small>{source.code_symbol}</small>}
          {source.paper_anchor === null ? null : <small>{source.paper_anchor}</small>}
          {source.payload_digest === null ? null : (
            <small title={source.payload_digest}>digest {source.payload_digest.slice(0, 12)}</small>
          )}
        </li>
      ))}
    </ul>
  );
}
