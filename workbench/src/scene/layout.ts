import type {
  OntologyObjectContract,
  RelationContract,
} from "../data/InvestigationDataSource";
import {
  LEGEND,
  SEMANTIC_LANES,
  semanticLane,
  type SemanticLane,
} from "../visuals/graph/visualGrammar";

export type DepthBasis = "event_sequence" | "version_index" | "reference_plane";

export interface SceneNode {
  readonly id: string;
  readonly kind: string;
  readonly layer: string;
  readonly label: string;
  readonly lane: SemanticLane;
  readonly color: string;
  readonly shape: "circle" | "diamond" | "hexagon" | "rectangle" | "triangle";
  readonly position: readonly [number, number, number];
  readonly depthBasis: DepthBasis;
}

export interface SceneRelation {
  readonly id: string;
  readonly relationType: string;
  readonly sourceId: string;
  readonly targetId: string;
  readonly sourcePosition: readonly [number, number, number];
  readonly targetPosition: readonly [number, number, number];
}

export interface SceneLayout {
  readonly nodes: ReadonlyArray<SceneNode>;
  readonly relations: ReadonlyArray<SceneRelation>;
  readonly omittedNodes: number;
  readonly omittedRelations: number;
}

export interface SceneLimits {
  readonly nodeLimit: number;
  readonly relationLimit: number;
}

export const DEFAULT_SCENE_LIMITS: SceneLimits = Object.freeze({
  nodeLimit: 5_000,
  relationLimit: 10_000,
});

const LAYER_Y: Readonly<Record<string, number>> = {
  schema: 5,
  economic_declaration: 3,
  runtime_occurrence: 1,
  learning_equilibrium: -1,
  research_evidence: -3,
  provenance: -5,
};

function boundedLimit(value: number, fallback: number): number {
  return Number.isInteger(value) && value >= 0 ? value : fallback;
}

function naturalLabel(object: OntologyObjectContract): string {
  const naturalKey = object.properties.natural_key;
  return typeof naturalKey === "string" && naturalKey.trim() ? naturalKey : object.ref.id;
}

function finiteCoordinate(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function depth(object: OntologyObjectContract): readonly [number, DepthBasis] {
  const context = object.properties.context;
  if (typeof context === "object" && context !== null && !Array.isArray(context)) {
    const sequence = finiteCoordinate(
      (context as Readonly<Record<string, unknown>>).event_sequence,
    );
    if (sequence !== null) {
      return [sequence, "event_sequence"];
    }
  }
  const version = finiteCoordinate(object.properties.version_index);
  return version === null ? [0, "reference_plane"] : [version, "version_index"];
}

function nodeBase(object: OntologyObjectContract): Omit<SceneNode, "position"> & {
  readonly base: readonly [number, number, number];
} {
  const lane = semanticLane(object.ref.kind);
  const laneIndex = SEMANTIC_LANES.indexOf(lane);
  const legend = LEGEND.find((entry) => entry.lane === lane) ?? LEGEND.at(-1)!;
  const [z, depthBasis] = depth(object);
  return {
    id: object.ref.id,
    kind: object.ref.kind,
    layer: object.layer,
    label: naturalLabel(object),
    lane,
    color: legend.color,
    shape: legend.shape,
    base: [(laneIndex - (SEMANTIC_LANES.length - 1) / 2) * 3, LAYER_Y[object.layer] ?? -7, z],
    depthBasis,
  };
}

export function layoutOntologyScene(
  objects: ReadonlyArray<OntologyObjectContract>,
  relations: ReadonlyArray<RelationContract>,
  limits: Partial<SceneLimits> = {},
): SceneLayout {
  const nodeLimit = boundedLimit(limits.nodeLimit ?? DEFAULT_SCENE_LIMITS.nodeLimit, DEFAULT_SCENE_LIMITS.nodeLimit);
  const relationLimit = boundedLimit(
    limits.relationLimit ?? DEFAULT_SCENE_LIMITS.relationLimit,
    DEFAULT_SCENE_LIMITS.relationLimit,
  );
  const selectedObjects = [...objects]
    .sort((left, right) => left.ref.id.localeCompare(right.ref.id))
    .slice(0, nodeLimit);
  const occupancy = new Map<string, number>();
  const nodes = selectedObjects.map((object): SceneNode => {
    const item = nodeBase(object);
    const occupancyKey = item.base.join("|");
    const ordinal = occupancy.get(occupancyKey) ?? 0;
    occupancy.set(occupancyKey, ordinal + 1);
    const column = ordinal % 5;
    const row = Math.floor(ordinal / 5);
    return {
      id: item.id,
      kind: item.kind,
      layer: item.layer,
      label: item.label,
      lane: item.lane,
      color: item.color,
      shape: item.shape,
      position: [item.base[0] + column * 0.24, item.base[1] + row * 0.24, item.base[2]],
      depthBasis: item.depthBasis,
    };
  });
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const eligibleRelations = [...relations]
    .sort((left, right) => left.ref.id.localeCompare(right.ref.id))
    .filter(
      (relation) => nodeById.has(relation.source.id) && nodeById.has(relation.target.id),
    );
  const selectedRelations = eligibleRelations.slice(0, relationLimit).map((relation) => ({
    id: relation.ref.id,
    relationType: relation.relation_type,
    sourceId: relation.source.id,
    targetId: relation.target.id,
    sourcePosition: nodeById.get(relation.source.id)!.position,
    targetPosition: nodeById.get(relation.target.id)!.position,
  }));
  return {
    nodes,
    relations: selectedRelations,
    omittedNodes: Math.max(0, objects.length - nodes.length),
    omittedRelations: Math.max(0, relations.length - selectedRelations.length),
  };
}
