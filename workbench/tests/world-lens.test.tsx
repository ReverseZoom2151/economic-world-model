import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { WorldLens } from "../src/lenses/world/WorldLens";
import { stableSemanticLayout } from "../src/visuals/graph/visualGrammar";
import type {
  OntologyObjectContract,
  RelationContract,
} from "../src/data/InvestigationDataSource";

const source = {
  record_type: "source_locator" as const,
  source_kind: "verified_run",
  source_id: "run-a",
  artifact_path: "config.json",
  record_selector: "identity",
  code_symbol: null,
  paper_anchor: null,
  payload_digest: "a".repeat(64),
};

function object(index: number, kind = "agent"): OntologyObjectContract {
  return {
    record_type: "ontology_object",
    ref: {
      record_type: "ontology_ref",
      id: `ewm:test:${kind}:${String(index).padStart(2, "0")}`,
      kind,
    },
    layer: "economic_declaration",
    properties: { natural_key: `${kind} ${index}` },
    sources: [source],
  };
}

function relation(left: OntologyObjectContract, right: OntologyObjectContract): RelationContract {
  return {
    record_type: "relation_assertion",
    ref: {
      record_type: "ontology_ref",
      id: "ewm:test:relation:participates",
      kind: "relation_assertion",
    },
    relation_type: "PARTICIPATES_IN",
    source: left.ref,
    target: right.ref,
    properties: {},
    sources: [source],
  };
}

describe("WorldLens", () => {
  it("assigns identical semantic coordinates to repeated input", () => {
    const objects = [object(2, "market"), object(1, "agent"), object(3, "dataset")];

    const first = stableSemanticLayout(objects);
    const second = stableSemanticLayout([...objects].reverse());

    expect(first).toEqual(second);
    expect(first["ewm:test:agent:01"]?.lane).toBe("agents");
    expect(first["ewm:test:market:02"]?.lane).toBe("markets");
  });

  it("shows typed legend, sources, selection, and bounded progressive expansion", async () => {
    const user = userEvent.setup();
    const objects = Array.from({ length: 14 }, (_, index) =>
      object(index, index === 1 ? "market" : "agent"),
    );
    const onSelect = vi.fn();
    render(
      <WorldLens
        objects={objects}
        relations={[relation(objects[0]!, objects[1]!)]}
        selectedId={null}
        onSelect={onSelect}
      />,
    );

    expect(screen.getByRole("heading", { name: "Declared economic world" })).toBeVisible();
    expect(screen.getByRole("list", { name: "Ontology legend" })).toBeVisible();
    expect(screen.getByText("verified run · 12 records")).toBeVisible();
    expect(screen.getAllByRole("button", { name: /Inspect/ })).toHaveLength(12);

    await user.click(screen.getByRole("button", { name: "Show 2 more objects" }));
    expect(screen.getAllByRole("button", { name: /Inspect/ })).toHaveLength(14);
    await user.click(screen.getAllByRole("button", { name: /Inspect/ })[0]!);
    expect(onSelect).toHaveBeenCalledWith("ewm:test:agent:00");
  });
});
