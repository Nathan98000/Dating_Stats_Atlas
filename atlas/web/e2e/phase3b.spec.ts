import { expect, test } from "@playwright/test";

/** Phase 3b (m3.1.0, ADR 0009 amended): the chances-of-matching DISPLAY is
 * capped at the registry ceiling and renders as "250+" wherever the figure
 * appears — result rows, the city page, the compare table — from the
 * API's one formatting helper; the compare table computes no difference
 * against a capped figure. The fixture's San Jose runs to 400 for a
 * graduate Asian woman of 30, so it is the capped case. */

const DISCLOSED_QS =
  "self_sex=female&self_age=30&age=28-40&marital=never,previously&self_edu=graduate&self_race=asian_nh";

test("a figure above the ceiling renders as 250+ on the result row, the city page and the compare table", async ({ page }) => {
  await page.goto(`/?${DISCLOSED_QS}`);
  const rows = page.getByTestId("ranked-list").locator("li");
  await expect(rows.first()).toBeVisible();
  const sanJose = rows.filter({ hasText: "San Jose" }).first();
  const fig = sanJose.getByTestId("match-figure");
  await expect(fig).toContainText("250+");
  await expect(fig).not.toContainText(/\b[3-9]\d\d\b/);
  await expect(fig.getByTestId("match-band")).toContainText("Far above most cities");
  // an uncapped row keeps its plain figure
  const nyc = rows.filter({ hasText: "New York" }).first();
  await expect(nyc.getByTestId("match-figure")).not.toContainText("+");

  await page.goto(`/city/san-jose-california?${DISCLOSED_QS}`);
  await expect(page.getByTestId("ranked-card").getByTestId("match-figure")).toContainText("250+");

  await page.goto(`/compare/san-jose-california/austin-texas?${DISCLOSED_QS}`);
  const table = page.getByTestId("compare-table");
  await expect(table).toContainText("250+");
  // no difference is computed from a capped figure: the cell shows the
  // same dash a missing figure gets, never "+171" parsed from "250+"
  const diff = table.locator('[data-diff-for="match_propensity"]');
  await expect(diff).toBeVisible();
  await expect(diff).toHaveText("—");
  // every other row's difference still computes
  await expect(table.locator('[data-diff-for="pool"]')).not.toHaveText("—");
});

test("an uncapped search computes the chances-of-matching difference as before", async ({ page }) => {
  await page.goto(
    "/compare/san-jose-california/austin-texas?self_sex=female&self_age=30&age=28-40&marital=never,previously");
  const table = page.getByTestId("compare-table");
  await expect(table).not.toContainText("250+");
  await expect(table.locator('[data-diff-for="match_propensity"]')).toHaveText(/^[+−]\d+$|^0$/);
});
