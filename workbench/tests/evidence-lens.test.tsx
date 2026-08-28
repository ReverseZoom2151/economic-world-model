import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { OntologyObjectContract, RelationContract } from "../src/data/InvestigationDataSource";
import { EvidenceLens } from "../src/lenses/evidence/EvidenceLens";
import { createFixtureDataSource } from "../src/testing/fixtures";

const ref = (id: string, kind: string) => ({ record_type: "ontology_ref" as const, id, kind });

const claim: OntologyObjectContract = {
  record_type: "ontology_object",
  ref: ref("claim:1", "claim"),
  layer: "research_evidence",
  properties: {
    natural_key: "Market clearing claim",
    evidence_classification: "verified_run_evidence",
    limitations: ["Synthetic population only", "Two-period horizon"],
  },
  sources: [
    {
      record_type: "source_locator",
      source_kind: "verified_run",
      source_id: "run:42",
      artifact_path: "reports/claims.jsonl",
      record_selector: "line:4",
      code_symbol: null,
      paper_anchor: null,
      payload_digest: "a".repeat(64),
    },
  ],
};

const evidence: OntologyObjectContract = {
  record_type: "ontology_object",
  ref: ref("evidence:1", "evidence_artifact"),
  layer: "research_evidence",
  properties: {
    natural_key: "Paired experiment",
    evidence_classification: "verified_run_evidence",
    source_file_status: "missing",
  },
  sources: [
    {
      record_type: "source_locator",
      source_kind: "verified_run",
      source_id: "run:42",
      artifact_path: "/home/researcher/secret/results.json",
      record_selector: null,
      code_symbol: null,
      paper_anchor: "experiment:paired",
      payload_digest: "b".repeat(64),
    },
    {
      record_type: "source_locator",
      source_kind: "paper",
      source_id: "paper:2",
      artifact_path: null,
      record_selector: null,
      code_symbol: null,
      paper_anchor: "section:4",
      payload_digest: null,
    },
  ],
};

const supports: RelationContract = {
  record_type: "relation_assertion",
  ref: ref("relation:supports", "relation_assertion"),
  relation_type: "SUPPORTS",
  source: evidence.ref,
  target: claim.ref,
  properties: {},
  sources: evidence.sources,
};

describe("evidence lens", () => {
  it("traverses claims to evidence while preserving classification, limitations, and safe locators", async () => {
    const source = createFixtureDataSource();
    vi.spyOn(source, "claims").mockResolvedValue({ items: [claim], next_cursor: null });
    vi.spyOn(source, "evidence").mockResolvedValue({ items: [evidence], next_cursor: null });
    vi.spyOn(source, "relations").mockResolvedValue({ items: [supports], next_cursor: null });

    render(<EvidenceLens dataSource={source} runId="run-a" />);

    const audit = await screen.findByRole("region", { name: "Claim audit" });
    expect(within(audit).getByText("Market clearing claim")).toBeVisible();
    expect(within(audit).getAllByText("verified run evidence").length).toBeGreaterThan(0);
    expect(
      within(audit).getAllByText("◇", { selector: "span" })[0],
    ).toHaveAttribute("data-status-shape", "verified_run_evidence");
    expect(within(audit).getByText("Synthetic population only")).toBeVisible();
    expect(within(audit).getByText("Two-period horizon")).toBeVisible();
    expect(within(audit).getByText("reports/claims.jsonl")).toBeVisible();
    expect(within(audit).getByText("[redacted unsafe path]")).toBeVisible();
    expect(within(audit).queryByText("/home/researcher/secret/results.json")).not.toBeInTheDocument();
    expect(within(audit).getByText("Source file reported missing.")).toBeVisible();
    expect(within(audit).getByText("No artifact path recorded")).toBeVisible();
  });

  it("does not imply support when evidence or SUPPORTS relations are absent", async () => {
    const source = createFixtureDataSource();
    vi.spyOn(source, "claims").mockResolvedValue({ items: [claim], next_cursor: null });
    vi.spyOn(source, "evidence").mockResolvedValue({ items: [], next_cursor: null });
    vi.spyOn(source, "relations").mockResolvedValue({ items: [], next_cursor: null });

    render(<EvidenceLens dataSource={source} runId="run-a" />);

    expect(await screen.findByText("No supporting evidence is linked to this claim.")).toBeVisible();
    expect(screen.getByText("Support status: unsupported")).toBeVisible();
  });
});
