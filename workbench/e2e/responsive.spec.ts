import { expect, test, type Page } from "@playwright/test";

const primary = [
  ["Overview", "Read the economy from evidence to consequence."],
  ["Economy", "Declared economic world"],
  ["Simulation", "Runtime episode"],
  ["Markets", "Market outcomes"],
  ["Learning", "Behavior-to-learning closure"],
  ["Evidence", "Evidence lens"],
] as const;

const advanced = [
  ["DDGE", "DDGE diagnostics"],
  ["Compare", "Comparison lens"],
  ["Lineage", "Lineage lens"],
  ["Graph", "Ontology graph"],
  ["Globe", "Explicit economic geography"],
] as const;

async function assertNoPageOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);
}

for (const viewport of [
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile-375", width: 375, height: 812 },
  { name: "mobile-320", width: 320, height: 800 },
]) {
  test(`keeps every investigation lens usable at ${viewport.name}`, async ({ browserName, page }) => {
    test.skip(browserName !== "chromium", "The complete responsive matrix runs once in Chromium.");
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/e2e/fixtures/app.html");

    for (const [label, heading] of primary) {
      await page.getByRole("button", { name: label, exact: true }).click();
      await expect(page.getByRole("heading", { name: heading })).toBeVisible();
      await assertNoPageOverflow(page);
    }

    const disclosure = page.locator(".advanced-nav");
    if ((await disclosure.getAttribute("open")) === null) {
      await page.getByText("Advanced analysis").click();
    }
    for (const [label, heading] of advanced) {
      await page.getByRole("button", { name: label, exact: true }).click();
      await expect(page.getByRole("heading", { name: heading })).toBeVisible();
      await assertNoPageOverflow(page);
    }
  });
}
