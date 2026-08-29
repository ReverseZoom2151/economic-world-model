import { expect, test, type Page } from "@playwright/test";

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

async function openLens(page: Page, label: string) {
  const toggle = page.getByRole("button", { name: "Open navigation" });
  if (await toggle.isVisible()) await toggle.click();
  await page
    .getByRole("navigation", { name: "Primary research workflows" })
    .getByRole("button", { name: label, exact: true })
    .click();
}

async function assertNoPageOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);
}

for (const viewport of [
  { name: "desktop", width: 1440, height: 900 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile-375", width: 375, height: 812 },
  { name: "mobile-320", width: 320, height: 800 },
]) {
  test(`keeps every investigation lens usable at ${viewport.name}`, async ({ browserName, page }) => {
    test.skip(browserName !== "chromium", "The complete responsive matrix runs once in Chromium.");
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/e2e/fixtures/app.html");

    for (const [label, heading] of lenses) {
      await openLens(page, label);
      await expect(page.getByRole("heading", { name: heading })).toBeVisible();
      await assertNoPageOverflow(page);
    }

    await openLens(page, "Economy");
    const context = page.getByRole("region", { name: "Workspace context and commands" });
    const objects = context.getByRole("button", { name: "Objects", exact: true });
    await expect(page.getByRole("region", { name: "Object explorer" })).toBeVisible();
    await objects.click();
    await expect(page.getByRole("region", { name: "Object explorer" })).toHaveCount(0);
    await objects.click();
    const explorer = page.getByRole("region", { name: "Object explorer" });
    await expect(explorer).toBeVisible();
    await explorer.getByRole("button", { name: /Household 01/ }).click();
    const evidence = context.getByRole("button", { name: "Evidence", exact: true });
    await expect(page.getByRole("region", { name: "Evidence inspector" })).toBeVisible();
    await evidence.click();
    await expect(page.getByRole("region", { name: "Evidence inspector" })).toHaveCount(0);
    await evidence.click();
    await expect(page.getByRole("region", { name: "Evidence inspector" })).toBeVisible();
    await assertNoPageOverflow(page);

    if (viewport.width <= 1100) {
      await page.getByRole("button", { name: "Open navigation" }).click();
      await expect(page.locator(".platform-brand__close")).toBeVisible();
      await page.locator(".platform-brand__close").click();
      await expect(page.getByRole("button", { name: "Open navigation" })).toBeVisible();
    }
  });
}
