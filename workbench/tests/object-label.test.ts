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

  it("retains a traceable identity suffix when no label field exists", () => {
    expect(ontologyObjectLabel(object("state_observation", {})))
      .toBe("State Observation · 12345678");
  });
});
