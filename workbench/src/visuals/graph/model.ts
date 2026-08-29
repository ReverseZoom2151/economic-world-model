import type {
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";
import { semanticLane, type SemanticLane } from "./visualGrammar";

export type GraphLayoutMode = "semantic" | "force" | "hierarchy";
export type GraphDensity = "overview" | "detail";

export interface GraphViewOptions {
  readonly layers: ReadonlyArray<string>;
  readonly relationTypes: ReadonlyArray<string>;
  readonly selectedId: string | null;
  readonly isolate: boolean;
  readonly neighborhoodDepth: number;
  readonly pathTargetId: string | null;
  readonly density: GraphDensity;
}

export interface GraphView {
  readonly objects: ReadonlyArray<OntologyObjectContract>;
  readonly relations: ReadonlyArray<RelationContract>;
  readonly pathNodeIds: ReadonlySet<string>;
  readonly pathRelationIds: ReadonlySet<string>;
  readonly omittedObjects: number;
}

export interface GraphCluster {
  readonly lane: SemanticLane;
  readonly count: number;
  readonly kinds: ReadonlyArray<string>;
}

export interface GraphCoordinate2D {
  readonly x: number;
  readonly y: number;
}

const LAYER_ORDER = [
  "schema",
  "economic_declaration",
  "runtime_occurrence",
  "learning_equilibrium",
  "research_evidence",
  "provenance",
] as const;

function orderedObjects(
  objects: ReadonlyArray<OntologyObjectContract>,
): ReadonlyArray<OntologyObjectContract> {
  return [...objects].sort((left, right) => left.ref.id.localeCompare(right.ref.id));
}

function orderedRelations(
  relations: ReadonlyArray<RelationContract>,
): ReadonlyArray<RelationContract> {
  return [...relations].sort((left, right) => left.ref.id.localeCompare(right.ref.id));
}

function adjacency(
  relations: ReadonlyArray<RelationContract>,
): ReadonlyMap<string, ReadonlyArray<{ readonly id: string; readonly relationId: string }>> {
  const result = new Map<string, Array<{ readonly id: string; readonly relationId: string }>>();
  for (const relation of orderedRelations(relations)) {
    result.set(relation.source.id, [
      ...(result.get(relation.source.id) ?? []),
      { id: relation.target.id, relationId: relation.ref.id },
    ]);
    result.set(relation.target.id, [
      ...(result.get(relation.target.id) ?? []),
      { id: relation.source.id, relationId: relation.ref.id },
    ]);
  }
  return result;
}

export function neighborhoodIds(
  relations: ReadonlyArray<RelationContract>,
  startId: string,
  depth: number,
): ReadonlySet<string> {
  const graph = adjacency(relations);
  const visited = new Set([startId]);
  let frontier = [startId];
  for (let level = 0; level < Math.max(0, depth); level += 1) {
    const next: string[] = [];
    for (const id of frontier) {
      for (const neighbor of graph.get(id) ?? []) {
        if (!visited.has(neighbor.id)) {
          visited.add(neighbor.id);
          next.push(neighbor.id);
        }
      }
    }
    frontier = next;
    if (frontier.length === 0) break;
  }
  return visited;
}

export function shortestGraphPath(
  relations: ReadonlyArray<RelationContract>,
  startId: string,
  targetId: string,
): { readonly nodeIds: ReadonlyArray<string>; readonly relationIds: ReadonlyArray<string> } | null {
  if (startId === targetId) return { nodeIds: [startId], relationIds: [] };
  const graph = adjacency(relations);
  const queue = [startId];
  const previous = new Map<string, { readonly id: string; readonly relationId: string }>();
  const visited = new Set([startId]);
  while (queue.length > 0) {
    const current = queue.shift()!;
    for (const neighbor of graph.get(current) ?? []) {
      if (visited.has(neighbor.id)) continue;
      visited.add(neighbor.id);
      previous.set(neighbor.id, { id: current, relationId: neighbor.relationId });
      if (neighbor.id === targetId) {
        const nodeIds = [targetId];
        const relationIds: string[] = [];
        let cursor = targetId;
        while (cursor !== startId) {
          const step = previous.get(cursor)!;
          relationIds.unshift(step.relationId);
          nodeIds.unshift(step.id);
          cursor = step.id;
        }
        return { nodeIds, relationIds };
      }
      queue.push(neighbor.id);
    }
  }
  return null;
}

function degreeById(relations: ReadonlyArray<RelationContract>): ReadonlyMap<string, number> {
  const degree = new Map<string, number>();
  for (const relation of relations) {
    degree.set(relation.source.id, (degree.get(relation.source.id) ?? 0) + 1);
    degree.set(relation.target.id, (degree.get(relation.target.id) ?? 0) + 1);
  }
  return degree;
}

export function deriveGraphView(
  objects: ReadonlyArray<OntologyObjectContract>,
  relations: ReadonlyArray<RelationContract>,
  options: GraphViewOptions,
): GraphView {
  const allowedLayers = new Set(options.layers);
  const allowedTypes = new Set(options.relationTypes);
  const layered = orderedObjects(objects).filter(
    (object) => allowedLayers.size === 0 || allowedLayers.has(object.layer),
  );
  const layeredIds = new Set(layered.map((object) => object.ref.id));
  const typedRelations = orderedRelations(relations).filter(
    (relation) =>
      layeredIds.has(relation.source.id) &&
      layeredIds.has(relation.target.id) &&
      (allowedTypes.size === 0 || allowedTypes.has(relation.relation_type)),
  );
  const path =
    options.selectedId !== null && options.pathTargetId !== null
      ? shortestGraphPath(typedRelations, options.selectedId, options.pathTargetId)
      : null;
  const pathNodeIds = new Set(path?.nodeIds ?? []);
  const pathRelationIds = new Set(path?.relationIds ?? []);
  const isolatedIds =
    options.isolate && options.selectedId !== null
      ? new Set(neighborhoodIds(typedRelations, options.selectedId, options.neighborhoodDepth))
      : null;
  if (isolatedIds !== null) {
    for (const id of pathNodeIds) isolatedIds.add(id);
  }
  const eligible = isolatedIds === null
    ? layered
    : layered.filter((object) => isolatedIds.has(object.ref.id));
  const limit = options.density === "detail" ? 400 : 72;
  const degree = degreeById(typedRelations);
  const prioritized = [...eligible].sort((left, right) => {
    const leftPriority = pathNodeIds.has(left.ref.id) || left.ref.id === options.selectedId ? 1 : 0;
    const rightPriority = pathNodeIds.has(right.ref.id) || right.ref.id === options.selectedId ? 1 : 0;
    return (
      rightPriority - leftPriority ||
      (degree.get(right.ref.id) ?? 0) - (degree.get(left.ref.id) ?? 0) ||
      left.ref.id.localeCompare(right.ref.id)
    );
  });
  const selectedObjects = options.density === "detail"
    ? prioritized.slice(0, limit)
    : prioritized.reduce<OntologyObjectContract[]>((selected, object) => {
        if (selected.length >= limit) return selected;
        const priority = pathNodeIds.has(object.ref.id) || object.ref.id === options.selectedId;
        const group = `${object.layer}:${object.ref.kind}`;
        const groupCount = selected.filter(
          (candidate) => `${candidate.layer}:${candidate.ref.kind}` === group,
        ).length;
        if (priority || groupCount < 6) selected.push(object);
        return selected;
      }, []);
  const selectedIds = new Set(selectedObjects.map((object) => object.ref.id));
  return {
    objects: selectedObjects,
    relations: typedRelations.filter(
      (relation) => selectedIds.has(relation.source.id) && selectedIds.has(relation.target.id),
    ),
    pathNodeIds,
    pathRelationIds,
    omittedObjects: Math.max(0, eligible.length - selectedObjects.length),
  };
}

export function graphClusters(
  objects: ReadonlyArray<OntologyObjectContract>,
): ReadonlyArray<GraphCluster> {
  const clusters = new Map<SemanticLane, { count: number; kinds: Set<string> }>();
  for (const object of objects) {
    const lane = semanticLane(object.ref.kind);
    const current = clusters.get(lane) ?? { count: 0, kinds: new Set<string>() };
    current.count += 1;
    current.kinds.add(object.ref.kind);
    clusters.set(lane, current);
  }
  return [...clusters]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([lane, cluster]) => ({
      lane,
      count: cluster.count,
      kinds: [...cluster.kinds].sort(),
    }));
}

