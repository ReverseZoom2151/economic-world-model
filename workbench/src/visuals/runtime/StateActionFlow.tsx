import type {
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";
import { eventLabel, eventSequence, orderedRuntimeEvents } from "./model";

interface StateActionFlowProps {
  readonly events: ReadonlyArray<OntologyObjectContract>;
  readonly relations: ReadonlyArray<RelationContract>;
  readonly selectedId: string | null;
  readonly onSelect: (id: string) => void;
}

export function StateActionFlow({
  events,
  relations,
  selectedId,
  onSelect,
}: StateActionFlowProps) {
  const ordered = orderedRuntimeEvents(events);
  return (
    <div className="runtime-flow">
      <ol aria-label="State action transition flow">
        {ordered.map((event) => (
          <li key={event.ref.id} data-event-kind={event.ref.kind}>
            <span className="runtime-flow__sequence">
              {eventSequence(event)?.toString().padStart(3, "0") ?? "—"}
            </span>
            <button
              type="button"
              aria-pressed={selectedId === event.ref.id}
              onClick={() => onSelect(event.ref.id)}
            >
              <span>{event.ref.kind.replaceAll("_", " ")}</span>
              <strong>{eventLabel(event)}</strong>
            </button>
          </li>
        ))}
      </ol>
      <p className="runtime-flow__relations">
        {relations.length} typed transition{relations.length === 1 ? "" : "s"}
      </p>
    </div>
  );
}
