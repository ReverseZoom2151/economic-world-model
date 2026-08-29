import type { SourceLocatorContract } from "../../data/InvestigationDataSource";
import { portableArtifactPath } from "./path";
import { TechnicalDetails } from "./TechnicalDetails";

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
            <strong>{portableArtifactPath(source.artifact_path)}</strong>
          </div>
          {source.paper_anchor === null ? null : <small>{source.paper_anchor}</small>}
          {source.code_symbol === null ? null : <small>{source.code_symbol}</small>}
          <TechnicalDetails
            summary="Source details"
            details={[
              { label: "Source identity", value: source.source_id },
              { label: "Record selector", value: source.record_selector },
              { label: "Payload digest", value: source.payload_digest },
            ]}
          />
        </li>
      ))}
    </ul>
  );
}
