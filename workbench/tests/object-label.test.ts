import { describe, expect, it } from "vitest";

import type { OntologyObjectContract } from "../src/data/InvestigationDataSource";
import { ontologyObjectLabel } from "../src/visuals/shared/objectLabel";

function object(kind: string, properties: Readonly<Record<string, unknown>>): OntologyObjectContract {
  return {
    record_type: "ontology_object",
    ref: { record_type: "ontology_ref", id: `ewm:test:${kind}:12345678`, kind },
    layer: "economic_declaration",
    properties,
    sources: [],
  };
}

describe("ontology object labels", () => {
  it("preserves declared natural keys", () => {
    expect(ontologyObjectLabel(object("claim", { natural_key: "Market clearing claim" })))
      .toBe("Market clearing claim");
  });

  it("renders semantic declaration fields without inventing names", () => {
    expect(ontologyObjectLabel(object("agent", { role: "household", count: 40 })))
      .toBe("Households (40)");
    expect(ontologyObjectLabel(object("market", { market: "spot_fx" }))).toBe("Spot Fx");
  });

  it("keeps machine identities out of the primary label", () => {
    expect(ontologyObjectLabel(object("state_observation", {})))
      .toBe("State Observation");
  });

  it("describes repeated runtime records with a readable event coordinate", () => {
    expect(ontologyObjectLabel(object("mechanism_invocation", {
      event_sequence: 42,
      state_version: 21,
    }))).toBe("Market clearing · Period 21");
    expect(ontologyObjectLabel(object("transaction", { event_sequence: 42 })))
      .toBe("Aggregate cleared trade · Event 42");
  });

  it("reads sequences from nested runtime events", () => {
    expect(ontologyObjectLabel(object("step", { event: { kind: "run_agents", sequence: 9 } })))
      .toBe("Run Agents · Event 9");
  });
});
