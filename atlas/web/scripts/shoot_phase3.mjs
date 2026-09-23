/** Phase 3 report screenshots against the running dev stack.
 *
 *   node scripts/shoot_phase3.mjs [base] [outDir]
 */
import { chromium } from "@playwright/test";
import path from "path";

const base = process.argv[2] ?? "http://localhost:3000";
const out = process.argv[3] ?? path.resolve("..", "results", "phase3");
const DEFAULT_QS = "self_sex=female&self_age=30&age=28-40&marital=never,previously";
const DISCLOSED_QS = `${DEFAULT_QS}&self_edu=graduate&self_race=asian_nh`;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

async function shot(name, opts = {}) {
  await page.screenshot({ path: path.join(out, name), ...opts });
  console.log("  " + name);
}

// 1: the panel — the two optional inputs and the renamed slider poles
await page.goto(`${base}/?${DEFAULT_QS}`);
await page.getByTestId("ranked-list").locator("li").first().waitFor();
await page.getByTestId("search-panel").screenshot({ path: path.join(out, "01_panel_about_you_and_poles.png") });
console.log("  01_panel_about_you_and_poles.png");

// 2: a result row with the match figure, its band and the balance tally
await page.getByTestId("ranked-list").locator("li").first().screenshot({
  path: path.join(out, "02_result_row_match_and_balance.png") });
console.log("  02_result_row_match_and_balance.png");

// 3: the information box open (Nathan's text + the link)
await page.getByTestId("match-info").first().focus();
await page.getByTestId("match-info-note").first().waitFor();
await shot("03_match_info_box.png");

// 4: the same search with education and race disclosed
await page.goto(`${base}/?${DISCLOSED_QS}`);
await page.getByTestId("ranked-list").locator("li").first().waitFor();
await shot("04_results_disclosed_grad_asian.png");

// 5: the city page's ranked card — rank, pool, balance, chances of matching
await page.goto(`${base}/city/austin-texas?${DEFAULT_QS}`);
await page.getByTestId("ranked-card").waitFor();
await page.getByTestId("ranked-card").screenshot({ path: path.join(out, "05_city_ranked_card.png") });
console.log("  05_city_ranked_card.png");

// 6: the compare table with the new row
await page.goto(`${base}/compare/provo-utah/austin-texas?${DEFAULT_QS}`);
await page.getByTestId("compare-table").waitFor();
await page.getByTestId("compare-table").screenshot({ path: path.join(out, "06_compare_match_row.png") });
console.log("  06_compare_match_row.png");

// 7: What we measure — the people group
await page.goto(`${base}/what-we-measure`);
await page.locator('[data-group="people"]').waitFor();
await page.locator('[data-group="people"]').screenshot({ path: path.join(out, "07_measure_people_group.png") });
console.log("  07_measure_people_group.png");

// 8: How it works — the chances-of-matching account
await page.goto(`${base}/how-it-works#chances-of-matching`);
await page.locator("article.prose-method").waitFor();
await shot("08_how_it_works.png", { fullPage: true });

await browser.close();
console.log("done ->", out);
