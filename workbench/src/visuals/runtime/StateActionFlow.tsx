import { useState } from "react";

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
  const [limit, setLimit] = useState(24);
  const visible = ordered.slice(0, limit);
  const remaining = ordered.length - visible.length;
  return (
    <div className="runtime-flow">
      <ol aria-label="State action transition flow">
        {visible.map((event) => (
          <li key={event.ref.id} data-event-kind={event.ref.kind}>
            <span className="runtime-flow__sequence">
              {eventSequence(event)?.toString().padStart(3, "0") ?? "n/a"}
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
      {remaining > 0 ? (
        <button type="button" className="expand-button" onClick={() => setLimit(ordered.length)}>
          Show {remaining} more events
        </button>
      ) : null}
      <p className="runtime-flow__relations">
        {relations.length} typed transition{relations.length === 1 ? "" : "s"}
      </p>
    </div>
  );
}
