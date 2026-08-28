import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { OntologyObjectContract } from "../src/data/InvestigationDataSource";
import { SceneLens } from "../src/lenses/scene/SceneLens";
import { SceneControls } from "../src/scene/SceneControls";
import type { CameraState } from "../src/state/investigation";
import { createFixtureDataSource } from "../src/testing/fixtures";

const object: OntologyObjectContract = {
  record_type: "ontology_object",
  ref: { record_type: "ontology_ref", id: "agent:1", kind: "agent" },
  layer: "economic_declaration",
  properties: { natural_key: "Household" },
  sources: [],
};

const camera: CameraState = {
  projection: "perspective",
  position: [12, 8, 16],
  target: [0, 0, 0],
};

describe("ontology scene interaction", () => {
  it("falls back to an accessible selectable table when WebGL is unavailable", async () => {
    const user = userEvent.setup();
    const dataSource = createFixtureDataSource();
    vi.spyOn(dataSource, "objects").mockResolvedValue({ items: [object], next_cursor: null });
    vi.spyOn(dataSource, "relations").mockResolvedValue({ items: [], next_cursor: null });
    const onSelect = vi.fn();

    render(
      <SceneLens
        dataSource={dataSource}
        runId="run-a"
        selectedId={null}
        camera={camera}
        onCameraChange={vi.fn()}
        onSelect={onSelect}
        webglAvailable={() => false}
      />,
    );

    expect(await screen.findByRole("heading", { name: "Ontology graph" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "3D" }));
    expect(await screen.findByText("3D rendering unavailable")).toBeVisible();
    expect(screen.getByText("No investigation data were discarded.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Select Household" }));
    expect(onSelect).toHaveBeenCalledWith("agent:1");
    expect(screen.queryByRole("img", { name: "3D ontology scene" })).not.toBeInTheDocument();
  });

  it("retains the legacy camera control contract for serialized scene state", async () => {
    const user = userEvent.setup();
    const onCameraChange = vi.fn();
    const onLayersChange = vi.fn();
    const onFocus = vi.fn();

    render(
      <SceneControls
        camera={camera}
        layers={["economic_declaration", "runtime_occurrence"]}
        visibleLayers={["economic_declaration", "runtime_occurrence"]}
        selectedId="agent:1"
        onCameraChange={onCameraChange}
        onLayersChange={onLayersChange}
        onFocus={onFocus}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Orthographic" }));
    expect(onCameraChange).toHaveBeenCalledWith(expect.objectContaining({ projection: "orthographic" }));
    await user.click(screen.getByRole("checkbox", { name: "runtime occurrence" }));
    expect(onLayersChange).toHaveBeenCalledWith(["economic_declaration"]);
    await user.click(screen.getByRole("button", { name: "Focus selection" }));
    expect(onFocus).toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Reset camera" }));
    expect(onCameraChange).toHaveBeenCalledWith(camera);
  });
});
