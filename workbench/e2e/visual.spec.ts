import { expect, test } from "@playwright/test";

test("preserves the research-workbench composition at desktop width", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/e2e/fixtures/app.html");
  await expect(page.getByRole("heading", { name: "Economic World Model" })).toBeVisible();
  await page
    .getByRole("navigation", { name: "Primary research workflows" })
    .getByRole("button", { name: "Economy" })
    .click();
  await page.locator(".world-lens").getByRole("button", { name: "Inspect Household 01" }).click();

  const explorer = await page.locator(".explorer").boundingBox();
  const lens = await page.locator(".lens-slot").boundingBox();
  const evidence = await page.locator(".inspector").boundingBox();
  expect(explorer).not.toBeNull();
  expect(lens).not.toBeNull();
  expect(evidence).not.toBeNull();
  expect(explorer!.x + explorer!.width).toBeLessThanOrEqual(lens!.x + 2);
  expect(lens!.x + lens!.width).toBeLessThanOrEqual(evidence!.x + 2);
  await test.info().attach("workbench-desktop", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
});

test("records a bounded semantic-scene frame sample", async ({ page }) => {
  await page.goto("/e2e/fixtures/app.html");
  await page
    .getByRole("navigation", { name: "Primary research workflows" })
    .getByRole("button", { name: "Graph" })
    .click();
  await page.getByRole("button", { name: "3D" }).click();
  await expect(
    page.getByRole("heading", { name: "Ontology graph" }),
  ).toBeVisible();
  const scene = page.getByRole("img", { name: "3D ontology scene" });
  const fallback = page.getByRole("heading", { name: "3D rendering unavailable" });
  await expect(scene.or(fallback)).toBeVisible();
  if ((await scene.count()) === 0) {
    return;
  }
  const canvas = scene.locator("canvas");
  await expect(canvas).toBeVisible();
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => resolve())));
  const frameDurations = await page.evaluate(
    () =>
      new Promise<number[]>((resolve) => {
        const samples: number[] = [];
        let previous = performance.now();
        const measure = (now: number) => {
          samples.push(now - previous);
          previous = now;
          if (samples.length === 12) resolve(samples.slice(1));
          else requestAnimationFrame(measure);
        };
        requestAnimationFrame(measure);
      }),
  );
  const ordered = frameDurations.toSorted((left, right) => left - right);
  const p95 = ordered[Math.floor((ordered.length - 1) * 0.95)]!;
  await test.info().attach("frame-sample.json", {
    body: JSON.stringify({ frameDurations, p95 }),
    contentType: "application/json",
  });
  expect(p95).toBeLessThan(250);
});
