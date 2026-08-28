import { useState } from "react";
import { createRoot } from "react-dom/client";

import type {
  InvestigationDataSource,
  OntologyObjectContract,
  RelationContract,
} from "../../src/data/InvestigationDataSource";
import { GlobeLens } from "../../src/lenses/globe/GlobeLens";
import "../../src/styles/global.css";
import { createFixtureDataSource } from "../../src/testing/fixtures";

const locator = {
  record_type: "source_locator" as const,
  source_kind: "researcher_declaration",
  source_id: "globe-e2e",
  artifact_path: "geo.json",
  record_selector: "anchors[0]",
  code_symbol: null,
  paper_anchor: null,
  payload_digest: "a".repeat(64),
};

const ref = (id: string, kind: string) => ({ record_type: "ontology_ref" as const, id, kind });

const market: OntologyObjectContract = {
  record_type: "ontology_object",
  ref: ref("market:bucharest", "market"),
  layer: "economic_declaration",
  properties: { natural_key: "Bucharest credit market" },
  sources: [locator],
};

const anchor: OntologyObjectContract = {
  record_type: "ontology_object",
  ref: ref("geo:bucharest", "geo_anchor"),
  layer: "provenance",
  properties: {
    crs: "EPSG:4326",
    latitude: 44.4268,
    longitude: 26.1025,
    anchor_basis: "declared",
    evidence_classification: "researcher_declared",
    validity: { start: 0, end: 10 },
    uncertainty_km: 2.5,
  },
  sources: [locator],
};

const geoRelation: RelationContract = {
  record_type: "relation_assertion",
  ref: ref("relation:market-geo", "relation_assertion"),
  relation_type: "GEO_ANCHORED_AT",
  source: market.ref,
  target: anchor.ref,
  properties: {},
  sources: [locator],
};

function globeDataSource(): InvestigationDataSource {
  const base = createFixtureDataSource();
  return {
    system: () => base.system(),
    runs: () => base.runs(),
    run: (id) => base.run(id),
    object: (runId, id) => base.object(runId, id),
    objects: async () => ({ items: [market, anchor], next_cursor: null }),
    relations: async () => ({ items: [geoRelation], next_cursor: null }),
    paths: (query) => base.paths(query),
    events: (query) => base.events(query),
    states: (query) => base.states(query),
    measurements: (query) => base.measurements(query),
    claims: (query) => base.claims(query),
    evidence: (query) => base.evidence(query),
    ddge: (query) => base.ddge(query),
    compare: (request) => base.compare(request),
  };
}

const fallback = new URLSearchParams(window.location.search).get("fallback") === "1";
const DATA_SOURCE = globeDataSource();

export function Harness() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  return (
    <main className="workbench">
      <GlobeLens
        dataSource={DATA_SOURCE}
        runId="run-a"
        comparisonRunId={null}
        selectedId={selectedId}
        time={5}
        onSelect={setSelectedId}
        {...(fallback ? { webglAvailable: () => false } : {})}
      />
    </main>
  );
}

const root = document.getElementById("root");
if (root === null) throw new Error("globe fixture root is missing");
createRoot(root).render(<Harness />);
