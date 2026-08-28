import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type {
  OntologyObjectContract,
  RelationContract,
} from "../src/data/InvestigationDataSource";
import { eligibleGeoPlacements } from "../src/globe/geometry";
import { GlobeLens } from "../src/lenses/globe/GlobeLens";
import { createFixtureDataSource } from "../src/testing/fixtures";

const source = {
  record_type: "source_locator" as const,
  source_kind: "researcher_declaration",
  source_id: "geo-overlay:1",
  artifact_path: "geo.json",
  record_selector: "anchors[0]",
  code_symbol: null,
  paper_anchor: null,
  payload_digest: "a".repeat(64),
};

const ref = (id: string, kind: string) => ({ record_type: "ontology_ref" as const, id, kind });
const object = (
  id: string,
  kind: string,
  layer: string,
  properties: Readonly<Record<string, unknown>>,
): OntologyObjectContract => ({
  record_type: "ontology_object",
  ref: ref(id, kind),
  layer,
  properties,
  sources: [source],
});

const market = object("market:1", "market", "economic_declaration", {
  natural_key: "Bucharest credit market",
});
const institution = object("institution:1", "institution", "economic_declaration", {
  natural_key: "Policy authority",
});
const unanchored = object("agent:unanchored", "agent", "economic_declaration", {
  natural_key: "Abstract household",
});
const bucharest = object("geo:bucharest", "geo_anchor", "provenance", {
  crs: "EPSG:4326",
  latitude: 44.4268,
  longitude: 26.1025,
  anchor_basis: "declared",
  evidence_classification: "researcher_declared",
  validity: { start: 0, end: 10 },
  uncertainty_km: 2.5,
});
const london = object("geo:london", "geo_anchor", "provenance", {
  crs: "EPSG:4326",
  latitude: 51.5072,
  longitude: -0.1276,
  anchor_basis: "observed",
  evidence_classification: "researcher_declared",
  validity: { start: 0, end: 10 },
  uncertainty_km: 1,
});

const relation = (
  id: string,
  type: string,
  relationSource: OntologyObjectContract,
  target: OntologyObjectContract,
): RelationContract => ({
  record_type: "relation_assertion",
  ref: ref(id, "relation_assertion"),
  relation_type: type,
  source: relationSource.ref,
  target: target.ref,
  properties: {},
  sources: [source],
});

const objects = [market, institution, unanchored, bucharest, london];
const relations = [
  relation("relation:market-geo", "GEO_ANCHORED_AT", market, bucharest),
  relation("relation:institution-geo", "GEO_ANCHORED_AT", institution, london),
  relation("relation:flow", "DERIVED_FROM", market, institution),
];

describe("economic globe", () => {
  it("places only explicitly anchored objects and filters declared validity", () => {
    const active = eligibleGeoPlacements(objects, relations, 5);
    const expired = eligibleGeoPlacements(objects, relations, 20);

    expect(active.map((placement) => placement.subject.ref.id)).toEqual([
      "institution:1",
      "market:1",
    ]);
    expect(active.some((placement) => placement.subject.ref.id === unanchored.ref.id)).toBe(false);
    expect(expired).toEqual([]);
  });

  it("keeps markers, evidence status, uncertainty, flows, and selection in the DOM fallback", async () => {
    const user = userEvent.setup();
    const dataSource = createFixtureDataSource();
    vi.spyOn(dataSource, "objects").mockResolvedValue({ items: objects, next_cursor: null });
    vi.spyOn(dataSource, "relations").mockResolvedValue({ items: relations, next_cursor: null });
    const onSelect = vi.fn();

    render(
      <GlobeLens
        dataSource={dataSource}
        runId="run-a"
        comparisonRunId={null}
        selectedId={null}
        time={5}
        onSelect={onSelect}
        webglAvailable={() => false}
      />,
    );

    expect(await screen.findByText("2 explicitly anchored objects")).toBeVisible();
    expect(screen.getAllByText("researcher declared")).toHaveLength(2);
    expect(screen.getByText("± 2.5 km")).toBeVisible();
    expect(screen.getByText("declared anchor")).toBeVisible();
    expect(screen.getByText("observed anchor")).toBeVisible();
    expect(screen.getAllByText(/researcher declaration: geo-overlay:1/)).toHaveLength(2);
    expect(screen.getByText("1 bounded flow")).toBeVisible();
    expect(screen.queryByText("Abstract household")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Select Bucharest credit market" }));
    expect(onSelect).toHaveBeenCalledWith("market:1");
  });

  it("shows a nonspatial unavailable state instead of locating synthetic objects", async () => {
    const dataSource = createFixtureDataSource();
    vi.spyOn(dataSource, "objects").mockResolvedValue({ items: [unanchored], next_cursor: null });
    vi.spyOn(dataSource, "relations").mockResolvedValue({ items: [], next_cursor: null });

    render(
      <GlobeLens
        dataSource={dataSource}
        runId="run-a"
        comparisonRunId={null}
        selectedId={null}
        time={null}
        onSelect={vi.fn()}
        webglAvailable={() => false}
      />,
    );

    expect(await screen.findByText("No explicit geography is available.")).toBeVisible();
    expect(screen.getByText("No jurisdiction or coordinate was inferred.")).toBeVisible();
  });

  it("labels comparison-run markers without inventing scenario versions", async () => {
    const dataSource = createFixtureDataSource();
    vi.spyOn(dataSource, "objects").mockImplementation(async (query) => ({
      items: query.runId === "run-a" ? [market, bucharest] : [institution, london],
      next_cursor: null,
    }));
    vi.spyOn(dataSource, "relations").mockImplementation(async (query) => ({
      items:
        query.runId === "run-a"
          ? [relations[0]!]
          : [relations[1]!],
      next_cursor: null,
    }));

    render(
      <GlobeLens
        dataSource={dataSource}
        runId="run-a"
        comparisonRunId="run-b"
        selectedId={null}
        time={5}
        onSelect={vi.fn()}
        webglAvailable={() => false}
      />,
    );

    expect(await screen.findByText("Comparison overlay: run-b")).toBeVisible();
    expect(screen.getByText("active run", { exact: true })).toBeVisible();
    expect(screen.getByText("comparison run", { exact: true })).toBeVisible();
    expect(screen.queryByText(/scenario v/i)).not.toBeInTheDocument();
  });
});
