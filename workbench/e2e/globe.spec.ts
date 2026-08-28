import { expect, test } from "@playwright/test";

test("renders only explicit economic geography from bundled assets", async ({ page }) => {
  await page.goto("/e2e/fixtures/globe.html");
  await expect(page.getByRole("heading", { name: "Explicit economic geography" })).toBeVisible();
  await expect(page.getByText("1 explicitly anchored objects")).toBeVisible();
  const globe = page.getByRole("img", { name: "3D economic globe with explicit anchors" });
  const accessibleEquivalent = page.getByText("Accessible 2D equivalent");
  await expect(globe.or(accessibleEquivalent)).toBeVisible();
  await expect(page.getByText("Bucharest credit market")).toBeVisible();
});

test("keeps coordinate evidence selectable without WebGL", async ({ page }) => {
  await page.goto("/e2e/fixtures/globe.html?fallback=1");
  await expect(page.getByText("Accessible 2D equivalent")).toBeVisible();
  const select = page.getByRole("button", { name: "Select Bucharest credit market" });
  await select.click();
  await expect(select).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("img", { name: "3D economic globe with explicit anchors" })).toHaveCount(0);
});
