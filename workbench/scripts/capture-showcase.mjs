import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import process from "node:process";

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

async function settle(delay = 450) {
  await page.waitForTimeout(delay);
  await page.evaluate(() => new Promise((resolveFrame) => {
    globalThis.requestAnimationFrame(() => resolveFrame());
  }));
}

async function capture(name, stage, focus = null) {
  await settle();
  await page.screenshot({
    path: resolve(outputDir, `${name}.png`),
    animations: "disabled",
    caret: "hide",
    fullPage: false,
  });
  captures.push({ name, stage, focus });
}

async function navigate(buttonName) {
  const target = page
    .getByRole("navigation", { name: "Primary research workflows" })
    .getByRole("button", { name: buttonName, exact: true });
  const box = await target.boundingBox();
  await target.click();
  return box === null ? null : [box.x + box.width / 2, box.y + box.height / 2];
}

async function nextStep(expectedHeading) {
  const target = page.locator(".guided-investigation__next");
  const box = await target.boundingBox();
  await target.click();
  await page.getByRole("heading", { name: expectedHeading }).waitFor();
  return box === null ? null : [box.x + box.width / 2, box.y + box.height / 2];
}

async function selectGraphHousehold() {
  const graphNodes = page.locator(".ontology-graph-2d g[role=button]");
  const householdNode = graphNodes.filter({ hasText: "Households" }).first();
  const showcaseNode = (await householdNode.count()) > 0 ? householdNode : graphNodes.first();
  if ((await showcaseNode.count()) > 0) await showcaseNode.click();
}

