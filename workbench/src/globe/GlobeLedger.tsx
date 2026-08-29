import { geoLabel, type GeoFlow, type TaggedGeoPlacement } from "./geometry";
import { TechnicalDetails } from "../visuals/provenance/TechnicalDetails";

interface GlobeLedgerProps {
  readonly placements: ReadonlyArray<TaggedGeoPlacement>;
  readonly flows: ReadonlyArray<GeoFlow>;
  readonly selectedId: string | null;
  readonly onSelect: (id: string) => void;
  readonly renderingUnavailable?: boolean;
}

export function GlobeLedger({
  placements,
  flows,
  selectedId,
  onSelect,
  renderingUnavailable = false,
}: GlobeLedgerProps) {
  return (
    <section className="globe-ledger" aria-label="Explicit geographic evidence">
      <header>
        <div>
          <p>{renderingUnavailable ? "Accessible 2D equivalent" : "Coordinate evidence ledger"}</p>
          <h3>{placements.length} explicitly anchored objects</h3>
        </div>
        <strong>{flows.length} bounded {flows.length === 1 ? "flow" : "flows"}</strong>
      </header>
      <ol>
        {placements.map((placement) => {
          const label = geoLabel(placement);
          const source = placement.anchor.sources[0];
          return (
            <li key={`${placement.runId}:${placement.subject.ref.id}`} data-selected={selectedId === placement.subject.ref.id}>
              <button
                type="button"
                aria-label={`Select ${label}`}
                aria-pressed={selectedId === placement.subject.ref.id}
                onClick={() => onSelect(placement.subject.ref.id)}
              >
                <span>{placement.runRole === "active" ? "active run" : "comparison run"}</span>
                <strong>{label}</strong>
                <small>{placement.crs} · {placement.latitude.toFixed(4)}, {placement.longitude.toFixed(4)}</small>
                <small>{placement.basis.replaceAll("_", " ")} anchor</small>
                <small>valid {String(placement.validity.start)} to {String(placement.validity.end)}</small>
                <small>{placement.evidenceClassification.replaceAll("_", " ")}</small>
                <small>± {placement.uncertaintyKm} km</small>
                {source === undefined ? null : (
                  <small>{source.source_kind.replaceAll("_", " ")} provenance</small>
                )}
              </button>
              <TechnicalDetails
                summary="Anchor details"
                details={[
                  { label: "Subject record ID", value: placement.subject.ref.id },
                  { label: "Anchor record ID", value: placement.anchor.ref.id },
                  { label: "Source record ID", value: source?.source_id },
                ]}
              />
            </li>
          );
        })}
      </ol>
    </section>
  );
}
