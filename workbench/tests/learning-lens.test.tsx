import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LearningLens } from "../src/lenses/learning/LearningLens";
import type {
  CoverageContract,
  OntologyObjectContract,
  RelationContract,
} from "../src/data/InvestigationDataSource";

function object(
  id: string,
  kind: string,
  properties: Readonly<Record<string, unknown>> = {},
): OntologyObjectContract {
  return {
    record_type: "ontology_object",
    ref: { record_type: "ontology_ref", id, kind },
    layer: kind === "action_occurrence" || kind === "generated_datum"
      ? "runtime_occurrence"
      : "learning_equilibrium",
    properties,
    sources: [],
  };
}

function relation(
  type: string,
  source: OntologyObjectContract,
  target: OntologyObjectContract,
): RelationContract {
  return {
    record_type: "relation_assertion",
    ref: {
      record_type: "ontology_ref",
      id: `ewm:test:relation:${type.toLowerCase()}:${source.ref.id}:${target.ref.id}`,
      kind: "relation_assertion",
    },
    relation_type: type,
    source: source.ref,
    target: target.ref,
    properties: {},
    sources: [],
  };
}

const gap: CoverageContract = {
  record_type: "coverage_entry",
  source: {
    record_type: "source_locator",
    source_kind: "ontology_adapter",
    source_id: "forecasting-profile",
    artifact_path: null,
    record_selector: null,
    code_symbol: null,
    paper_anchor: null,
    payload_digest: "a".repeat(64),
  },
  field: "adapter.forecasting.raw_behavior_data",
  status: "unavailable",
  targets: [],
  reason: "the sealed summary retains fixed-point statistics, not simulated microdata",
};

describe("LearningLens", () => {
  it("shows exact dataset membership, training identity, deployment, and closure", () => {
    const parameter = object("ewm:test:parameter:theta-v1", "parameter_version", {
      coefficient_name: "forecast",
      value: 0.42,
      deployment_status: "candidate",
    });
    const action = object("ewm:test:action:1", "action_occurrence");
    const firstDatum = object("ewm:test:datum:1", "generated_datum");
    const secondDatum = object("ewm:test:datum:2", "generated_datum");
    const dataset = object("ewm:test:dataset:retained", "dataset", {
      dataset_kind: "retained_fixed_point_summary_set",
    });
    const training = object("ewm:test:training:population", "training_run", {
      learner: "population_mean",
      status: "adapter_reconstructed_from_summary",
      sample_size: 1000,
    });
    const model = object("ewm:test:model:forecast-v1", "model_version", {
      model_family: "population_mean_forecaster",
    });
    const objects = [parameter, action, firstDatum, secondDatum, dataset, training, model];
    const relations = [
      relation("GENERATES", action, firstDatum),
      relation("GENERATES", action, secondDatum),
      relation("INCLUDED_IN", firstDatum, dataset),
      relation("INCLUDED_IN", secondDatum, dataset),
      relation("TRAINS", dataset, training),
      relation("PRODUCES", training, model),
      relation("DEPLOYS", model, parameter),
    ];

    render(<LearningLens objects={objects} relations={relations} coverage={[gap]} />);

    expect(screen.getByRole("heading", { name: "Behavior-to-learning closure" })).toBeVisible();
    expect(screen.getByText("2 included records")).toBeVisible();
    expect(screen.getByText("population mean")).toBeVisible();
    expect(screen.getByText("adapter reconstructed from summary")).toBeVisible();
    expect(screen.getByText("Parameter Version · Theta V1")).toBeVisible();
    expect(screen.getByText("ewm:test:parameter:theta-v1")).toBeInTheDocument();
    expect(screen.getByText("Closure linked")).toBeVisible();
  });

  it("preserves an unavailable stage and its coverage reason", () => {
    render(<LearningLens objects={[]} relations={[]} coverage={[gap]} />);

    expect(screen.getByText("Dataset stage unavailable")).toBeVisible();
    expect(
      screen.getByText("the sealed summary retains fixed-point statistics, not simulated microdata"),
    ).toBeVisible();
    expect(screen.getByText("Closure incomplete")).toBeVisible();
  });
});
