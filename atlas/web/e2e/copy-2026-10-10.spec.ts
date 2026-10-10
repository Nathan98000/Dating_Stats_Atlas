import { expect, test } from "@playwright/test";
import { expandRow, fetchMeta, seedAboutYou } from "./helpers";

/** Nathan's changes of 2026-10-10, after the city-detail redesign: balance's
 * box and the points' caption in his words, no box for What moved the score
 * (the Sharpen compatibility pill and box are in phase6.spec.ts), and on
 * Compare a column called Comparison that judges every measure with a
 * direction, Not much included, and never shows a dash; the sentence after
 * the search and the line under the table gone; room on the table's right;
 * political lean a line per party (phase4d.spec.ts). Then his second round:
 * the same-sex note in his words on every page that shows it, one balance
 * caption on every search, and the city page's first card in two columns. */

const BALANCE_BOX =
  "Balance compares all single men with all single women in the ages you picked, no other filters are used for the calculation.";
const QS = "sex=male&self_age=30&age=28-40&marital=never,previously";

test("balance's box and the points' caption are Nathan's words, and the points have no box", async ({ page, request }) => {
  const ps = (await fetchMeta(request)).policy_strings;
  expect(ps.balance_caption).toBe(BALANCE_BOX);
  expect(ps.moved_caption).toBe("Compared with the median city");
  await page.goto(`/?${QS}`);
  const row = await expandRow(page, 4);
  const detail = row.getByTestId("row-detail");
  await expect(detail.getByTestId("moved-caption")).toHaveText("Compared with the median city");
  await expect(detail.getByRole("button", { name: /^About/ })).toHaveCount(1);
  await detail.getByRole("button", { name: ps.balance_info_label }).click();
  await expect(page.getByTestId("info-tip-note")).toHaveText(BALANCE_BOX);
});

test("compare: a measure set to Not much is judged like every other row", async ({ page }) => {
  // weather and cost of living set to Not much
  await page.goto(`/compare/provo-utah/austin-texas?${QS}&iw=n&ic=n`);
  const table = page.getByTestId("compare-table");
  await expect(table).toBeVisible();
  for (const id of ["pleasant_days", "rent_1br", "everyday_prices"]) {
    const cell = table.locator(`[data-diff-for="${id}"]`);
    const edge = await cell.getAttribute("data-edge");
    expect(edge, id).not.toBeNull();
    if (edge === "0") continue; // a tie: the two values read the same
    await expect(cell, id).toContainText(edge === "1" ? "Provo" : "Austin");
    await expect(cell.locator("[data-diff-value]"), id).toHaveText(/^by /);
  }
  // population alone stays unjudged: its plain difference, no dash
  const pop = table.locator('[data-diff-for="who_lives_here"]');
  await expect(pop).toHaveAttribute("data-edge", "0");
  await expect(pop).toHaveText(/^[+−]\d/);
});

test("compare: no dash in the Comparison column, no 'edge' on the page, the two sentences gone", async ({ page }) => {
  await page.goto(`/compare/provo-utah/austin-texas?${QS}&ist=n`);
  const table = page.getByTestId("compare-table");
  await expect(table.getByRole("columnheader", { name: "Comparison" })).toBeVisible();
  for (const text of await table.locator("[data-diff-for], [data-no-diff]").allInnerTexts()) {
    expect(text).not.toContain("—");
  }
  const main = page.locator("main");
  await expect(main).not.toContainText(/\bedge\b/i);
  await expect(main).not.toContainText("yardstick");
  await expect(page.getByTestId("diff-legend")).toHaveCount(0);
  await expect(main.locator("p").filter({ hasText: /^For single men 28–40/ }))
    .toHaveText("For single men 28–40 (never married, divorced or widowed).");
});

test("compare at 1440: the Comparison column has room, and its lines don't wrap", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/compare/provo-utah/austin-texas?${QS}`);
  const table = page.getByTestId("compare-table");
  const head = table.getByRole("columnheader", { name: "Comparison" });
  expect((await head.boundingBox())!.width).toBeGreaterThanOrEqual(200);
  const lines = table.locator("[data-diff-value]");
  expect(await lines.count()).toBeGreaterThan(8);
  for (const box of await lines.evaluateAll((els) => els.map((e) => e.getBoundingClientRect().height))) {
    expect(box).toBeLessThan(24);
  }
  const pad = await table.locator("[data-diff-for]").first().evaluate((td) => getComputedStyle(td).paddingRight);
  expect(pad).toBe("28px");
});

test("compare on a phone: the ▲ beside the value that does better is named, never 'Edge'", async ({ page, request }) => {
  const ps = (await fetchMeta(request)).policy_strings;
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/compare/provo-utah/austin-texas?${QS}`);
  const marks = page.getByTestId("compare-table").getByRole("img", { name: ps.compare_does_better });
  expect(await marks.count()).toBeGreaterThan(3);
  await expect(page.getByTestId("compare-table").getByRole("img", { name: /edge/i })).toHaveCount(0);
});

const SAME_SEX_NOTE = "On a same-sex search, matches count every single man in these ages, not just those looking for men.";
const SAME_SEX_QS = "self_age=33&sex=male&age=28-38&marital=never,previously";

test("a man looking for men: the note in Nathan's words on Rankings, the city page and Compare; balance's box as on any search", async ({ page }) => {
  await seedAboutYou(page, { sex: "male" });
  await page.goto(`/?${SAME_SEX_QS}`);
  await expect(page.getByTestId("same-sex-note")).toHaveText(SAME_SEX_NOTE);
  await expect(page.getByTestId("balance-footnote")).toHaveText(BALANCE_BOX);
  const row = await expandRow(page, 4);
  await row.getByRole("button", { name: "About balance" }).click();
  await expect(page.getByTestId("info-tip-note")).toHaveText(BALANCE_BOX);
  await page.goto(`/city/austin-texas?${SAME_SEX_QS}`);
  await expect(page.getByTestId("ranked-card").getByTestId("same-sex-note")).toHaveText(SAME_SEX_NOTE);
  await page.goto(`/compare/provo-utah/austin-texas?${SAME_SEX_QS}`);
  await expect(page.getByTestId("compare-table").getByTestId("same-sex-note")).toHaveText(SAME_SEX_NOTE);
  await expect(page.locator("main")).not.toContainText("describes the city");
});

test("the city page's first card: two columns from 768px, balance and compatibility beside the score", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/city/austin-texas?${QS}`);
  const card = page.getByTestId("ranked-card");
  const [spot, people, box] = [await card.getByTestId("city-spot").boundingBox(),
    await card.getByTestId("city-people").boundingBox(), await card.boundingBox()];
  expect(people!.x).toBeGreaterThan(spot!.x + spot!.width);
  expect(people!.y).toBeLessThan(spot!.y);
  // the old wrapping row left the card about 466px tall at this width
  expect(box!.height).toBeLessThan(420);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/city/austin-texas?${QS}`);
  const [spotP, peopleP] = [await card.getByTestId("city-spot").boundingBox(),
    await card.getByTestId("city-people").boundingBox()];
  expect(peopleP!.y).toBeGreaterThan(spotP!.y + spotP!.height);
});
