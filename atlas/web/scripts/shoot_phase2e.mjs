/** Phase 2e report screenshots against the running dev stack.
 *
 *   node scripts/shoot_phase2e.mjs [base] [outDir]
 */
import { chromium } from "@playwright/test";
import path from "path";

const base = process.argv[2] ?? "http://localhost:3000";
const out = process.argv[3] ?? path.resolve("..", "results", "phase2e");

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

async function shot(name) {
  await page.screenshot({ path: path.join(out, name) });
  console.log("  " + name);
}

// 1: the rent stat page — image, strip, note, sort toggle
await page.goto(`${base}/stats/median_gross_rent`);
await page.getByTestId("stat-list").locator("li").first().waitFor();
await shot("01_rent_stat_page.png");

// 2: sorted the other way — same numbers, reversed
await page.getByTestId("stat-sort").getByRole("radio", { name: "Highest first" }).click();
await page.waitForTimeout(250);
await page.mouse.wheel(0, 300);
await shot("02_rent_highest_first.png");

// 3: city page — photograph with attribution, real map
await page.goto(`${base}/city/winston-salem-north-carolina`);
await page.getByTestId("locator-map").waitFor();
await shot("03_city_photo_and_map.png");

// 4: the crime cards with an open popover
await page.goto(`${base}/city/provo-utah?self_sex=female&self_age=30&age=28-40&marital=never,previously`);
const info = page.getByTestId("crime-info-violent_crime_rate");
await info.scrollIntoViewIfNeeded();
await info.hover();
await page.getByTestId("crime-info-violent_crime_rate-note").waitFor();
await shot("04_crime_cards_popover.png");

// 5: compare crime — plain numbers, one banner
await page.goto(`${base}/compare/provo-utah/austin-texas`);
await page.getByTestId("compare-crime").scrollIntoViewIfNeeded();
await page.waitForTimeout(250);
await shot("05_compare_crime_banner.png");

// 6: What we measure
await page.goto(`${base}/what-we-measure`);
await page.getByTestId("measure-crime").waitFor();
await shot("06_what_we_measure.png");

// 7: the eight-group panel
await page.goto(`${base}/`);
await page.getByTestId("ranked-list").locator("li").first().waitFor();
await page.getByTestId("race-panel").scrollIntoViewIfNeeded();
await page.waitForTimeout(250);
await shot("07_panel_eight_groups.png");

// 8: the compare picker finding New York
await page.goto(`${base}/compare`);
await page.getByLabel("First city").fill("new york");
await page.getByRole("option").first().waitFor();
await shot("08_picker_new_york.png");

await browser.close();
console.log("done ->", out);
