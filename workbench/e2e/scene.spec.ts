import { expect, test } from "@playwright/test";

test("renders the deterministic scene without continuous animation", async ({ page }) => {
  await page.goto("/e2e/fixtures/scene.html");
  await expect(page.getByRole("heading", { name: "Deterministic ontology scene" })).toBeVisible();
  await expect(page.getByText("semantic lane", { exact: true })).toBeVisible();
  const scene = page.getByRole("img", { name: "3D ontology scene" });
  const fallback = page.getByText("3D rendering unavailable");
  await expect(scene.or(fallback)).toBeVisible();
  await page.getByRole("button", { name: "Orthographic" }).click();
  await expect(page.getByRole("button", { name: "Orthographic" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

test("keeps selection available in the no-WebGL fallback", async ({ page }) => {
  await page.goto("/e2e/fixtures/scene.html?fallback=1");
  await expect(page.getByText("3D rendering unavailable")).toBeVisible();
  await page.getByRole("button", { name: "Select Household 01" }).click();
  await expect(page.getByRole("row", { name: /Household 01/ })).toHaveAttribute(
    "data-selected",
    "true",
  );
  await expect(page.getByRole("img", { name: "3D ontology scene" })).toHaveCount(0);
});