try {
  await page.goto(baseUrl, { waitUntil: "networkidle", timeout: 120_000 });
  await page.getByRole("heading", { name: "Economic World Model" }).waitFor();
  await page.getByRole("heading", { name: "Read the economy from evidence to consequence." }).waitFor();
  await capture("overview", "Choose a research question", [995, 785]);

  const auditEntry = page.getByRole("button", { name: "Audit FX execution", exact: true });
  const auditBox = await auditEntry.boundingBox();
  await auditEntry.click();
  await page.getByRole("heading", { name: "Declared economic world" }).waitFor();
  await capture(
    "journey-01-economy",
    "Scope the declared actors, market, mechanisms, and accounting boundary",
    auditBox === null ? null : [auditBox.x + auditBox.width / 2, auditBox.y + auditBox.height / 2],
  );

  const householdCard = page.locator(".world-lens .semantic-graph__equivalent button").filter({ hasText: "Households" }).first();
  const worldCard = page.locator(".world-lens .semantic-graph__equivalent button").first();
  const economySelection = (await householdCard.count()) > 0 ? householdCard : worldCard;
  if ((await economySelection.count()) > 0) await economySelection.click();
  if ((await page.locator(".inspector .object-detail").count()) > 0) {
    await page.locator(".inspector .object-detail").waitFor();
    await capture("economy-selected", "Inspect a declared economic actor and its sourced properties", [1550, 760]);
  }

  let focus = await nextStep("Runtime episode");
  await page.locator(".runtime-flow").waitFor();
  const runtimeEvent = page.locator(".runtime-flow button").first();
  if ((await runtimeEvent.count()) > 0) await runtimeEvent.click();
  await capture("journey-02-simulation", "Verify ordered decisions, clearing, and settlement events", focus);

  focus = await nextStep("Market outcomes");
  await page.locator(".market-stat-grid").waitFor();
  await capture("journey-03-market", "Read price, volume, residual, and rejected-order outcomes", focus);

  focus = await nextStep("Behavior-to-learning closure");
  await page.locator(".learning-closure").waitFor();
  await capture("journey-04-learning", "Test whether behavior generated data that trained and redeployed a model", focus);

  focus = await nextStep("DDGE diagnostics");
  await capture("journey-05-ddge", "Separate inner equilibrium evidence from an unavailable DDGE certificate", focus);

  focus = await nextStep("Evidence lens");
  await page.locator(".claim-card").first().waitFor();
  await capture("journey-06-evidence", "Audit the synthetic claim, its source, classification, and limits", focus);

  focus = await nextStep("Lineage lens");
  const start = page.getByLabel("Lineage start");
  const target = page.getByLabel("Lineage target");
  await start.selectOption({ label: "World" });
  await target.selectOption({ label: "Households (40)" });
  await page.getByRole("region", { name: "Lineage path" }).getByText("DECLARES →").waitFor();
  await capture("journey-07-lineage", "Confirm the declared World-to-Households provenance relation", focus);

  focus = await nextStep("Ontology graph");
  await page.locator(".ontology-graph-2d svg").waitFor();
  const overviewDensity = page
    .getByLabel("Semantic zoom")
    .getByRole("button", { name: "Overview", exact: true });
  if ((await overviewDensity.count()) > 0) await overviewDensity.click();
  const isolate = page.getByRole("checkbox", { name: "Isolate neighborhood" });
  if ((await isolate.count()) > 0 && (await isolate.isChecked())) await isolate.uncheck();
  await capture("graph-2d", "Read the balanced ontology overview instead of an undifferentiated node cloud", focus);

  await selectGraphHousehold();
  const neighborhoodDepth = page.getByLabel("Neighborhood depth");
  if ((await neighborhoodDepth.count()) > 0) await neighborhoodDepth.selectOption("2");
  if ((await isolate.count()) > 0) await isolate.check();
  await capture("graph-2d-neighborhood", "Isolate the two-hop neighborhood around Households", [1100, 850]);

  if ((await isolate.count()) > 0) await isolate.uncheck();
  const dimension3d = page.getByRole("button", { name: "3D", exact: true });
  const dimensionBox = await dimension3d.boundingBox();
  await dimension3d.click();
  const scene = page.getByRole("img", { name: "3D ontology scene" });
  await scene.waitFor({ timeout: 30_000 });
  await page.getByRole("button", { name: "Reset camera", exact: true }).click();
  await capture(
    "graph-3d",
    "Rotate the same overview as a spatial ontology, with no duplicated world view",
    dimensionBox === null ? null : [dimensionBox.x + dimensionBox.width / 2, dimensionBox.y + dimensionBox.height / 2],
  );

  if ((await isolate.count()) > 0) await isolate.check();
  const focusSelection = page.getByRole("button", { name: "Focus selection", exact: true });
  if ((await focusSelection.count()) > 0 && (await focusSelection.isEnabled())) await focusSelection.click();
  await capture("graph-3d-focus", "Focus the 3D camera on the selected local economic subgraph", [1110, 875]);

  focus = await nextStep("Explicit economic geography");
  await page.locator(".economic-globe canvas").waitFor({ timeout: 30_000 });
  await capture("journey-09-globe", "Bound declared geography and surface its ±250 km uncertainty", focus);
  const ledgerEntry = page.locator(".geo-ledger button").first();
  if ((await ledgerEntry.count()) > 0) await ledgerEntry.click();
  await capture("globe-selected", "Inspect one geographic ledger entry without implying observed precision", [1530, 825]);

  focus = await nextStep("Read the economy from evidence to consequence.");
  await page.getByRole("heading", { name: /Execution passed inside the synthetic runtime/ }).waitFor();
  await page.getByText("14,484", { exact: true }).waitFor();
  await capture(
    "journey-10-conclusion",
    "Reach the bounded result: zero rejected orders and negligible accounting drift, while model closure remains unproven",
    focus,
  );

  await page.getByRole("button", { name: "Close investigation", exact: true }).click();
  focus = await navigate("Compare");
  await page.getByRole("heading", { name: "Comparison lens" }).waitFor();
  await capture("compare", "Show the honest one-run comparison boundary", focus);

  focus = await navigate("Overview");
  await page.getByRole("heading", { name: "Read the economy from evidence to consequence." }).waitFor();
  await page.setViewportSize({ width: 390, height: 844 });
  await capture("mobile-overview", "Verify the research entry point at a narrow viewport", [195, 422]);

  writeFileSync(
    resolve(outputDir, "capture-manifest.json"),
    `${JSON.stringify({
      schema: "ewm.showcase-capture.v3",
      capturedOn: "2026-08-29",
      sourceCommit,
      runId: "85814cfc1134cb6fc355",
      runIdentity: "85814cfc1134cb6fc35596af0567fc80525d5729b7c104d99470ee846e59a620",
      projectionDigest: "91a00ddafe8e2a309afd520bd49192a95bdf3edfd03c0cbbb8c36c3b88560a32",
      achievement: {
        question: "Did the FX economy clear without rejected orders or material accounting drift?",
        result: "Execution passed inside the synthetic runtime; adaptive model closure remains unproven.",
        rejectedOrders: 0,
        totalVolume: 14484,
        meanPrice: 1.000339747592091,
        maxCashResidual: 2.473825588822365e-10,
      },
      figma: {
        file: "https://www.figma.com/design/G7201TNCRNk5AMdRMexznH",
        foundationsFrame: "5:19",
        renaissanceSeriesFrame: "5:41",
        workflowStoryboardFrame: "6:45",
        readmeHeroFrame: "6:113",
        openGraphFrame: "6:120",
      },
      baseUrl,
      sourceSize: [1920, 1440],
      captures,
    }, null, 2)}\n`,
  );
} finally {
  await browser.close();
}
