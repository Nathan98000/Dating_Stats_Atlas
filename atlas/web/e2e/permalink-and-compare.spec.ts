import { expect, test } from "@playwright/test";

/** Reproducibility survives m2.0.0 with no permalink in the UI: the API's
 * own permalink still resolves, a stale pin refuses onto a plain page with
 * no version ids, and the compare page renders two cities from one
 * response. */

test("the API's permalink resolves even though no page shows one", async ({ page }) => {
  const res = await page.request.post("/api/rank", {
    data: {
      self: { sex: "female", age: 30 },
      seeking: { age: [28, 40], marital: ["never_married", "previously_married"] },
    },
  });
  expect(res.ok()).toBe(true);
  const body = await res.json();
  await page.goto(body.permalink);
  const rows = page.getByTestId("ranked-list").locator("li");
  await expect(rows.first()).toBeVisible();
  expect(await rows.first().getAttribute("data-cbsa")).toBe(body.ranked[0].cbsa);
});

test("a stale pin refuses plainly, with no version id in the copy", async ({ page }) => {
  const res = await page.request.post("/api/rank", {
    data: {
      self: { sex: "female", age: 30 },
      seeking: { age: [28, 40], marital: ["never_married"] },
    },
  });
  const { permalink } = await res.json();
  const stale = permalink.replace(/\/r\/[^/]+\//, "/r/2099.01a/");
  await page.goto(stale);
  const shell = page.getByTestId("pin-mismatch");
  await expect(shell).toBeVisible();
  await expect(shell).toContainText("earlier edition");
  const text = (await shell.textContent()) ?? "";
  expect(text).not.toMatch(/\bm\d+\.\d+\.\d+\b/);
  expect(text).not.toMatch(/\b[0-9a-f]{12}\b/);
  await page.getByTestId("rerun-current").click();
  await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
});

test("the compare page shows two cities from one response", async ({ page }) => {
  await page.goto(
    "/compare/austin-texas/pittsburgh-pennsylvania?self_sex=female&self_age=30&age=28-40&marital=never,previously",
  );
  const table = page.getByTestId("compare-table");
  await expect(table).toBeVisible();
  await expect(table).toContainText("People who match");
  // Phase 2f item 6.1 (ADR 0007, reversing ADR 0003): pools GET a
  // difference now — the plain subtraction of the two displayed counts
  const poolDiff = table.locator('[data-diff-for="pool"]');
  await expect(poolDiff).toHaveText(/^[+−][\d,]+$/);
  await expect(table).toContainText("Rent");
  const text = (await table.textContent()) ?? "";
  expect(text).not.toMatch(/\bCBSA\b/i);
});
