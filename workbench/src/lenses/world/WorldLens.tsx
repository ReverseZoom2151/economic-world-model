import { useState } from "react";

import type {
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";
import { SemanticGraph } from "../../visuals/graph/SemanticGraph";

interface WorldLensProps {
  readonly objects: ReadonlyArray<OntologyObjectContract>;
  readonly relations: ReadonlyArray<RelationContract>;
  readonly selectedId: string | null;
  readonly onSelect: (id: string) => void;
}

const INITIAL_OBJECT_LIMIT = 12;

export function WorldLens({ objects, relations, selectedId, onSelect }: WorldLensProps) {
  const [limit, setLimit] = useState(INITIAL_OBJECT_LIMIT);
  const ordered = [...objects].sort((left, right) => left.ref.id.localeCompare(right.ref.id));
  const visible = ordered.slice(0, limit);
  const remaining = Math.max(0, ordered.length - visible.length);
  return (
    <article className="lens-surface world-lens">
      <header className="lens-heading">
        <div>
          <p>World / declarations</p>
          <h2>Declared economic world</h2>
        </div>
        <dl>
          <div>
            <dt>Objects</dt>
            <dd>{objects.length}</dd>
          </div>
          <div>
            <dt>Relations</dt>
            <dd>{relations.length}</dd>
          </div>
        </dl>
      </header>
      <SemanticGraph
        objects={visible}
        relations={relations}
        selectedId={selectedId}
        onSelect={onSelect}
      />
      {remaining > 0 ? (
        <button
          type="button"
          className="expand-button"
          onClick={() => setLimit(objects.length)}
        >
          Show {remaining} more objects
        </button>
      ) : null}
    </article>
  );
}
