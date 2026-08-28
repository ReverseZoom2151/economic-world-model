import type {
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";
import type { TimeWindow } from "../../state/investigation";
import { StateActionFlow } from "../../visuals/runtime/StateActionFlow";
import { eventSequence } from "../../visuals/runtime/model";

interface RuntimeLensProps {
  readonly events: ReadonlyArray<OntologyObjectContract>;
  readonly relations: ReadonlyArray<RelationContract>;
  readonly timeWindow: TimeWindow | null;
  readonly selectedId: string | null;
  readonly onSelect: (id: string) => void;
}

export function RuntimeLens({
  events,
  relations,
  timeWindow,
  selectedId,
  onSelect,
}: RuntimeLensProps) {
  const visible = events.filter((event) => {
    const sequence = eventSequence(event);
    return (
      timeWindow === null ||
      (sequence !== null && sequence >= timeWindow.start && sequence <= timeWindow.end)
    );
  });
  return (
    <article className="lens-surface runtime-lens">
      <header className="lens-heading">
        <div>
          <p>Runtime / episode</p>
          <h2>Runtime episode</h2>
        </div>
        <strong>
          {timeWindow === null
            ? "All projected events"
            : `Sequence ${timeWindow.start}–${timeWindow.end}`}
        </strong>
      </header>
      {visible.length === 0 ? (
        <p className="sparse-fallback">No events fall inside the selected sequence window.</p>
      ) : (
        <StateActionFlow
          events={visible}
          relations={relations}
          selectedId={selectedId}
          onSelect={onSelect}
        />
      )}
    </article>
  );
}
