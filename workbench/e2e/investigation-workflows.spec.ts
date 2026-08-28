import { expect, test } from "@playwright/test";

const lenses = [
  ["World", "Declared economic world"],
  ["Runtime", "Runtime episode"],
  ["Learning", "Behavior-to-learning closure"],
  ["DDGE", "DDGE diagnostics"],
  ["Compare", "Comparison lens"],
  ["Evidence", "Evidence lens"],
  ["Lineage", "Lineage lens"],
] as const;

test("executes the eight bounded researcher workflows", async ({ page }) => {
  await page.goto("/e2e/fixtures/app.html");
  await expect(
    page.getByRole("heading", { name: "Ontology Research Workbench" }),
  ).toBeVisible();
  await expect(page.getByLabel("Approved run")).toHaveValue("run-a");

  for (const [button, heading] of lenses) {
    await page.getByRole("button", { name: button, exact: true }).click();
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
  }

  await expect(page.getByText("Active projection", { exact: true })).toBeVisible();
});

test("keeps semantic scene and explicit-geography workflows available", async ({ page }) => {
  await page.goto("/e2e/fixtures/app.html");
  await page.getByRole("button", { name: "3D Scene" }).click();
  await expect(
    page.getByRole("heading", { name: "Deterministic ontology scene" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Globe" }).click();
  await expect(
    page.getByRole("heading", { name: "Explicit economic geography" }),
  ).toBeVisible();
  await expect(page.getByText("No explicit geography is available.")).toBeVisible();
});
