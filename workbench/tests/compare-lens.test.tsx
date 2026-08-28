import { render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ComparisonResultContract } from "../src/data/InvestigationDataSource";
import { CompareLens } from "../src/lenses/compare/CompareLens";
import { createFixtureDataSource } from "../src/testing/fixtures";

const ACCEPTED: ComparisonResultContract = {
  comparison_id: "accepted-comparison",
  request: { left_run_id: "run-a", right_run_id: "run-b" },
  result: {
    preflight: { compatible: true, issues: [], left: {}, right: {} },
    plan: {
      entries: [
        {
          comparison_key: "price@paired-sample",
          left_measurement: { id: "measurement:left", kind: "measurement" },
          right_measurement: { id: "measurement:right", kind: "measurement" },
        },
      ],
      unaligned_measurement_ids: [],
    },
    aligned: [
      {
        comparison_key: "price@paired-sample",
        estimand_identity: "price",
        sample_identity: "paired-sample-v1",
        estimator_identity: "paired-mean-v1",
        hypothesis_id: "price",
        unit: "index",
        left_name: "baseline price",
        right_name: "policy price",
        left_value: 1,
        right_value: 1.25,
        left_intervention: { family: "policy", level: "baseline" },
        right_intervention: { family: "policy", level: "selective" },
        pairing: { method: "common_random_numbers", seeds: [7, 8] },
        multiplicity: { method: "holm", alpha: 0.05, family: ["price"] },
      },
    ],
    unaligned: [],
  },
};

describe("comparison lens", () => {
  it("renders compatibility preflight before aligned values and preserves paired design metadata", async () => {
    const source = createFixtureDataSource();
    vi.spyOn(source, "compare").mockResolvedValue(ACCEPTED);

    render(<CompareLens dataSource={source} activeRunId="run-a" />);

    const preflight = await screen.findByRole("region", { name: "Comparison preflight" });
    const aligned = screen.getByRole("region", { name: "Aligned comparison" });
    expect(preflight.compareDocumentPosition(aligned) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(within(preflight).getByText("Compatible")).toBeVisible();
    expect(within(aligned).getByText("paired-sample-v1")).toBeVisible();
    expect(within(aligned).getByText("common_random_numbers")).toBeVisible();
    expect(within(aligned).getByText("Seeds 7, 8")).toBeVisible();
    expect(within(aligned).getByText("holm · α 0.05")).toBeVisible();
    expect(within(aligned).getByText("index")).toBeVisible();
  });

  it("shows every blocking mismatch and withholds aligned output", async () => {
    const source = createFixtureDataSource();
    vi.spyOn(source, "compare").mockResolvedValue({
      comparison_id: "rejected-comparison",
      result: {
        preflight: {
          compatible: false,
          issues: [
            {
              code: "protocol_identity_mismatch",
              scope: "run",
              message: "protocol identities differ",
              left: "protocol:a",
              right: "protocol:b",
              blocking: true,
            },
            {
              code: "paired_seed_mismatch",
              scope: "run",
              message: "paired seeds differ",
              left: [7, 8],
              right: [7, 9],
              blocking: true,
            },
          ],
          left: {},
          right: {},
        },
        plan: { entries: [], unaligned_measurement_ids: ["left", "right"] },
        aligned: [],
        unaligned: [
          {
            side: "left",
            measurement_id: "left",
            comparison_key: "price",
            reason_code: "preflight_failed",
            reason: "run preflight failed",
          },
        ],
      },
    });

    render(<CompareLens dataSource={source} activeRunId="run-a" />);

    expect(await screen.findByText("Incompatible")).toBeVisible();
    expect(screen.getByText("protocol identities differ")).toBeVisible();
    expect(screen.getByText("paired seeds differ")).toBeVisible();
    expect(screen.getByText("Aligned values withheld")).toBeVisible();
    expect(screen.queryByText("No measurable difference")).not.toBeInTheDocument();
  });

  it("states when a comparison is unsupported because only one run exists", async () => {
    const source = createFixtureDataSource({
      runs: [
        {
          run_id: "run-a",
          source_run_hash: "1".repeat(20),
          profile_identity: "ewm.scalar.v1",
          integrity_level: "checksummed",
          projection_digest: "2".repeat(64),
          ontology_schema: "ewm.ontology.v1",
        },
      ],
    });
    const compare = vi.spyOn(source, "compare");

    render(<CompareLens dataSource={source} activeRunId="run-a" />);

    expect(await screen.findByText("Comparison unavailable")).toBeVisible();
    expect(compare).not.toHaveBeenCalled();
  });

  it("never invents scenario or protocol versions while loading", async () => {
    const source = createFixtureDataSource();
    let resolve: (value: ComparisonResultContract) => void = () => undefined;
    vi.spyOn(source, "compare").mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    );

    render(<CompareLens dataSource={source} activeRunId="run-a" />);

    expect(await screen.findByText("Running compatibility preflight…")).toBeVisible();
    expect(screen.queryByText(/scenario v/i)).not.toBeInTheDocument();
    resolve(ACCEPTED);
    await waitFor(() => expect(screen.getByText("Compatible")).toBeVisible());
  });
});
