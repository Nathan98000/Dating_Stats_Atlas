/** Phase 2d report screenshots against the running dev stack (full
 * build): the new surfaces, in the state the report describes.
 *
 *   node scripts/shoot_phase2d.mjs [base] [outDir]
 */
import { chromium } from "@playwright/test";
import path from "path";

const base = process.argv[2] ?? "http://localhost:3000";
const out = process.argv[3] ?? path.resolve("..", "results", "phase2d");

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

async function shot(name, clip) {
  await page.screenshot({ path: path.join(out, name), ...(clip ?? {}) });
  console.log("  " + name);
}

// 1: home with the four importance controls and the sticky panel
await page.goto(`${base}/?self_sex=female&self_age=30&age=28-40&marital=never,previously`);
await page.getByTestId("ranked-list").locator("li").first().waitFor();
await page.mouse.wheel(0, 520);
await page.waitForTimeout(400);
await shot("01_panel_four_controls.png");

// 2: the slider info note, open
await page.mouse.wheel(0, -2000);
await page.waitForTimeout(300);
await page.getByTestId("slider-info").hover();
await page.getByTestId("slider-info-note").waitFor();
await shot("02_slider_info.png");

// 3: city page — artwork, five-band cards, stat links
await page.goto(`${base}/city/provo-utah?self_sex=female&self_age=30&age=28-40&marital=never,previously`);
await page.getByTestId("city-art").waitFor();
await shot("03_city_art_and_cards.png", { fullPage: false });

// 4: the crime section on the city page
await page.getByTestId("crime-section").scrollIntoViewIfNeeded();
await page.waitForTimeout(300);
await shot("04_city_crime.png");

// 5: compare with the between-columns crime note
await page.goto(`${base}/compare/provo-utah/austin-texas?self_sex=female&self_age=30&age=28-40&marital=never,previously`);
await page.getByTestId("compare-crime").scrollIntoViewIfNeeded();
await page.waitForTimeout(300);
await shot("05_compare_crime_note.png");

// 6: a stat page
await page.goto(`${base}/stats/median_gross_rent`);
await page.getByTestId("stat-list").waitFor();
await shot("06_stat_page_rent.png");

// 7: How it works, restructured
await page.goto(`${base}/how-it-works`);
await page.locator("article.prose-method h2").first().waitFor();
await shot("07_how_it_works.png");

// 8: compare landing with pickers
await page.goto(`${base}/compare`);
await page.getByLabel("First city").waitFor();
await shot("08_compare_landing.png");

await browser.close();
console.log("done ->", out);
