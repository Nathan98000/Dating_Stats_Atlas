/** Phase 2f report screenshots against the running dev stack.
 *
 *   node scripts/shoot_phase2f.mjs [base] [outDir]
 */
import { chromium } from "@playwright/test";
import path from "path";

const base = process.argv[2] ?? "http://localhost:3000";
const out = process.argv[3] ?? path.resolve("..", "results", "phase2f");
const CITY = "/city/provo-utah?self_sex=female&self_age=30&age=28-40&marital=never,previously";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

async function shot(name, opts = {}) {
  await page.screenshot({ path: path.join(out, name), ...opts });
  console.log("  " + name);
}

// 1: the home page — hero photograph with attribution, new headline
await page.goto(`${base}/`);
await page.getByTestId("ranked-list").locator("li").first().waitFor();
await shot("01_home_hero_headline.png");

// 2: the panel's weighting group — slider immediately above importance
await page.getByTestId("weighting").scrollIntoViewIfNeeded();
await page.waitForTimeout(250);
await shot("02_panel_weighting_group.png");

// 3–5: the card grid at three widths — the five-segment indicators
// align across every row (gate 6)
for (const [name, w, h] of [
  ["03_city_cards_1280.png", 1280, 900],
  ["04_city_cards_1024.png", 1024, 900],
  ["05_city_cards_375.png", 375, 1400],
]) {
  await page.setViewportSize({ width: w, height: h });
  await page.goto(`${base}${CITY}`);
  await page.locator('[data-card="median_gross_rent"]').scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  await shot(name);
}
await page.setViewportSize({ width: 1280, height: 900 });

// 6: the crime popover held open with its link (items 3 + 5.3)
await page.goto(`${base}${CITY}`);
const info = page.getByTestId("crime-info-violent_crime_rate");
await info.scrollIntoViewIfNeeded();
await info.hover();
await page.getByTestId("crime-info-violent_crime_rate-note").waitFor();
await shot("06_crime_popover_see_more.png");

// 7: the compare table — five new differences, colours, legend
await page.goto(`${base}/compare/provo-utah/austin-texas?self_sex=female&self_age=30&age=28-40&marital=never,previously`);
await page.getByTestId("diff-legend").scrollIntoViewIfNeeded();
await page.waitForTimeout(250);
await shot("07_compare_differences_legend.png");

// 8: compare crime — new banner, per-100,000 unit under the labels
await page.getByTestId("compare-crime").scrollIntoViewIfNeeded();
await page.waitForTimeout(250);
await shot("08_compare_crime_units.png");

// 9: What we measure — no intro, cost group with rent + everyday prices
await page.goto(`${base}/what-we-measure`);
await page.getByTestId("measure-crime").waitFor();
await shot("09_what_we_measure.png", { fullPage: true });

// 10: the rent stat page — source line, caution, header row, no band labels
await page.goto(`${base}/stats/median_gross_rent`);
await page.getByTestId("stat-list").locator("li").first().waitFor();
await shot("10_rent_stat_page.png");

await browser.close();
console.log("done ->", out);
