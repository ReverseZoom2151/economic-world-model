import { expect, test } from "@playwright/test";

test("does not issue remote requests or execute URL-provided markup", async ({ page }) => {
  const remote: string[] = [];
  page.on("request", (request) => {
    if (!request.url().startsWith("http://127.0.0.1:4173/")) remote.push(request.url());
  });
  await page.goto(
    "/e2e/fixtures/app.html?q=%3Cimg%20src%3Dx%20onerror%3Dwindow.__ewm_xss%3D1%3E",
  );

  await expect(page.getByRole("heading", { name: "Ontology Research Workbench" })).toBeVisible();
  expect(remote).toEqual([]);
  expect(await page.evaluate(() => (window as typeof window & { __ewm_xss?: number }).__ewm_xss)).toBeUndefined();
  expect(await page.locator("img[src='x']").count()).toBe(0);
});

test("keeps browser persistence empty", async ({ page }) => {
  await page.goto("/e2e/fixtures/app.html");
  const persistence = await page.evaluate(() => ({
    local: Object.keys(localStorage),
    session: Object.keys(sessionStorage),
    cookies: document.cookie,
  }));

  expect(persistence).toEqual({ local: [], session: [], cookies: "" });
});
