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
  const target = page.getByRole("button", { name: buttonName, exact: true });
  const box = await target.boundingBox();
  await target.click();
  return box === null ? null : [box.x + box.width / 2, box.y + box.height / 2];
}

try {
  await page.goto(baseUrl, { waitUntil: "networkidle", timeout: 120_000 });
  await page.getByRole("heading", { name: "Ontology Research Workbench" }).waitFor();
  await page.getByRole("heading", { name: "Read the economy from evidence to consequence." }).waitFor();
  await capture("overview", [960, 560]);

  let focus = await click("Economy");
  await page.getByRole("heading", { name: "Declared economic world" }).waitFor();
  await capture("economy", focus);

  focus = await click("Simulation");
  await page.getByRole("heading", { name: "Runtime episode" }).waitFor();
  await capture("simulation", focus);

  focus = await click("Markets");
  await page.getByRole("heading", { name: "Market outcomes" }).waitFor();
  await capture("market-diagnostics", focus);

  focus = await click("Learning");
  await page.getByRole("heading", { name: "Behavior-to-learning closure" }).waitFor();
  await capture("learning", focus);

  const advanced = page.locator(".advanced-nav");
  if ((await advanced.getAttribute("open")) === null) {
    await advanced.locator("summary").click();
  }
  focus = await click("Graph");
  await page.getByRole("heading", { name: "Ontology graph" }).waitFor();
  await page.locator(".ontology-graph-2d svg").waitFor();
  const graphNodes = page.locator(".ontology-graph-2d g[role=button]");
  const householdNode = graphNodes.filter({ hasText: "Households" }).first();
  const showcaseNode = (await householdNode.count()) > 0 ? householdNode : graphNodes.first();
  if ((await showcaseNode.count()) > 0) await showcaseNode.click();
  const neighborhoodDepth = page.getByLabel("Neighborhood depth");
  if ((await neighborhoodDepth.count()) > 0) await neighborhoodDepth.selectOption("2");
  const isolate = page.getByRole("checkbox", { name: "Isolate neighborhood" });
  if ((await isolate.count()) > 0) await isolate.check();
  await capture("graph-2d", focus);

  focus = await click("3D");
  const scene = page.getByRole("img", { name: "3D ontology scene" });
  await scene.waitFor({ timeout: 30_000 });
  await click("Reset camera");
  await capture("graph-3d", focus);

  focus = await click("Globe");
  await page.getByRole("heading", { name: "Explicit economic geography" }).waitFor();
  await page.locator(".economic-globe canvas").waitFor({ timeout: 30_000 });
  await capture("globe", focus);

  writeFileSync(
    resolve(outputDir, "capture-manifest.json"),
    `${JSON.stringify({ baseUrl, sourceSize: [1920, 1440], captures }, null, 2)}\n`,
  );
} finally {
  await browser.close();
}
