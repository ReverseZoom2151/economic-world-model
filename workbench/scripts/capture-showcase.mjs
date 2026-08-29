import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import process from "node:process";
import { execFileSync } from "node:child_process";

import { chromium } from "@playwright/test";

const baseUrl = process.argv[2] ?? "http://127.0.0.1:8765";
const outputDir = resolve(process.argv[3] ?? "../docs/assets/workbench");
mkdirSync(outputDir, { recursive: true });

const browser = await chromium.launch({
  headless: true,
  args: ["--enable-webgl", "--ignore-gpu-blocklist", "--use-angle=swiftshader"],
});
const page = await browser.newPage({
  colorScheme: "light",
  deviceScaleFactor: 1,
  reducedMotion: "reduce",
  viewport: { width: 1920, height: 1440 },
});
const captures = [];
const sourceCommit = execFileSync("git", ["rev-parse", "HEAD"], {
  encoding: "utf8",
}).trim();

async function settle() {
  await page.waitForTimeout(350);
  await page.evaluate(() => new Promise((resolveFrame) => globalThis.requestAnimationFrame(() => resolveFrame())));
}

async function capture(name, focus = null) {
  await settle();
  await page.screenshot({
    path: resolve(outputDir, `${name}.png`),
    animations: "disabled",
    caret: "hide",
    fullPage: false,
  });
  captures.push({ name, focus });
}

async function click(buttonName) {
  const target = page
    .getByRole("navigation", { name: "Primary research workflows" })
    .getByRole("button", { name: buttonName, exact: true });
  const box = await target.boundingBox();
  await target.click();
  return box === null ? null : [box.x + box.width / 2, box.y + box.height / 2];
}

async function selectFirstMeaningfulObject() {
  const candidates = page.locator(".world-lens .semantic-graph__equivalent button");
  if ((await candidates.count()) > 0) await candidates.first().click();
}

