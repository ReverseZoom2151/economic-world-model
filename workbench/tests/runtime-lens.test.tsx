import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RuntimeLens } from "../src/lenses/runtime/RuntimeLens";
import { orderedRuntimeEvents } from "../src/visuals/runtime/model";
import type { OntologyObjectContract } from "../src/data/InvestigationDataSource";

function event(sequence: number, kind: string): OntologyObjectContract {
  return {
    record_type: "ontology_object",
    ref: {
      record_type: "ontology_ref",
      id: `ewm:test:event:${sequence}`,
      kind,
    },
    layer: "runtime_occurrence",
    properties: {
      natural_key: `${kind} ${sequence}`,
      context: { event_sequence: sequence, time: sequence * 0.5 },
    },
    sources: [],
  };
}

describe("RuntimeLens", () => {
  it("orders events by declared sequence without mutating source order", () => {
    const source = [event(7, "settlement_event"), event(2, "action_event")];

    expect(orderedRuntimeEvents(source).map((item) => item.ref.id)).toEqual([
      "ewm:test:event:2",
      "ewm:test:event:7",
    ]);
    expect(source[0]?.ref.id).toBe("ewm:test:event:7");
  });

  it("brushes an explicit event window and preserves event type labels", () => {
    const onSelect = vi.fn();
    render(
      <RuntimeLens
        events={[
          event(1, "state_observation"),
          event(2, "action_event"),
          event(3, "settlement_event"),
        ]}
        relations={[]}
        timeWindow={{ start: 2, end: 3 }}
        selectedId={null}
        onSelect={onSelect}
      />,
    );

    expect(screen.getByRole("heading", { name: "Runtime episode" })).toBeVisible();
    expect(screen.queryByText("state observation 1")).not.toBeInTheDocument();
    expect(screen.getByText("action event 2")).toBeVisible();
    expect(screen.getByText("settlement event 3")).toBeVisible();
    expect(screen.getByText("Sequence 2–3")).toBeVisible();
  });
});
