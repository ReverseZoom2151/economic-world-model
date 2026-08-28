import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "../src/app/App";
import { createFixtureDataSource, deferredDataSource } from "../src/testing/fixtures";

describe("investigation shell", () => {
  it("starts from a run overview and reveals contextual tools inside researcher workflows", async () => {
    const user = userEvent.setup();
    render(<App dataSource={createFixtureDataSource()} />);

    expect(await screen.findByRole("heading", { name: "Ontology Research Workbench" })).toBeVisible();
    expect(screen.getByRole("navigation", { name: "Primary research workflows" })).toBeVisible();
    expect(
      await screen.findByRole("heading", { name: "Read the economy from evidence to consequence." }),
    ).toBeVisible();
    expect(screen.queryByRole("region", { name: "Object explorer" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Event timeline" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Understand the world" }));
    expect(screen.getByRole("region", { name: "Object explorer" })).toBeVisible();
    expect(screen.queryByRole("region", { name: "Evidence inspector" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Inspect Household 01" }));
    expect(await screen.findByRole("region", { name: "Evidence inspector" })).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Learning" }));
    expect(
      await screen.findByRole("heading", { name: "Behavior-to-learning closure" }),
    ).toBeVisible();
    await user.click(screen.getByText("Advanced analysis"));
    await user.click(screen.getByRole("button", { name: "DDGE" }));
    expect(await screen.findByRole("heading", { name: "DDGE diagnostics" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Graph" }));
    expect(
      await screen.findByRole("heading", { name: "Ontology graph" }),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Evidence" }));
    expect(screen.getByRole("heading", { name: "Evidence lens" })).toBeVisible();

    await user.selectOptions(screen.getByRole("combobox", { name: "Approved run" }), "run-b");
    expect(screen.getByText("run-b", { selector: "strong" })).toBeVisible();
  });

  it("renders loading and empty states without inventing records", async () => {
    const deferred = deferredDataSource();
    const view = render(<App dataSource={deferred.source} />);

    expect(screen.getByText("Loading approved runs…")).toBeVisible();
    deferred.resolve({ status: "ready", runs: [] });
    expect(await screen.findByText("No approved runs are available.")).toBeVisible();

    view.unmount();
  });

  it.each([
    ["partial", "Projection coverage is partial."],
    ["unsupported", "This projection profile is not supported by the workbench."],
    ["integrity_error", "Projection integrity verification failed."],
  ] as const)("renders the %s state explicitly", async (status, message) => {
    render(<App dataSource={createFixtureDataSource({ status })} />);

    await waitFor(() => expect(screen.getByText(message)).toBeVisible());
  });
});
