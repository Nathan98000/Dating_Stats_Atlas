/** Phase 2g report screenshots against the running dev stack.
 *
 *   node scripts/shoot_phase2g.mjs [base] [outDir]
 */
import { chromium } from "@playwright/test";
import path from "path";

const base = process.argv[2] ?? "http://localhost:3000";
const out = process.argv[3] ?? path.resolve("..", "results", "phase2g");
const BELOW_BAR =
  "/?self_sex=female&self_age=30&age=25-35&marital=never&edu=graduate&inc=250000&race=nhpi_nh";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

async function shot(name, opts = {}) {
  await page.screenshot({ path: path.join(out, name), ...opts });
  console.log("  " + name);
}

// 1: the couple hero with its CC0 credit
await page.goto(`${base}/`);
await page.getByTestId("ranked-list").locator("li").first().waitFor();
await shot("01_home_couple_hero.png");

// 2: the rent stat page — HUD source line, no caution box, HUD dollars
await page.goto(`${base}/stats/rent_1br`);
await page.getByTestId("stat-list").locator("li").first().waitFor();
await shot("02_rent_page_hud.png");

// 3: Austin's card in FY2027 dollars
await page.goto(`${base}/city/austin-texas?self_sex=female&self_age=30&age=28-40&marital=never,previously`);
await page.locator('[data-card="rent_1br"]').scrollIntoViewIfNeeded();
await page.waitForTimeout(250);
await shot("03_austin_rent_card.png");

// 4–5: the all-excluded screen at both widths (gate 7)
await page.goto(`${base}${BELOW_BAR}`);
await page.getByTestId("narrow-state").waitFor();
await shot("04_narrow_state_1280.png");
await page.setViewportSize({ width: 375, height: 812 });
await page.goto(`${base}${BELOW_BAR}`);
await page.getByTestId("narrow-state").scrollIntoViewIfNeeded();
await page.waitForTimeout(250);
await shot("05_narrow_state_375.png");
await page.setViewportSize({ width: 1280, height: 900 });

// 6: How it works — the rewrite with both corrections
await page.goto(`${base}/how-it-works`);
await page.locator("article.prose-method").waitFor();
await shot("06_how_it_works.png", { fullPage: true });

// 7: About the crime figures — the rewrite
await page.goto(`${base}/about-crime-data`);
await page.locator("article.prose-method").waitFor();
await shot("07_about_crime.png", { fullPage: true });

await browser.close();
console.log("done ->", out);