function hashFraction(value: string): number {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) / 0xffffffff;
}

function normalizedPositions(
  positions: ReadonlyMap<string, GraphCoordinate2D>,
): Readonly<Record<string, GraphCoordinate2D>> {
  const values = [...positions.values()];
  const minX = Math.min(...values.map((item) => item.x));
  const maxX = Math.max(...values.map((item) => item.x));
  const minY = Math.min(...values.map((item) => item.y));
  const maxY = Math.max(...values.map((item) => item.y));
  const width = Math.max(1, maxX - minX);
  const height = Math.max(1, maxY - minY);
  return Object.fromEntries(
    [...positions].map(([id, point]) => [
      id,
      { x: 70 + ((point.x - minX) / width) * 1060, y: 60 + ((point.y - minY) / height) * 600 },
    ]),
  );
}

export function layoutGraph2D(
  objects: ReadonlyArray<OntologyObjectContract>,
  relations: ReadonlyArray<RelationContract>,
  mode: GraphLayoutMode,
): Readonly<Record<string, GraphCoordinate2D>> {
  const ordered = orderedObjects(objects);
  if (ordered.length === 0) return {};
  if (mode === "hierarchy") {
    const positions = new Map<string, GraphCoordinate2D>();
    const groups = new Map<string, OntologyObjectContract[]>();
    for (const object of ordered) {
      groups.set(object.layer, [...(groups.get(object.layer) ?? []), object]);
    }
    const layers = [...groups].sort(([left], [right]) => {
      const leftIndex = LAYER_ORDER.indexOf(left as (typeof LAYER_ORDER)[number]);
      const rightIndex = LAYER_ORDER.indexOf(right as (typeof LAYER_ORDER)[number]);
      return (leftIndex < 0 ? 99 : leftIndex) - (rightIndex < 0 ? 99 : rightIndex) || left.localeCompare(right);
    });
    layers.forEach(([, group], column) => {
      group.forEach((object, row) => positions.set(object.ref.id, { x: column, y: row }));
    });
    return normalizedPositions(positions);
  }
  if (mode === "semantic") {
    const positions = new Map<string, GraphCoordinate2D>();
    const groups = new Map<string, OntologyObjectContract[]>();
    for (const object of ordered) {
      const lane = semanticLane(object.ref.kind);
      groups.set(lane, [...(groups.get(lane) ?? []), object]);
    }
    [...groups].sort(([left], [right]) => left.localeCompare(right)).forEach(([, group], column) => {
      group.forEach((object, row) => positions.set(object.ref.id, { x: column, y: row }));
    });
    return normalizedPositions(positions);
  }

  const positions = new Map<string, { x: number; y: number }>();
  ordered.forEach((object, index) => {
    const angle = 2 * Math.PI * ((index + hashFraction(object.ref.id)) / ordered.length);
    const radius = 1 + 0.35 * hashFraction(`radius:${object.ref.id}`);
    positions.set(object.ref.id, { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius });
  });
  const eligibleRelations = orderedRelations(relations).filter(
    (relation) => positions.has(relation.source.id) && positions.has(relation.target.id),
  );
  for (let iteration = 0; iteration < 60; iteration += 1) {
    const force = new Map(ordered.map((object) => [object.ref.id, { x: 0, y: 0 }]));
    for (let leftIndex = 0; leftIndex < ordered.length; leftIndex += 1) {
      for (let rightIndex = leftIndex + 1; rightIndex < ordered.length; rightIndex += 1) {
        const left = positions.get(ordered[leftIndex]!.ref.id)!;
        const right = positions.get(ordered[rightIndex]!.ref.id)!;
        const dx = left.x - right.x;
        const dy = left.y - right.y;
        const distanceSquared = Math.max(0.025, dx * dx + dy * dy);
        const magnitude = 0.008 / distanceSquared;
        const leftForce = force.get(ordered[leftIndex]!.ref.id)!;
        const rightForce = force.get(ordered[rightIndex]!.ref.id)!;
        leftForce.x += dx * magnitude;
        leftForce.y += dy * magnitude;
        rightForce.x -= dx * magnitude;
        rightForce.y -= dy * magnitude;
      }
    }
    for (const relation of eligibleRelations) {
      const source = positions.get(relation.source.id)!;
      const target = positions.get(relation.target.id)!;
      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const attraction = 0.018;
      force.get(relation.source.id)!.x += dx * attraction;
      force.get(relation.source.id)!.y += dy * attraction;
      force.get(relation.target.id)!.x -= dx * attraction;
      force.get(relation.target.id)!.y -= dy * attraction;
    }
    for (const object of ordered) {
      const point = positions.get(object.ref.id)!;
      const delta = force.get(object.ref.id)!;
      point.x = point.x * 0.996 + Math.max(-0.08, Math.min(0.08, delta.x));
      point.y = point.y * 0.996 + Math.max(-0.08, Math.min(0.08, delta.y));
    }
  }
  return normalizedPositions(positions);
}
