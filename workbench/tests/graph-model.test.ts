import { describe, expect, it } from "vitest";

import type {
  OntologyObjectContract,
  RelationContract,
} from "../src/data/InvestigationDataSource";
import {
  deriveGraphView,
  graphClusters,
  layoutGraph2D,
  neighborhoodIds,
  shortestGraphPath,
} from "../src/visuals/graph/model";

function object(id: string, kind: string, layer = "economic_declaration"): OntologyObjectContract {
  return {
    record_type: "ontology_object",
    ref: { record_type: "ontology_ref", id, kind },
    layer,
    properties: { natural_key: id },
    sources: [],
  };
}

function relation(
  id: string,
  type: string,
  source: OntologyObjectContract,
  target: OntologyObjectContract,
): RelationContract {
  return {
    record_type: "relation_assertion",
    ref: { record_type: "ontology_ref", id, kind: "relation_assertion" },
    relation_type: type,
    source: source.ref,
    target: target.ref,
    properties: {},
    sources: [],
  };
}

const agent = object("agent", "agent");
const market = object("market", "market");
const datum = object("datum", "generated_datum", "runtime_occurrence");
const model = object("model", "model_version", "learning_equilibrium");
const objects = [agent, market, datum, model];
const relations = [
  relation("r1", "PARTICIPATES_IN", agent, market),
  relation("r2", "GENERATES", market, datum),
  relation("r3", "PRODUCES", datum, model),
];

describe("ontology graph model", () => {
  it("derives typed and layered graph views without inventing endpoints", () => {
    const view = deriveGraphView(objects, relations, {
      layers: ["economic_declaration", "runtime_occurrence"],
      relationTypes: ["GENERATES"],
      selectedId: null,
      isolate: false,
      neighborhoodDepth: 1,
      pathTargetId: null,
      density: "detail",
    });

    expect(view.objects.map((item) => item.ref.id).sort()).toEqual(["agent", "datum", "market"]);
    expect(view.relations.map((item) => item.ref.id)).toEqual(["r2"]);
  });

  it("expands bounded neighborhoods and returns a deterministic shortest path", () => {
    expect([...neighborhoodIds(relations, "agent", 1)].sort()).toEqual(["agent", "market"]);
    expect(shortestGraphPath(relations, "agent", "model")).toEqual({
      nodeIds: ["agent", "market", "datum", "model"],
      relationIds: ["r1", "r2", "r3"],
    });
  });

  it("isolates a neighborhood while retaining a requested path", () => {
    const view = deriveGraphView(objects, relations, {
      layers: [],
      relationTypes: [],
      selectedId: "agent",
      isolate: true,
      neighborhoodDepth: 1,
      pathTargetId: "model",
      density: "overview",
    });

    expect(view.objects.map((item) => item.ref.id).sort()).toEqual(["agent", "datum", "market", "model"]);
    expect([...view.pathRelationIds]).toEqual(["r1", "r2", "r3"]);
  });

  it("builds stable force coordinates and explicit semantic clusters", () => {
    const first = layoutGraph2D(objects, relations, "force");
    const second = layoutGraph2D([...objects].reverse(), [...relations].reverse(), "force");

    expect(second).toEqual(first);
    expect(graphClusters(objects)).toEqual([
      { lane: "agents", count: 1, kinds: ["agent"] },
      { lane: "data", count: 1, kinds: ["generated_datum"] },
      { lane: "markets", count: 1, kinds: ["market"] },
      { lane: "models", count: 1, kinds: ["model_version"] },
    ]);
  });
});
