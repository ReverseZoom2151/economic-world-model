import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

import { expect, test } from "@playwright/test";

const PYTHON = "../.venv/bin/python";
const EXPORT_SCRIPT = [
  "import sys",
  "from pathlib import Path",
  "import ewm",
  "from ewm.cli import main",
  "root = Path(sys.argv[1])",
  "run = ewm.run_experiment('fx.rollout', preset='smoke', seed=61, output_root=root / 'runs').run_dir",
  "raise SystemExit(main(['snapshot', 'export', str(run), '--selection', str(root / 'selection.json'), '--output', str(root / 'investigation.html')]))",
].join("; ");

function buildSnapshot(outputDirectory: string): string {
  mkdirSync(outputDirectory, { recursive: true });
  writeFileSync(
    `${outputDirectory}/selection.json`,
    JSON.stringify({ lens: "world", filters: { kinds: [], layers: [], query: "" } }),
  );
  execFileSync(PYTHON, ["-c", EXPORT_SCRIPT, outputDirectory], {
    cwd: process.cwd(),
    stdio: "pipe",
    timeout: 120_000,
  });
  return `${outputDirectory}/investigation.html`;
}

test("opens a verified standalone investigation with networking disabled", async ({
  context,
  page,
}, testInfo) => {
  test.setTimeout(150_000);
  const snapshot = buildSnapshot(testInfo.outputDir);
  const remoteRequests: string[] = [];
  page.on("request", (request) => {
    if (/^https?:/.test(request.url())) remoteRequests.push(request.url());
  });
  await context.setOffline(true);

  await page.goto(pathToFileURL(snapshot).href);

  await expect(
    page.getByRole("heading", { name: "Ontology Research Workbench" }),
  ).toBeVisible();
  await expect(page.getByText("offline-snapshot", { exact: false })).toHaveCount(0);
  await expect(page.getByLabel("Approved run")).toBeEnabled();
  await expect(page.getByText("Active projection", { exact: true })).toBeVisible();
  expect(remoteRequests).toEqual([]);
});

test("refuses to render a corrupted embedded investigation", async ({ page }, testInfo) => {
  test.setTimeout(150_000);
  const snapshot = buildSnapshot(testInfo.outputDir);
  const html = readFileSync(snapshot, "utf8");
  const marker = '<template id="ewm-snapshot"';
  const payloadStart = html.indexOf(">", html.indexOf(marker)) + 1;
  const replacement = html[payloadStart] === "A" ? "B" : "A";
  writeFileSync(
    snapshot,
    `${html.slice(0, payloadStart)}${replacement}${html.slice(payloadStart + 1)}`,
  );

  await page.goto(pathToFileURL(snapshot).href);

  await expect(page.getByRole("alert")).toContainText("Snapshot integrity check failed");
  await expect(
    page.getByRole("heading", { name: "Ontology Research Workbench" }),
  ).toHaveCount(0);
});
