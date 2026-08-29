import { expect, test } from "@playwright/test";

const lenses = [
  ["Economy", "Declared economic world"],
  ["Simulation", "Runtime episode"],
  ["Learning", "Behavior-to-learning closure"],
  ["DDGE", "DDGE diagnostics"],
  ["Compare", "Comparison lens"],
  ["Evidence", "Evidence lens"],
  ["Lineage", "Lineage lens"],
] as const;

const advanced = new Set(["DDGE", "Compare", "Lineage"]);

async function openAdvanced(page: import("@playwright/test").Page) {
  const details = page.locator(".advanced-nav");
  if ((await details.getAttribute("open")) === null) {
    await page.getByText("Advanced analysis").click();
  }
}

test("executes the eight bounded researcher workflows", async ({ page }) => {
  await page.goto("/e2e/fixtures/app.html");
  await expect(
    page.getByRole("heading", { name: "Ontology Research Workbench" }),
  ).toBeVisible();
  await expect(page.getByLabel("Approved run")).toHaveValue("run-a");

  for (const [button, heading] of lenses) {
    if (advanced.has(button)) await openAdvanced(page);
    await page.getByRole("button", { name: button, exact: true }).click();
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
  }

  await expect(page.getByText("Active projection", { exact: true })).toBeVisible();
});

test("keeps semantic scene and explicit-geography workflows available", async ({ page }) => {
  await page.goto("/e2e/fixtures/app.html");
  await openAdvanced(page);
  await page.getByRole("button", { name: "Graph" }).click();
  await expect(
    page.getByRole("heading", { name: "Ontology graph" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Globe" }).click();
  await expect(
    page.getByRole("heading", { name: "Explicit economic geography" }),
  ).toBeVisible();
  await expect(page.getByText("No explicit geography is available.")).toBeVisible();
});
