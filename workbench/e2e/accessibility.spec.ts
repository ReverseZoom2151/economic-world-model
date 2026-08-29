import { createRequire } from "node:module";

import { expect, test } from "@playwright/test";

const require = createRequire(import.meta.url);

test("has no serious automated accessibility violations", async ({ page }) => {
  await page.goto("/e2e/fixtures/app.html");
  await expect(page.getByRole("heading", { name: "Economic World Model" })).toBeVisible();
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  const violations = await page.evaluate(async () => {
    const axe = (window as typeof window & {
      axe: { run: () => Promise<{ violations: Array<{ impact: string | null; id: string }> }> };
    }).axe;
    const result = await axe.run();
    return result.violations.filter(
      (violation) => violation.impact === "serious" || violation.impact === "critical",
    );
  });

  expect(violations).toEqual([]);
});

test("supports keyboard navigation and reduced motion", async ({ browser }) => {
  const context = await browser.newContext({ reducedMotion: "reduce" });
  const page = await context.newPage();
  await page.goto("/e2e/fixtures/app.html");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to active analysis" })).toBeFocused();
  const overview = page.getByRole("button", { name: "Overview", exact: true });
  for (let attempt = 0; attempt < 3 && !(await overview.evaluate((element) => element === document.activeElement)); attempt += 1) {
    await page.keyboard.press("Tab");
  }
  await expect(overview).toBeFocused();
  const motion = await overview.evaluate(
    (element) => {
      const milliseconds = (value: string) =>
        value.endsWith("ms") ? Number.parseFloat(value) : Number.parseFloat(value) * 1_000;
      return {
        animation: milliseconds(getComputedStyle(element).animationDuration),
        transition: milliseconds(getComputedStyle(element).transitionDuration),
      };
    },
  );
  expect(motion.animation).toBeLessThanOrEqual(0.001);
  expect(motion.transition).toBeLessThanOrEqual(0.001);
  await context.close();
});

test("keeps the closed mobile navigation out of the keyboard order", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/e2e/fixtures/app.html");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to active analysis" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Open navigation" })).toBeFocused();
});

test("moves focus into the mobile navigation and restores it on Escape", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/e2e/fixtures/app.html");
  const toggle = page.getByRole("button", { name: "Open navigation" });
  await toggle.click();
  await expect(
    page.getByRole("complementary", { name: "EWM platform navigation" })
      .getByRole("button", { name: "Close navigation" }),
  ).toBeFocused();
  await expect(page.locator("main")).toHaveAttribute("inert", "");
  await page.keyboard.press("Escape");
  await expect(toggle).toBeFocused();
  await expect(page.locator("main")).not.toHaveAttribute("inert", "");
});
