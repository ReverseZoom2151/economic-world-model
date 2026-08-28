import { useMemo } from "react";

import type { OntologyObjectContract } from "../../data/InvestigationDataSource";
import {
  type GraphDensity,
  type GraphLayoutMode,
  type GraphView,
  layoutGraph2D,
} from "./model";
import { LEGEND, semanticLane } from "./visualGrammar";

interface OntologyGraph2DProps {
  readonly view: GraphView;
  readonly layoutMode: GraphLayoutMode;
  readonly density: GraphDensity;
  readonly selectedId: string | null;
  readonly onSelect: (id: string) => void;
}

function label(object: OntologyObjectContract): string {
  const naturalKey = object.properties.natural_key;
  return typeof naturalKey === "string" && naturalKey.trim() ? naturalKey : object.ref.id;
}

function visibleLabel(value: string, density: GraphDensity): string {
  const limit = density === "detail" ? 34 : 20;
  return value.length <= limit ? value : `${value.slice(0, limit - 1)}…`;
}

function relationColor(type: string): string {
  const colors = ["#286f6c", "#805c14", "#6b4c7a", "#8b4438", "#496584", "#51613b"];
  let hash = 0;
  for (let index = 0; index < type.length; index += 1) hash = (hash * 31 + type.charCodeAt(index)) | 0;
  return colors[Math.abs(hash) % colors.length]!;
}

export function OntologyGraph2D({
  view,
  layoutMode,
  density,
  selectedId,
  onSelect,
}: OntologyGraph2DProps) {
  const positions = useMemo(
    () => layoutGraph2D(view.objects, view.relations, layoutMode),
    [layoutMode, view.objects, view.relations],
  );
  const objectsById = useMemo(
    () => new Map(view.objects.map((object) => [object.ref.id, object])),
    [view.objects],
  );
  if (view.objects.length === 0) {
    return <p className="sparse-fallback">No graph objects satisfy the current evidence filters.</p>;
  }
  return (
    <section className="ontology-graph-2d" aria-label="Interactive two-dimensional ontology graph">
      <svg viewBox="0 0 1200 720" role="group" aria-label="Selectable ontology nodes and typed relations">
        <title>Ontology graph with {view.objects.length} nodes and {view.relations.length} relations</title>
        <defs>
          <marker id="graph-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke" />
          </marker>
        </defs>
        <g aria-label="Typed relations">
          {view.relations.map((relation) => {
            const source = positions[relation.source.id];
            const target = positions[relation.target.id];
            if (source === undefined || target === undefined) return null;
            const highlighted = view.pathRelationIds.has(relation.ref.id);
            return (
              <line
                key={relation.ref.id}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke={highlighted ? "#151813" : relationColor(relation.relation_type)}
                strokeWidth={highlighted ? 4 : 1.5}
                strokeOpacity={highlighted ? 0.95 : 0.48}
                markerEnd="url(#graph-arrow)"
              >
                <title>{relation.relation_type}: {relation.source.id} → {relation.target.id}</title>
              </line>
            );
          })}
        </g>
        <g aria-label="Ontology objects">
          {view.objects.map((object) => {
            const point = positions[object.ref.id];
            if (point === undefined) return null;
            const lane = semanticLane(object.ref.kind);
            const legend = LEGEND.find((entry) => entry.lane === lane) ?? LEGEND.at(-1)!;
            const selected = selectedId === object.ref.id;
            const highlighted = view.pathNodeIds.has(object.ref.id);
            const radius = selected ? 15 : highlighted ? 12 : 9;
            const name = label(object);
            return (
              <g
                key={object.ref.id}
                className="ontology-graph-2d__node"
                transform={`translate(${point.x} ${point.y})`}
                role="button"
                tabIndex={0}
                aria-label={`Select ${name}, ${object.ref.kind.replaceAll("_", " ")}`}
                aria-pressed={selected}
                onClick={() => onSelect(object.ref.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelect(object.ref.id);
                  }
                }}
              >
                <circle
                  r={radius + 5}
                  fill="transparent"
                  stroke={selected ? "#151813" : highlighted ? "#c7f24a" : "transparent"}
                  strokeWidth={selected ? 3 : 5}
                />
                <circle r={radius} fill={legend.color} stroke="#f3f3eb" strokeWidth="2" />
                <text x={radius + 8} y="4" data-selected={selected}>
                  {visibleLabel(name, density)}
                </text>
                <title>{name} · {object.ref.kind} · {object.layer}</title>
              </g>
            );
          })}
        </g>
      </svg>
      <footer className="graph-readable-status" aria-live="polite">
        <span>{view.objects.length} visible nodes</span>
        <span>{view.relations.length} typed relations</span>
        <span>{view.pathRelationIds.size ? `${view.pathRelationIds.size}-edge path highlighted` : "No path highlighted"}</span>
        {selectedId !== null && objectsById.has(selectedId) ? (
          <strong>Selected: {label(objectsById.get(selectedId)!)}</strong>
        ) : null}
      </footer>
    </section>
  );
}
