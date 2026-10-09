// Phase 6: the report's screenshots (atlas/PHASE6.md §4), at 1440 and 390 against a
// production build (BASE). Writes screens/<name>-<width>.png in the current directory.
//   node phase6_screens.mjs
import { launch, BASE, VIEWPORTS, settle } from "./common.mjs";
import { mkdirSync } from "fs";

const SAME_SEX = "/?self_age=33&sex=male&age=28-38&marital=never%2Cpreviously";
const shots = {
  "home-card-open": async (page) => {
    await page.goto(BASE + "/"); await settle(page, 400);
    await page.locator("[data-testid=card-toggle]").first().click(); await page.waitForTimeout(400);
    await page.locator("[data-testid=card-detail]").scrollIntoViewIfNeeded();
    await page.evaluate(() => window.scrollBy(0, -200));
  },
  // a man looking for men; Los Angeles's new photograph is the #3 card
  "home-same-sex": async (page) => {
    await page.goto(BASE + SAME_SEX); await settle(page, 400);
    await page.locator("[data-testid=list-heading]").scrollIntoViewIfNeeded();
    await page.evaluate(() => window.scrollBy(0, -120));
  },
  "home-sheet-summary": async (page) => {
    await page.goto(BASE + "/"); await settle(page, 400);
    if (page.viewportSize().width >= 1120) return "skip";
    await page.evaluate(() => window.scrollTo(0, 1500)); await page.waitForTimeout(400);
    await page.getByRole("button", { name: "Adjust your search" }).click(); await page.waitForTimeout(500);
  },
  "home-new-top-three": async (page) => {
    await page.goto(BASE + "/"); await settle(page, 400);
    const w = page.viewportSize().width;
    if (w < 1120) {
      await page.evaluate(() => window.scrollTo(0, 1500)); await page.waitForTimeout(400);
      await page.getByRole("button", { name: "Adjust your search" }).click(); await page.waitForTimeout(500);
    }
    const scope = w < 1120 ? page.locator("dialog[open]") : page.locator("[data-testid=rail]");
    for (const [name, level] of [["Cost of living importance", "A lot"], ["Weather importance", "A lot"],
                                 ["Social life importance", "Not much"]]) {
      await scope.getByRole("radiogroup", { name }).getByRole("radio", { name: level }).click();
      await page.waitForTimeout(150);
    }
    if (w < 1120) await page.getByTestId("show-results").click();
    await page.getByTestId("results-notice").filter({ hasText: /\S/ }).waitFor({ timeout: 20000 });
    await page.locator("[data-testid=list-heading]").scrollIntoViewIfNeeded();
    await page.evaluate(() => window.scrollBy(0, -80));
    await page.waitForTimeout(300);
  },
  "city-san-francisco": async (page) => { await page.goto(BASE + "/city/san-francisco-california"); await settle(page, 400); },
  "city-deltona": async (page) => {
    await page.goto(BASE + "/city/deltona-florida"); await settle(page, 400);
    await page.locator("[data-testid=photo-place]").scrollIntoViewIfNeeded();
  },
  "city-champaign": async (page) => { await page.goto(BASE + "/city/champaign-illinois"); await settle(page, 400); },
  "city-virginia-beach": async (page) => { await page.goto(BASE + "/city/virginia-beach-virginia"); await settle(page, 400); },
  "compare-austin-denver": async (page) => { await page.goto(BASE + "/compare/austin-texas/denver-colorado"); await settle(page, 400); },
  "compare-austin-abilene": async (page) => { await page.goto(BASE + "/compare/austin-texas/abilene-texas"); await settle(page, 400); },
  "stat-rent": async (page) => { await page.goto(BASE + "/stats/rent_1br"); await settle(page, 400); },
  "city-los-angeles": async (page) => { await page.goto(BASE + "/city/los-angeles-california"); await settle(page, 400);
    await page.locator("[data-testid=city-photo]").scrollIntoViewIfNeeded(); },
};

mkdirSync("screens", { recursive: true });
const browser = await launch();
for (const w of ["1440", "390"]) {
  for (const [name, go] of Object.entries(shots)) {
    const ctx = await browser.newContext(VIEWPORTS[w]);
    if (name === "home-same-sex") {
      await ctx.addInitScript(() => localStorage.setItem("dsa_about_you", JSON.stringify({ sex: "male" })));
    }
    const page = await ctx.newPage();
    const r = await go(page);
    if (r !== "skip") await page.screenshot({ path: `screens/${name}-${w}.png` });
    process.stdout.write(`${name}-${w}${r === "skip" ? " (skipped)" : ""}\n`);
    await ctx.close();
  }
}
await browser.close();
