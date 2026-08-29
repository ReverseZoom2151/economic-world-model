import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DdgeLens } from "../src/lenses/ddge/DdgeLens";
import type {
  OntologyObjectContract,
  RelationContract,
} from "../src/data/InvestigationDataSource";

function object(
  id: string,
  kind: string,
  properties: Readonly<Record<string, unknown>>,
): OntologyObjectContract {
  return {
    record_type: "ontology_object",
    ref: { record_type: "ontology_ref", id, kind },
    layer: "learning_equilibrium",
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
      id: `ewm:test:relation:${type}:${source.ref.id}:${target.ref.id}`,
      kind: "relation_assertion",
    },
    relation_type: type,
    source: source.ref,
    target: target.ref,
    properties: {},
    sources: [],
  };
}

function candidate(id: string, status: string, theta: number): OntologyObjectContract {
  return object(id, "ddge_candidate", {
    theta,
    status,
    stable: theta < 1,
    basin: theta < 1 ? "low initialization" : "high initialization",
    initialization: theta < 1 ? 0.1 : 2.0,
  });
}

function residual(
  id: string,
  value: ReadonlyArray<number>,
  norm: number,
): OntologyObjectContract {
  return object(id, "residual", {
    value,
    norm,
    tolerance: 1e-8,
    solver: "brentq_and_multistart_fixed_point_iteration",
    stopping_rule: "residual_norm <= tolerance or 1000 iterations",
    status: norm <= 1e-8 ? "within_tolerance" : "outside_tolerance",
  });
}

describe("DdgeLens", () => {
  it("retains all candidates, residual forms, selector, basins, stability, and certificate", () => {
    const correspondence = object("ewm:test:correspondence", "inner_equilibrium", {
      selector: "retain_all_independently_bracketed_roots",
      candidate_count: 2,
      status: "numerically_validated",
    });
    const first = candidate("ewm:test:candidate:low", "numerically_validated", 0.42);
    const second = candidate("ewm:test:candidate:high", "candidate", 1.25);
    const scalar = residual("ewm:test:residual:scalar", [2e-10], 2e-10);
    const vector = residual("ewm:test:residual:vector", [0.02, -0.01], 0.02);
    const certificate = object("ewm:test:certificate:contraction", "theorem_certificate", {
      certificate_kind: "contraction_distance_bound",
      assumptions: ["operator is a contraction", "modulus is 0.6"],
      bound: 5e-10,
      bound_unit: "parameter distance",
      status: "certified",
    });
    const relations = [
      relation("HAS_CANDIDATE", correspondence, first),
      relation("HAS_CANDIDATE", correspondence, second),
      relation("HAS_RESIDUAL", first, scalar),
      relation("HAS_RESIDUAL", second, vector),
      relation("CERTIFIES", certificate, first),
    ];

    render(
      <DdgeLens
        objects={[correspondence, first, second, scalar, vector, certificate]}
        relations={relations}
      />,
    );

    expect(screen.getByRole("heading", { name: "DDGE diagnostics" })).toBeVisible();
    expect(screen.getByText("Retain all independently bracketed roots")).toBeVisible();
    expect(screen.getByText("retain_all_independently_bracketed_roots")).toBeInTheDocument();
    expect(
      screen.getAllByText(/Ddge Candidate/, { selector: ".candidate-basins strong" }),
    ).toHaveLength(2);
    expect(screen.getByText("[2e-10]")).toBeVisible();
    expect(screen.getByText("[0.02, −0.01]")).toBeVisible();
    expect(screen.getAllByText("brentq and multistart fixed point iteration")).toHaveLength(2);
    expect(screen.getByText("low initialization")).toBeVisible();
    expect(screen.getByText("Stable")).toBeVisible();
    expect(screen.getByText("5e-10 parameter distance")).toBeVisible();
    expect(screen.getByText("operator is a contraction")).toBeVisible();
  });

  it.each(["observed", "candidate", "numerically_validated", "certified"])(
    "renders the %s status without promotion",
    (status) => {
      render(<DdgeLens objects={[candidate(`ewm:test:${status}`, status, 0.5)]} relations={[]} />);

      expect(screen.getByText(status.replaceAll("_", " "))).toBeVisible();
    },
  );

  it("does not turn an uncertified small residual into a bound", () => {
    const point = candidate("ewm:test:candidate:uncertified", "numerically_validated", 0.2);
    const small = residual("ewm:test:residual:small", [1e-12], 1e-12);

    render(
      <DdgeLens
        objects={[point, small]}
        relations={[relation("HAS_RESIDUAL", point, small)]}
      />,
    );

    expect(screen.getByText("No linked theorem certificate authorizes a bound.")).toBeVisible();
    expect(screen.queryByText(/Distance bound/i)).not.toBeInTheDocument();
    expect(screen.getByText("No preferred candidate selected")).toBeVisible();
  });
});
