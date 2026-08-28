import axe from "axe-core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "../src/app/App";

describe("workbench client foundation", () => {
  it("renders its research purpose and passes an initial accessibility scan", async () => {
    const { container } = render(<App />);

    expect(
      screen.getByRole("heading", { name: "Ontology Research Workbench" }),
    ).toBeVisible();
    expect(screen.getByText("Client foundation ready")).toBeVisible();

    const accessibility = await axe.run(container, {
      rules: { "color-contrast": { enabled: false } },
    });
    expect(accessibility.violations).toEqual([]);
  });
});
