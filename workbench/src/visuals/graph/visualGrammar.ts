import type { OntologyObjectContract } from "../../data/InvestigationDataSource";

export const SEMANTIC_LANES = [
  "agents",
  "institutions",
  "markets",
  "data",
  "models",
  "evidence",
  "other",
] as const;

export type SemanticLane = (typeof SEMANTIC_LANES)[number];

export interface SemanticCoordinate {
  readonly x: number;
  readonly y: number;
  readonly lane: SemanticLane;
  readonly layer: string;
  readonly shape: "circle" | "diamond" | "hexagon" | "rectangle" | "triangle";
  readonly color: string;
}

export interface LegendEntry {
  readonly lane: SemanticLane;
  readonly label: string;
  readonly shape: SemanticCoordinate["shape"];
  readonly color: string;
}

export const LEGEND: ReadonlyArray<LegendEntry> = [
  { lane: "agents", label: "Agents", shape: "circle", color: "#0072b2" },
  { lane: "institutions", label: "Institutions", shape: "diamond", color: "#e69f00" },
  { lane: "markets", label: "Markets", shape: "hexagon", color: "#009e73" },
  { lane: "data", label: "Data", shape: "rectangle", color: "#cc79a7" },
  { lane: "models", label: "Learned models", shape: "triangle", color: "#d55e00" },
  { lane: "evidence", label: "Evidence", shape: "diamond", color: "#5f6360" },
  { lane: "other", label: "Other declarations", shape: "rectangle", color: "#8a8d83" },
];

const KIND_LANES: Readonly<Record<string, SemanticLane>> = {
  agent: "agents",
  capability: "agents",
  firm: "agents",
  household: "agents",
  learner: "agents",
  action: "agents",
  action_occurrence: "agents",
  belief: "agents",
  objective: "agents",
  constraint: "agents",
  institution: "institutions",
  mechanism: "institutions",
  protocol: "institutions",
  market: "markets",
  order_book: "markets",
  transaction: "markets",
  outcome: "markets",
  dataset: "data",
  generated_datum: "data",
  state_observation: "data",
  event: "data",
  measurement: "data",
  observation: "data",
  deployment: "models",
  learned_parameter: "models",
  model: "models",
  model_version: "models",
  parameter_version: "models",
  training_run: "models",
  claim: "evidence",
  evidence_artifact: "evidence",
};

const LAYER_ORDER: Readonly<Record<string, number>> = {
  schema: 0,
  economic_declaration: 1,
  runtime_occurrence: 2,
  learning_equilibrium: 3,
  research_evidence: 4,
  provenance: 5,
};

export function semanticLane(kind: string): SemanticLane {
  return KIND_LANES[kind] ?? "other";
}

export function stableSemanticLayout(
  objects: ReadonlyArray<OntologyObjectContract>,
): Readonly<Record<string, SemanticCoordinate>> {
  const result: Record<string, SemanticCoordinate> = {};
  const grouped = new Map<string, OntologyObjectContract[]>();
  for (const object of [...objects].sort((left, right) => left.ref.id.localeCompare(right.ref.id))) {
    const lane = semanticLane(object.ref.kind);
    const key = `${lane}|${object.layer}`;
    grouped.set(key, [...(grouped.get(key) ?? []), object]);
  }
  for (const [key, group] of [...grouped].sort(([left], [right]) => left.localeCompare(right))) {
    const [laneValue, layer = "unknown"] = key.split("|");
    const lane = laneValue as SemanticLane;
    const legend = LEGEND.find((entry) => entry.lane === lane) ?? LEGEND[LEGEND.length - 1]!;
    const laneIndex = SEMANTIC_LANES.indexOf(lane);
    const layerIndex = LAYER_ORDER[layer] ?? Object.keys(LAYER_ORDER).length;
    group.forEach((object, row) => {
      result[object.ref.id] = {
        x: 90 + laneIndex * 180,
        y: 75 + layerIndex * 115 + row * 54,
        lane,
        layer,
        shape: legend.shape,
        color: legend.color,
      };
    });
  }
  return result;
}
