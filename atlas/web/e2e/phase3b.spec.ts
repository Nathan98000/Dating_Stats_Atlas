import { expect, test } from "@playwright/test";
import { revealRows, seedAboutYou } from "./helpers";

/** Phase 3b (m3.1.0, ADR 0009 amended): the compatibility figure's DISPLAY is
 * capped at the registry ceiling and renders as "250+" wherever the figure
 * appears — result rows, the city page, the compare table — from the
 * API's one formatting helper; the compare table computes no difference
 * against a capped figure. The fixture's San Jose runs to 400 for a
 * graduate Asian woman of 30 who gives her race (m4.0.0: her details are
 * in the browser, never the URL), so it is the capped case. */

const DISCLOSED_QS = "sex=male&self_age=30&age=28-40&marital=never,previously";

test("a figure above the ceiling renders as 250+ on the result row, the city page and the compare table", async ({ page }) => {
  await seedAboutYou(page, { sex: "female", edu: "graduate", race: "asian_nh" });
  // Phase 5: the top three are cards, which carry no figure; worst first,
  // San Jose (near the top of this variant) is a row
  await page.goto(`/?${DISCLOSED_QS}&sort=worst_first`);
  const rows = page.getByTestId("ranked-list").locator("li[data-rank]");
  await expect(rows.first()).toBeVisible();
  // Phase 5: the figure sits in each row's detail
  await revealRows(page);
  const sanJose = rows.filter({ hasText: "San Jose" }).first();
  const fig = sanJose.getByTestId("match-figure");
  await expect(fig).toContainText("250+");
  await expect(fig).not.toContainText(/\b[3-9]\d\d\b/);
  // Phase 4b: the band ("Far above most cities") is still served, never shown
  await expect(fig).not.toContainText(/most cities|About average/);
  // an uncapped row keeps its plain figure
  const nyc = rows.filter({ hasText: "New York" }).first();
  await expect(nyc.getByTestId("match-figure")).not.toContainText("+");

  await page.goto(`/city/san-jose-california?${DISCLOSED_QS}`);
  await expect(page.getByTestId("ranked-card").getByTestId("match-figure")).toContainText("250+");

  await page.goto(`/compare/san-jose-california/austin-texas?${DISCLOSED_QS}`);
  const table = page.getByTestId("compare-table");
  await expect(table).toContainText("250+");
  // no difference is computed from a capped figure: the cell stays as
  // empty as a missing figure leaves it (no dash since 2026-10-10), never
  // "+171" parsed from "250+"
  const diff = table.locator('[data-diff-for="match_propensity"]');
  await expect(diff).toHaveCount(1);
  await expect(diff).toHaveText("");
  // every other row's difference still computes
  await expect(table.locator('[data-diff-for="pool"] [data-diff-value]')).toHaveText(/\d/);
});

test("an uncapped search computes the compatibility difference as before", async ({ page }) => {
  await page.goto(
    "/compare/san-jose-california/austin-texas?sex=male&self_age=30&age=28-40&marital=never,previously");
  const table = page.getByTestId("compare-table");
  await expect(table).not.toContainText("250+");
  // (Phase 6, F07: a judged difference reads "by {n}")
  await expect(table.locator('[data-diff-for="match_propensity"] [data-diff-value]')).toHaveText(/^by \d+$|^[+−]\d+$|^0$/);
});

// a same-sex search's slider box, race set aside and its figures: phase4b.spec.ts
// ("the slider's box reads the registry string exactly") and phase4c.spec.ts
// ("on a same-sex search own race stays selectable", "a race chosen on a
// same-sex search changes no number")
