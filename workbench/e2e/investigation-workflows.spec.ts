import { expect, test } from "@playwright/test";

const lenses = [
  ["Overview", "Read the economy from evidence to consequence."],
  ["Economy", "Declared economic world"],
  ["Simulation", "Runtime episode"],
  ["Markets", "Market outcomes"],
  ["Learning", "Behavior-to-learning closure"],
  ["Evidence", "Evidence lens"],
  ["DDGE", "DDGE diagnostics"],
  ["Compare", "Comparison lens"],
  ["Lineage", "Lineage lens"],
  ["Graph", "Ontology graph"],
  ["Globe", "Explicit economic geography"],
] as const;

test("executes every bounded researcher workflow from the persistent platform navigation", async ({ page }) => {
  await page.goto("/e2e/fixtures/app.html");
  await expect(
    page.getByRole("heading", { name: "Economic World Model" }),
  ).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Approved run" })).toHaveValue("run-a");
  const navigation = page.getByRole("navigation", { name: "Primary research workflows" });

  for (const [button, heading] of lenses) {
    await navigation.getByRole("button", { name: button, exact: true }).click();
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    await expect(navigation.getByRole("button", { name: button, exact: true })).toHaveAttribute(
      "aria-current",
      "page",
    );
  }

  await expect(page.getByText("Active projection", { exact: true })).toBeVisible();
});

test("keeps run, object, and evidence context synchronized", async ({ page }) => {
  await page.goto("/e2e/fixtures/app.html");
  const navigation = page.getByRole("navigation", { name: "Primary research workflows" });
  await navigation.getByRole("button", { name: "Economy", exact: true }).click();

  await page.locator(".world-lens").getByRole("button", { name: "Inspect Household 01" }).click();
  await expect(page.getByRole("region", { name: "Evidence inspector" })).toContainText(
    "Household 01",
  );
  const contextCommands = page.getByRole("region", { name: "Workspace context and commands" });
  await contextCommands.getByRole("button", { name: "Evidence", exact: true }).click();
  await expect(page.getByRole("region", { name: "Evidence inspector" })).toHaveCount(0);
  await contextCommands.getByRole("button", { name: "Evidence", exact: true }).click();
  await expect(page.getByRole("region", { name: "Evidence inspector" })).toBeVisible();

  await page.getByRole("combobox", { name: "Approved run" }).selectOption("run-b");
  await expect(page.locator(".provenance-strip strong")).toHaveText("Scalar model · v1 · run 2");
});
