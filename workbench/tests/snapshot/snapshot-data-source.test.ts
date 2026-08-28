import { createHash } from "node:crypto";

import { beforeEach, describe, expect, it, vi } from "vitest";

import type { InvestigationSnapshot } from "../../src/data/SnapshotDataSource";
import { SnapshotDataSource } from "../../src/data/SnapshotDataSource";

const source = {
  record_type: "source_locator" as const,
  source_kind: "verified_run",
  source_id: "a".repeat(64),
  artifact_path: "run/events.jsonl",
  record_selector: "line:1",
  code_symbol: null,
  paper_anchor: null,
  payload_digest: "b".repeat(64),
};

const agent = {
  record_type: "ontology_object" as const,
  ref: { record_type: "ontology_ref" as const, id: "agent", kind: "agent" },
  layer: "economic_declaration",
  properties: { natural_key: "Agent" },
  sources: [source],
};
const event = {
  record_type: "ontology_object" as const,
  ref: {
    record_type: "ontology_ref" as const,
    id: "event",
    kind: "transition_event",
  },
  layer: "runtime_occurrence",
  properties: { event_sequence: 1, natural_key: "Event" },
  sources: [source],
};
const claim = {
  record_type: "ontology_object" as const,
  ref: { record_type: "ontology_ref" as const, id: "claim", kind: "claim" },
  layer: "research_evidence",
  properties: { evidence_classification: "verified_run_evidence" },
  sources: [source],
};
const evidence = {
  record_type: "ontology_object" as const,
  ref: {
    record_type: "ontology_ref" as const,
    id: "evidence",
    kind: "evidence_artifact",
  },
  layer: "research_evidence",
  properties: { evidence_classification: "verified_run_evidence" },
  sources: [source],
};
const relation = {
  record_type: "relation_assertion" as const,
  ref: {
    record_type: "ontology_ref" as const,
    id: "supports",
    kind: "relation_assertion",
  },
  relation_type: "SUPPORTS",
  source: evidence.ref,
  target: claim.ref,
  properties: {},
  sources: [source],
};
const measurement = {
  record_type: "measurement" as const,
  ref: {
    record_type: "ontology_ref" as const,
    id: "measurement",
    kind: "measurement",
  },
  subject: agent.ref,
  name: "price",
  value: 1,
  unit: "index",
  status: "observed",
  sample: {},
  uncertainty: {},
  sources: [source],
};

const payload: InvestigationSnapshot = {
  schema: "ewm.investigation.v1",
  source_run_hash: "a".repeat(20),
  source_identity_sha256: "a".repeat(64),
  source_bundle_sha256: "b".repeat(64),
  profile_identity: "ewm.fixture.v1",
  profile_digest: "c".repeat(64),
  integrity_level: "checksummed",
  projection_digest: "d".repeat(64),
  subset_digest: "e".repeat(64),
  selection: {
    object_ids: ["agent", "claim", "event", "evidence"],
    relation_ids: ["supports"],
    event_ids: ["event"],
    lens: "world",
    filters: { kinds: [], layers: [], query: "" },
    time_window: null,
    camera: null,
    layout: {},
  },
  runs: [
    {
      run_id: "run-a",
      source_run_hash: "a".repeat(20),
      profile_identity: "ewm.fixture.v1",
      integrity_level: "checksummed",
      projection_digest: "d".repeat(64),
      ontology_schema: "ewm.ontology.v1",
      coverage: [],
    },
  ],
  objects: [agent, claim, event, evidence],
  relations: [relation],
  measurements: [measurement],
  coverage: [],
  comparisons: [
    {
      comparison_id: "same-run",
      request: { left_run_id: "run-a", right_run_id: "run-a" },
      result: { comparable: true },
    },
  ],
  globe_geometry: null,
};

describe("SnapshotDataSource", () => {
  it("matches every bounded read/query contract without using the network", async () => {
    const network = vi.spyOn(globalThis, "fetch");
    const data = new SnapshotDataSource(payload);

    expect(await data.system()).toMatchObject({ mode: "offline-snapshot", run_count: 1 });
    expect(await data.runs()).toEqual(payload.runs);
    expect((await data.run("run-a")).projection_digest).toBe("d".repeat(64));
    expect((await data.object("run-a", "agent")).ref.kind).toBe("agent");
    expect((await data.objects({ runId: "run-a", kinds: ["agent"] })).items).toEqual([
      agent,
    ]);
    expect(
      (await data.relations({ runId: "run-a", incidentIds: ["claim"] })).items,
    ).toEqual([relation]);
    expect(
      await data.paths({
        runId: "run-a",
        startId: "evidence",
        targetId: "claim",
        maxDepth: 1,
      }),
    ).toMatchObject({ truncated: false, paths: [{ relations: [relation] }] });
    expect((await data.events({ runId: "run-a" })).items).toEqual([event]);
    expect((await data.states({ runId: "run-a" })).items).toEqual([]);
    expect((await data.measurements({ runId: "run-a", names: ["price"] })).items).toEqual([
      measurement,
    ]);
    expect((await data.claims({ runId: "run-a" })).items).toEqual([claim]);
    expect((await data.evidence({ runId: "run-a" })).items).toEqual([evidence]);
    expect((await data.ddge({ runId: "run-a" })).items).toEqual([]);
    expect(
      await data.compare({ left_run_id: "run-a", right_run_id: "run-a" }),
    ).toEqual(payload.comparisons[0]);
    expect(network).not.toHaveBeenCalled();
  });

  it("uses deterministic cursors and rejects access outside the selected run", async () => {
    const data = new SnapshotDataSource(payload);
    const first = await data.objects({ runId: "run-a", limit: 2 });
    const second = await data.objects({
      runId: "run-a",
      limit: 2,
      cursor: first.next_cursor ?? undefined,
    });

    expect(first.items).toEqual([agent, claim]);
    expect(second.items).toEqual([event, evidence]);
    await expect(data.run("missing")).rejects.toThrow("not available in this snapshot");
  });
});

describe("offline snapshot bootstrap", () => {
  beforeEach(() => {
    vi.resetModules();
    document.body.replaceChildren();
  });

  it("verifies canonical embedded bytes before exposing snapshot data", async () => {
    const canonical = JSON.stringify(payload);
    const template = document.createElement("template");
    template.id = "ewm-snapshot";
    template.dataset.sha256 = createHash("sha256").update(canonical).digest("hex");
    template.content.textContent = btoa(canonical);
    document.body.append(template);

    const { consumeSnapshot } = await import("../../src/snapshot/bootstrap");
    await expect(consumeSnapshot()).resolves.toEqual(payload);
    expect(document.getElementById("ewm-snapshot")).toBeNull();
  });

  it("removes corrupt material and reports an integrity failure", async () => {
    const template = document.createElement("template");
    template.id = "ewm-snapshot";
    template.dataset.sha256 = "0".repeat(64);
    template.content.textContent = btoa(JSON.stringify(payload));
    document.body.append(template);

    const { consumeSnapshot, SnapshotIntegrityError } = await import(
      "../../src/snapshot/bootstrap"
    );
    await expect(consumeSnapshot()).rejects.toBeInstanceOf(SnapshotIntegrityError);
    expect(document.getElementById("ewm-snapshot")).toBeNull();
  });
});
