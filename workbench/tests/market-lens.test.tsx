import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MarketLens } from "../src/lenses/market/MarketLens";
import { buildMarketSpec } from "../src/visuals/market/spec";
import type {
  MeasurementContract,
  OntologyObjectContract,
} from "../src/data/InvestigationDataSource";

function measurement(): MeasurementContract {
  return {
    record_type: "measurement",
    ref: {
      record_type: "ontology_ref",
      id: "ewm:test:measurement:price",
      kind: "measurement",
    },
    subject: {
      record_type: "ontology_ref",
      id: "ewm:test:market:goods",
      kind: "market",
    },
    name: "Clearing price",
    value: 1.25,
    unit: "index points",
    status: "observed",
    sample: { sample_size: 32, estimator: "paired mean" },
    uncertainty: { method: "paired standard error", value: 0.08 },
    sources: [
      {
        record_type: "source_locator",
        source_kind: "verified_run",
        source_id: "run-a",
        artifact_path: "metrics.json",
        record_selector: "clearing_price",
        code_symbol: null,
        paper_anchor: null,
        payload_digest: "a".repeat(64),
      },
    ],
  };
}

function rejection(): OntologyObjectContract {
  return {
    record_type: "ontology_object",
    ref: {
      record_type: "ontology_ref",
      id: "ewm:test:event:rejection",
      kind: "market_rejection",
    },
    layer: "runtime_occurrence",
    properties: { natural_key: "Order 17", reason: "budget constraint" },
    sources: [],
  };
}

describe("MarketLens", () => {
  it("rejects chart inputs that omit scientific metadata", () => {
    const incomplete = { ...measurement(), uncertainty: {} };

    expect(() => buildMarketSpec([incomplete])).toThrow(/uncertainty/i);
  });

  it("shows units, sample, uncertainty, source, and market rejections", () => {
    render(<MarketLens measurements={[measurement()]} rejections={[rejection()]} />);

    expect(screen.getByRole("heading", { name: "Market outcomes" })).toBeVisible();
    expect(screen.getByText("index points")).toBeVisible();
    expect(screen.getByText("n = 32")).toBeVisible();
    expect(screen.getByText("paired standard error · 0.08")).toBeVisible();
    expect(screen.getByText("verified run · run-a")).toBeVisible();
    expect(screen.getByText("budget constraint")).toBeVisible();
  });

  it("uses a textual sparse-data fallback instead of interpolating a chart", () => {
    render(<MarketLens measurements={[]} rejections={[]} />);

    expect(screen.getByText("No market measurements were projected for this run.")).toBeVisible();
    expect(screen.queryByTestId("market-chart")).not.toBeInTheDocument();
  });
});
