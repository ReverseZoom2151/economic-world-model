import { describe, expect, it } from "vitest";

import type { OntologyObjectContract, RelationContract } from "../src/data/InvestigationDataSource";
import { layoutOntologyScene } from "../src/scene/layout";

const source = {
  record_type: "source_locator" as const,
  source_kind: "verified_run",
  source_id: "run:scene",
  artifact_path: "events.jsonl",
  record_selector: null,
  code_symbol: null,
  paper_anchor: null,
  payload_digest: "a".repeat(64),
};

function object(
  id: string,
  kind: string,
  layer: string,
  properties: Readonly<Record<string, unknown>> = {},
): OntologyObjectContract {
  return {
    record_type: "ontology_object",
    ref: { record_type: "ontology_ref", id, kind },
    layer,
    properties,
    sources: [source],
  };
}

const objects = [
  object("agent:1", "agent", "economic_declaration", { natural_key: "Household" }),
  object("market:1", "market", "economic_declaration", { natural_key: "Credit market" }),
  object("action:1", "action_occurrence", "runtime_occurrence", {
    context: { event_sequence: 4 },
  }),
  object("model:1", "model_version", "learning_equilibrium", { version_index: 2 }),
] as const;

const relations: ReadonlyArray<RelationContract> = [
  {
    record_type: "relation_assertion",
    ref: { record_type: "ontology_ref", id: "relation:1", kind: "relation_assertion" },
    relation_type: "PARTICIPATES_IN",
    source: objects[0].ref,
    target: objects[1].ref,
    properties: {},
    sources: [source],
  },
];

describe("deterministic ontology scene layout", () => {
  it("maps semantic lane to X, ontology layer to Y, and declared time or version to Z", () => {
    const layout = layoutOntologyScene(objects, relations);
    const agent = layout.nodes.find((node) => node.id === "agent:1")!;
    const market = layout.nodes.find((node) => node.id === "market:1")!;
    const action = layout.nodes.find((node) => node.id === "action:1")!;
    const model = layout.nodes.find((node) => node.id === "model:1")!;

    expect(agent.lane).toBe("agents");
    expect(market.lane).toBe("markets");
    expect(agent.position[0]).not.toBe(market.position[0]);
    expect(agent.position[1]).not.toBe(action.position[1]);
    expect(agent.position[2]).toBe(0);
    expect(agent.depthBasis).toBe("reference_plane");
    expect(action.position[2]).toBe(4);
    expect(action.depthBasis).toBe("event_sequence");
    expect(model.position[2]).toBe(2);
    expect(model.depthBasis).toBe("version_index");
  });

  it("is stable under input reordering and keeps relation direction", () => {
    const first = layoutOntologyScene(objects, relations);
    const second = layoutOntologyScene([...objects].reverse(), [...relations].reverse());

    expect(second).toEqual(first);
    expect(first.relations[0]).toMatchObject({
      sourceId: "agent:1",
      targetId: "market:1",
      relationType: "PARTICIPATES_IN",
    });
  });

  it("applies explicit progressive limits and reports every omitted record", () => {
    const layout = layoutOntologyScene(objects, relations, { nodeLimit: 2, relationLimit: 0 });

    expect(layout.nodes).toHaveLength(2);
    expect(layout.relations).toHaveLength(0);
    expect(layout.omittedNodes).toBe(2);
    expect(layout.omittedRelations).toBe(1);
  });
});
