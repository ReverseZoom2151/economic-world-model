import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  InvestigationProvider,
  initialInvestigationState,
  investigationReducer,
  parseInvestigationUrl,
  serializeInvestigationUrl,
  useInvestigation,
} from "../src/state/investigation";

describe("investigation state", () => {
  it("synchronizes every cross-lens selection through one typed reducer", () => {
    const actions = [
      { type: "select-run", runId: "run-a" },
      { type: "select-object", objectId: "ewm:object:a" },
      { type: "select-relation", relationId: "ewm:relation:a" },
      { type: "set-time-window", window: { start: 4, end: 12 } },
      { type: "set-comparison", comparison: { leftRunId: "run-a", rightRunId: "run-b" } },
      { type: "set-lens", lens: "evidence" },
      {
        type: "set-camera",
        camera: {
          projection: "orthographic",
          position: [2, 3, 5],
          target: [0, 1, 0],
        },
      },
      {
        type: "set-filters",
        filters: {
          kinds: ["claim"],
          layers: ["research_evidence"],
          query: "calibration",
        },
      },
    ] as const;

    const state = actions.reduce(investigationReducer, initialInvestigationState);

    expect(state.runId).toBe("run-a");
    expect(state.objectId).toBe("ewm:object:a");
    expect(state.relationId).toBe("ewm:relation:a");
    expect(state.timeWindow).toEqual({ start: 4, end: 12 });
    expect(state.comparison?.rightRunId).toBe("run-b");
    expect(state.lens).toBe("evidence");
    expect(state.camera?.projection).toBe("orthographic");
    expect(state.filters.kinds).toEqual(["claim"]);
  });

  it("round-trips shareable view state without accepting credentials", () => {
    const state = investigationReducer(initialInvestigationState, {
      type: "hydrate",
      state: {
        runId: "run-a",
        objectId: "ewm:object:a",
        lens: "runtime",
        timeWindow: { start: 1, end: 9 },
      },
    });
    const search = serializeInvestigationUrl(state);
    const parsed = parseInvestigationUrl(
      `${search}&token=query-secret&session_token=another-secret`,
    );

    expect(search).toContain("run=run-a");
    expect(search).not.toContain("token");
    expect(parsed.runId).toBe("run-a");
    expect(parsed.lens).toBe("runtime");
    expect(parsed).not.toHaveProperty("token");
    expect(parsed).not.toHaveProperty("session_token");
  });

  it("exposes reducer state and dispatch through one provider", () => {
    const { result } = renderHook(() => useInvestigation(), {
      wrapper: InvestigationProvider,
    });

    act(() => result.current.dispatch({ type: "set-lens", lens: "market" }));

    expect(result.current.state.lens).toBe("market");
  });
});
