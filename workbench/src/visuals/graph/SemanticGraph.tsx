import type { Core, ElementDefinition } from "cytoscape";
import { useEffect, useMemo } from "react";

import type {
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";
import { LEGEND, stableSemanticLayout } from "./visualGrammar";
import type { SemanticCoordinate } from "./visualGrammar";

interface SemanticGraphProps {
  readonly objects: ReadonlyArray<OntologyObjectContract>;
  readonly relations: ReadonlyArray<RelationContract>;
  readonly selectedId: string | null;
  readonly onSelect: (id: string) => void;
}

function label(object: OntologyObjectContract): string {
  const naturalKey = object.properties.natural_key;
  return typeof naturalKey === "string" ? naturalKey : object.ref.id;
}

function NodeGlyph({ coordinate }: { readonly coordinate: SemanticCoordinate }) {
  switch (coordinate.shape) {
    case "circle":
      return <circle r="13" fill={coordinate.color} />;
    case "diamond":
      return <polygon points="0,-15 15,0 0,15 -15,0" fill={coordinate.color} />;
    case "hexagon":
      return (
        <polygon points="-13,-8 0,-15 13,-8 13,8 0,15 -13,8" fill={coordinate.color} />
      );
    case "triangle":
      return <polygon points="0,-16 15,13 -15,13" fill={coordinate.color} />;
    case "rectangle":
      return <rect x="-15" y="-11" width="30" height="22" fill={coordinate.color} />;
  }
}

export function SemanticGraph({
  objects,
  relations,
  selectedId,
  onSelect,
}: SemanticGraphProps) {
  const layout = useMemo(() => stableSemanticLayout(objects), [objects]);
  const objectIds = useMemo(() => new Set(objects.map((object) => object.ref.id)), [objects]);
  const visibleRelations = relations.filter(
    (relation) => objectIds.has(relation.source.id) && objectIds.has(relation.target.id),
  );
  const elements = useMemo<ReadonlyArray<ElementDefinition>>(
    () => [
      ...objects.map((object) => ({
        data: { id: object.ref.id, label: label(object), kind: object.ref.kind },
        position: layout[object.ref.id],
      })),
      ...visibleRelations.map((relation) => ({
        data: {
          id: relation.ref.id,
          source: relation.source.id,
          target: relation.target.id,
          relationType: relation.relation_type,
        },
      })),
    ],
    [layout, objects, visibleRelations],
  );

  useEffect(() => {
    let graph: Core | null = null;
    let active = true;
    void import("cytoscape").then(({ default: cytoscape }) => {
      const created = cytoscape({
        elements: [...elements],
        headless: true,
        layout: { name: "preset", fit: false },
        styleEnabled: false,
      });
      if (active) {
        graph = created;
      } else {
        created.destroy();
      }
    });
    return () => {
      active = false;
      graph?.destroy();
    };
  }, [elements]);

  const width = Math.max(720, ...Object.values(layout).map((coordinate) => coordinate.x + 100));
  const height = Math.max(360, ...Object.values(layout).map((coordinate) => coordinate.y + 80));
  const sourceBoundary = [
    ...new Set(
      objects.flatMap((object) =>
        object.sources.map(
          (source) => `${source.source_kind.replaceAll("_", " ")} · ${source.source_id}`,
        ),
      ),
    ),
  ].sort();

  return (
    <div className="semantic-graph">
      <ul className="typed-legend" aria-label="Ontology legend">
        {LEGEND.map((entry) => (
          <li key={entry.lane}>
            <span
              className={`legend-shape legend-shape--${entry.shape}`}
              style={{ "--legend-color": entry.color } as React.CSSProperties}
              aria-hidden="true"
            />
            {entry.label}
          </li>
        ))}
      </ul>
      <div className="source-boundary" aria-label="Displayed source boundary">
        {sourceBoundary.map((source) => (
          <span key={source}>{source}</span>
        ))}
      </div>
      <svg
        className="semantic-graph__plot"
        role="img"
        aria-label="Stable semantic graph of declared economic objects"
        viewBox={`0 0 ${width} ${height}`}
      >
        {visibleRelations.map((relation) => {
          const source = layout[relation.source.id];
          const target = layout[relation.target.id];
          return source === undefined || target === undefined ? null : (
            <line
              key={relation.ref.id}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              className="semantic-edge"
            />
          );
        })}
        {objects.map((object) => {
          const coordinate = layout[object.ref.id];
          return coordinate === undefined ? null : (
            <g
              key={object.ref.id}
              transform={`translate(${coordinate.x} ${coordinate.y})`}
              className={selectedId === object.ref.id ? "semantic-node is-selected" : "semantic-node"}
            >
              <NodeGlyph coordinate={coordinate} />
              <text x="20" y="4">
                {label(object)}
              </text>
            </g>
          );
        })}
      </svg>
      <ol className="semantic-graph__equivalent" aria-label="World objects">
        {objects.map((object) => (
          <li key={object.ref.id}>
            <button
              type="button"
              aria-pressed={selectedId === object.ref.id}
              aria-label={`Inspect ${label(object)}`}
              onClick={() => onSelect(object.ref.id)}
            >
              <span>{object.ref.kind.replaceAll("_", " ")}</span>
              <strong>{label(object)}</strong>
              <small>{layout[object.ref.id]?.lane}</small>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
