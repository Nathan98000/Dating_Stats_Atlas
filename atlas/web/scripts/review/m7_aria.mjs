// m7: the accessibility tree, as a screen reader would walk it (Playwright ARIA snapshots):
// the home page's header, hero, results header, first card, a row collapsed and expanded,
// the sheet at 390, a city page's score card, and the compare table's first rows.
//   node m7_aria.mjs -> m7_aria.txt
import { launch, BASE, VIEWPORTS, settle } from "./common.mjs";
import { writeFileSync } from "fs";

const browser = await launch();
let txt = "";
const add = (h, s) => { txt += `\n===== ${h}\n${s}\n`; };
{
  const ctx = await browser.newContext(VIEWPORTS["1440"]);
  const page = await ctx.newPage();
  await page.goto(BASE + "/"); await settle(page, 400);
  add("1440 banner", await page.getByRole("banner").first().ariaSnapshot());
  add("1440 hero", await page.locator("[data-testid=hero]").ariaSnapshot());
  add("1440 rail", await page.locator("[data-testid=search-panel]").ariaSnapshot());
  add("1440 results header", await page.locator("section[aria-labelledby=results-heading] > *").first().ariaSnapshot());
  add("1440 card #1", await page.locator("[data-testid=featured-card]").first().ariaSnapshot());
  add("1440 row #4 collapsed", await page.locator('li[data-rank="4"]').ariaSnapshot());
  await page.locator('li[data-rank="4"] [data-testid=row-toggle]').locator("visible=true").first().click();
  await page.waitForTimeout(300);
  add("1440 row #4 expanded", await page.locator('li[data-rank="4"]').ariaSnapshot());
  add("1440 how the score works", await page.locator("[data-testid=score-explainer]").ariaSnapshot());
  await ctx.close();
}
{
  const ctx = await browser.newContext(VIEWPORTS["390"]);
  const page = await ctx.newPage();
  await page.goto(BASE + "/"); await settle(page, 400);
  await page.evaluate(() => window.scrollTo(0, 1500)); await page.waitForTimeout(400);
  await page.getByRole("button", { name: "Adjust your search" }).tap(); await page.waitForTimeout(500);
  add("390 sheet", await page.locator("dialog[open]").ariaSnapshot());
  await ctx.close();
}
{
  const ctx = await browser.newContext(VIEWPORTS["1440"]);
  const page = await ctx.newPage();
  await page.goto(BASE + "/city/san-francisco-california"); await settle(page, 400);
  add("city SF main (first 120 lines)", (await page.locator("main").ariaSnapshot()).split("\n").slice(0, 120).join("\n"));
  await page.goto(BASE + "/compare/austin-texas/denver-colorado"); await settle(page, 400);
  add("compare pair main (first 120 lines)", (await page.locator("main").ariaSnapshot()).split("\n").slice(0, 120).join("\n"));
  await ctx.close();
}
await browser.close();
writeFileSync("m7_aria.txt", txt);
console.log(txt.length);
