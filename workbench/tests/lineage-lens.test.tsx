import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { OntologyObjectContract, PathResultContract, RelationContract } from "../src/data/InvestigationDataSource";
import { LineageLens } from "../src/lenses/lineage/LineageLens";
import { createFixtureDataSource } from "../src/testing/fixtures";

const sourceLocator = {
  record_type: "source_locator" as const,
  source_kind: "code",
  source_id: "git:abc123",
  artifact_path: "src/ewm/markets/clearing.py",
  record_selector: null,
  code_symbol: "clear_market",
  paper_anchor: null,
  payload_digest: "d".repeat(64),
};

const objects: ReadonlyArray<OntologyObjectContract> = [
  {
    record_type: "ontology_object",
    ref: { record_type: "ontology_ref", id: "action:1", kind: "action_occurrence" },
    layer: "runtime_occurrence",
    properties: { natural_key: "Submitted bid" },
    sources: [sourceLocator],
  },
  {
    record_type: "ontology_object",
    ref: { record_type: "ontology_ref", id: "outcome:1", kind: "outcome" },
    layer: "runtime_occurrence",
    properties: { natural_key: "Cleared allocation" },
    sources: [sourceLocator],
  },
];

const relation: RelationContract = {
  record_type: "relation_assertion",
  ref: { record_type: "ontology_ref", id: "relation:1", kind: "relation_assertion" },
  relation_type: "PRODUCES",
  source: objects[0]!.ref,
  target: objects[1]!.ref,
  properties: {},
  sources: [sourceLocator],
};

const pathResult: PathResultContract = {
  paths: [{ nodes: [objects[0]!.ref, objects[1]!.ref], relations: [relation] }],
  visited_records: 2,
  truncated: false,
};

describe("lineage lens", () => {
  it("preserves relation direction and source identity along a bounded path", async () => {
    const source = createFixtureDataSource();
    vi.spyOn(source, "objects").mockResolvedValue({ items: objects, next_cursor: null });
    vi.spyOn(source, "paths").mockResolvedValue(pathResult);

    render(<LineageLens dataSource={source} runId="run-a" selectedId="action:1" />);

    const path = await screen.findByRole("region", { name: "Lineage path" });
    expect(within(path).getByText("action:1")).toBeVisible();
    expect(within(path).getByText("PRODUCES →")).toBeVisible();
    expect(within(path).getByText("outcome:1")).toBeVisible();
    expect(within(path).getByText("git:abc123")).toBeVisible();
    expect(within(path).getByText("src/ewm/markets/clearing.py")).toBeVisible();
    expect(within(path).getByText("clear_market")).toBeVisible();
    expect(source.paths).toHaveBeenCalledWith(
      expect.objectContaining({
        direction: "outgoing",
        startId: "action:1",
        targetId: "outcome:1",
      }),
    );
  });

  it("shows bounded-search and missing-path states without drawing an inferred edge", async () => {
    const source = createFixtureDataSource();
    vi.spyOn(source, "objects").mockResolvedValue({ items: objects, next_cursor: null });
    vi.spyOn(source, "paths").mockResolvedValue({ paths: [], visited_records: 200, truncated: true });

    render(<LineageLens dataSource={source} runId="run-a" selectedId="action:1" />);

    expect(await screen.findByText("No directed lineage path was found.")).toBeVisible();
    expect(screen.getByText("Search stopped at the configured record limit.")).toBeVisible();
    expect(screen.queryByText("PRODUCES →")).not.toBeInTheDocument();
  });
});
