import { expect, test } from "@playwright/test";

/** Permalinks reproduce or refuse with an explanation (§5.4/§10.1); the
 * compare page renders two metros from one response. */

test("a live permalink reproduces the ranking under its pins", async ({ page }) => {
  const res = await page.request.post("/api/rank", {
    data: {
      self: { sex: "female", age: 30 },
      seeking: { age: [28, 40], marital: ["never_married", "previously_married"] },
    },
  });
  expect(res.ok()).toBe(true);
  const body = await res.json();
  await page.goto(body.permalink);
  await expect(page.locator("text=Reproduced exactly under its pins")).toBeVisible();
  const firstCbsa = await page
    .getByTestId("ranked-list")
    .locator("li")
    .first()
    .getAttribute("data-cbsa");
  expect(firstCbsa).toBe(body.ranked[0].cbsa);
});

test("a stale pin is a real page offering a re-run, never a substitution", async ({ page }) => {
  const res = await page.request.post("/api/rank", {
    data: {
      self: { sex: "female", age: 30 },
      seeking: { age: [28, 40], marital: ["never_married"] },
    },
  });
  const { permalink } = await res.json();
  const stale = permalink.replace(/\/r\/[^/]+\//, "/r/2099.01a/");
  await page.goto(stale);
  await expect(page.getByTestId("pin-mismatch")).toBeVisible();
  await expect(page.getByTestId("pin-mismatch")).toContainText("different build");
  // no ranking rows rendered under the wrong pin
  await expect(page.getByTestId("ranked-list")).toHaveCount(0);
  await page.getByTestId("rerun-current").click();
  await expect(page).toHaveURL(/\/\?self_sex=female/);
  await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
});

test("the compare page shows two metros from one response", async ({ page }) => {
  // two fixture metros that rank for the default profile
  await page.goto("/compare/35620/12420?self_sex=female&self_age=30&age=28-40&marital=never,previously");
  const table = page.getByTestId("compare-table");
  await expect(table).toBeVisible();
  await expect(table).toContainText("Compatible people");
  // both pools carry their own margins; no pool difference is invented
  const poolRow = table.locator("tr", { hasText: "Compatible people" }).first();
  await expect(poolRow).toContainText(/margin at least ±[\d,]+.*margin at least ±[\d,]+/s);
  await expect(poolRow).toContainText("a difference would not");
  // static stats do get a difference column
  const rentRow = table.locator("tr", { hasText: "Median rent" });
  await expect(rentRow).toContainText(/[+−][\d,]+/);
});