try {
  await page.goto(baseUrl, { waitUntil: "networkidle", timeout: 120_000 });
  await page.getByRole("heading", { name: "Economic World Model" }).waitFor();
  await page.getByRole("heading", { name: "Read the economy from evidence to consequence." }).waitFor();
  await capture("overview", [960, 560]);

  let focus = await click("Economy");
  await page.getByRole("heading", { name: "Declared economic world" }).waitFor();
  await capture("economy", focus);
  await selectFirstMeaningfulObject();
  await page.locator(".inspector .object-detail").waitFor();
  await capture("economy-selected", [1110, 740]);

  focus = await click("Simulation");
  await page.getByRole("heading", { name: "Runtime episode" }).waitFor();
  await capture("simulation", focus);

  focus = await click("Markets");
  await page.getByRole("heading", { name: "Market outcomes" }).waitFor();
  await capture("market-diagnostics", focus);

  focus = await click("Learning");
  await page.getByRole("heading", { name: "Behavior-to-learning closure" }).waitFor();
  await capture("learning", focus);

  focus = await click("Evidence");
  await page.getByRole("heading", { name: "Evidence lens" }).waitFor();
  await capture("evidence", focus);

  focus = await click("DDGE");
  await page.getByRole("heading", { name: "DDGE diagnostics" }).waitFor();
  await capture("ddge", focus);

  focus = await click("Compare");
  await page.getByRole("heading", { name: "Comparison lens" }).waitFor();
  await capture("compare", focus);

  focus = await click("Lineage");
  await page.getByRole("heading", { name: "Lineage lens" }).waitFor();
  const start = page.getByLabel("Lineage start");
  const target = page.getByLabel("Lineage target");
  await start.waitFor();
  await target.waitFor();
  if ((await start.inputValue()) === "") {
    await start.selectOption({ index: 1 });
  }
  const targetOptions = await target.locator("option").evaluateAll((options) =>
    options.map((option) => ({ label: option.textContent ?? "", value: option.value })),
  );
  const declaredAnchor =
    targetOptions.find((option) => /a8813/i.test(option.label) && option.value !== "") ??
    targetOptions.find((option) => /geo anchor/i.test(option.label) && option.value !== "");
  await target.selectOption(declaredAnchor?.value ?? { index: 1 });
  if ((await target.inputValue()) === "") {
    throw new Error("Lineage showcase target selection did not persist");
  }
  await page
    .getByRole("region", { name: "Lineage path" })
    .or(page.getByText("The bounded path query failed."))
    .waitFor();
  await capture("lineage", focus);

  focus = await click("Graph");
  await page.getByRole("heading", { name: "Ontology graph" }).waitFor();
  await page.locator(".ontology-graph-2d svg").waitFor();
  const overviewDensity = page
    .getByLabel("Semantic zoom")
    .getByRole("button", { name: "Overview", exact: true });
  if ((await overviewDensity.count()) > 0) await overviewDensity.click();
  const isolate = page.getByRole("checkbox", { name: "Isolate neighborhood" });
  if ((await isolate.count()) > 0 && (await isolate.isChecked())) await isolate.uncheck();
  await capture("graph-2d", focus);

  const graphNodes = page.locator(".ontology-graph-2d g[role=button]");
  const householdNode = graphNodes.filter({ hasText: "Households" }).first();
  const showcaseNode = (await householdNode.count()) > 0 ? householdNode : graphNodes.first();
  if ((await showcaseNode.count()) > 0) await showcaseNode.click();
  const neighborhoodDepth = page.getByLabel("Neighborhood depth");
  if ((await neighborhoodDepth.count()) > 0) await neighborhoodDepth.selectOption("2");
  if ((await isolate.count()) > 0) await isolate.check();
  await capture("graph-2d-neighborhood", [1040, 845]);

  if ((await isolate.count()) > 0) await isolate.uncheck();
  const detail = page
    .getByLabel("Semantic zoom")
    .getByRole("button", { name: "Detail", exact: true });
  if ((await detail.count()) > 0) await detail.click();

  const dimension3d = page.getByRole("button", { name: "3D", exact: true });
  focus = await dimension3d.boundingBox().then((box) =>
    box === null ? null : [box.x + box.width / 2, box.y + box.height / 2],
  );
  await dimension3d.click();
  const scene = page.getByRole("img", { name: "3D ontology scene" });
  await scene.waitFor({ timeout: 30_000 });
  await page.getByRole("button", { name: "Reset camera", exact: true }).click();
  await capture("graph-3d", focus);

  if ((await isolate.count()) > 0) await isolate.check();
  const focusSelection = page.getByRole("button", { name: "Focus selection", exact: true });
  if ((await focusSelection.count()) > 0 && (await focusSelection.isEnabled())) {
    await focusSelection.click();
  }
  await capture("graph-3d-focus", [1060, 900]);

  focus = await click("Globe");
  await page.getByRole("heading", { name: "Explicit economic geography" }).waitFor();
  await page.locator(".economic-globe canvas").waitFor({ timeout: 30_000 });
  await capture("globe", focus);

  focus = await click("Overview");
  await page.getByRole("heading", { name: "Read the economy from evidence to consequence." }).waitFor();
  await page.setViewportSize({ width: 390, height: 844 });
  await capture("mobile-overview", [195, 422]);

  writeFileSync(
    resolve(outputDir, "capture-manifest.json"),
    `${JSON.stringify({
      schema: "ewm.showcase-capture.v2",
      capturedOn: "2026-08-29",
      sourceCommit,
      runId: "85814cfc1134cb6fc355",
      runIdentity: "85814cfc1134cb6fc35596af0567fc80525d5729b7c104d99470ee846e59a620",
      projectionDigest: "91a00ddafe8e2a309afd520bd49192a95bdf3edfd03c0cbbb8c36c3b88560a32",
      figma: {
        file: "https://www.figma.com/design/bvIJUuCscGMrEerMzznxJI",
        heroFrame: "2:2",
        openGraphFrame: "2:19",
        brandSystemFrame: "2:28",
      },
      baseUrl,
      sourceSize: [1920, 1440],
      captures,
    }, null, 2)}\n`,
  );
} finally {
  await browser.close();
}
