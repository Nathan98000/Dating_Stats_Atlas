// Phase 7: the brief's measures that the review's scripts don't take, and its
// screenshots, against a local production build (BASE, default :3400).
//
//   R03  card #1's panel after a click on the card, at 1440x900 and 768x1024:
//        how many of its pixels show once the page is at rest, and its top
//   R08  at 390x844, scrolling down 0-160px in 2px steps: any position where
//        the bar shows while #1's score is below the bar's top edge
//   R09  rows (and Compare's two score cells) showing "/100"
//   R07  /robots.txt and /sitemap.xml, and a canonical link on every page
//        of the review's list (the 404 excepted)
// and the screenshots the brief lists, to ../screens/ (SHOTS, default
// ../screens relative to the current folder).
//
//   cd atlas/results/phase7/after && node ../../../web/scripts/review/phase7_measure.mjs
import { chromium } from "@playwright/test";
import { mkdirSync, writeFileSync } from "fs";
import path from "path";

const BASE = process.env.BASE || "http://127.0.0.1:3400";
const SHOTS = path.resolve(process.env.SHOTS || "../screens");
mkdirSync(SHOTS, { recursive: true });
const PAGES = {
  home: "/", "city-sf": "/city/san-francisco-california", "city-deltona": "/city/deltona-florida",
  "city-abilene": "/city/abilene-texas", "city-champaign": "/city/champaign-illinois", compare: "/compare",
  "compare-pair": "/compare/austin-texas/denver-colorado", "compare-floor": "/compare/austin-texas/abilene-texas",
  about: "/about", "what-we-measure": "/what-we-measure", "about-crime": "/about-crime-data",
  "stat-rent": "/stats/rent_1br", "stat-prices": "/stats/everyday_prices", "stat-lean": "/stats/political_lean",
  "stat-venues": "/stats/venues_per_100k", "stat-walk": "/stats/resident_walkability_index",
  "stat-days": "/stats/pleasant_days", "stat-students": "/stats/students_per_1k_adults",
  "stat-people": "/stats/who_lives_here", privacy: "/privacy", terms: "/terms",
};
const PHONE = { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true };
const out = {};
const browser = await chromium.launch();

async function ctxPage(opts) {
  const ctx = await browser.newContext(opts);
  const page = await ctx.newPage();
  return { ctx, page };
}
async function home(page, qs = "") {
  await page.goto(BASE + "/" + qs);
  await page.locator('li[data-rank="1"]').waitFor();
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
}
async function rest(page) {
  let last = -1;
  for (let i = 0; i < 40; i++) {
    const y = await page.evaluate(() => window.scrollY);
    if (y === last) return;
    last = y;
    await page.waitForTimeout(150);
  }
}

// R03
out.r03 = {};
for (const [w, h] of [[1440, 900], [768, 1024]]) {
  const { ctx, page } = await ctxPage({ viewport: { width: w, height: h } });
  await home(page);
  await page.locator('li[data-rank="1"]').getByTestId("card-body").click({ position: { x: 8, y: 60 } });
  await page.getByTestId("card-detail").waitFor();
  await page.waitForTimeout(100);
  await rest(page);
  const r = await page.getByTestId("card-detail").evaluate((el) => el.getBoundingClientRect().toJSON());
  out.r03[`${w}x${h}`] = { panel_top: Math.round(r.top), panel_bottom: Math.round(r.bottom), panel_height: Math.round(r.height),
    visible_px: Math.round(Math.max(0, Math.min(r.bottom, h) - Math.max(r.top, 0))),
    whole_panel_in_view: r.top >= 0 && r.bottom <= h + 0.5, scrollY: await page.evaluate(() => window.scrollY) };
  if (w === 1440) await page.screenshot({ path: path.join(SHOTS, "home-1440-card-open.png") });
  await ctx.close();
}

// R08
{
  const { ctx, page } = await ctxPage(PHONE);
  await home(page);
  const steps = [];
  for (let y = 0; y <= 160; y += 2) {
    await page.evaluate((y) => window.scrollTo(0, y), y);
    await page.waitForTimeout(60);
    steps.push(await page.evaluate(() => {
      const bar = document.querySelector('[data-testid="bottom-bar"]');
      const score = document.querySelector('[data-testid="featured-card"] [data-testid="card-score"]');
      const r = bar.getBoundingClientRect();
      const barTop = window.innerHeight - bar.offsetHeight;
      return { y: Math.round(window.scrollY), shown: r.top < window.innerHeight - 1,
        score_bottom: Math.round(score.getBoundingClientRect().bottom), bar_top: barTop };
    }));
  }
  const covering = steps.filter((s) => s.shown && s.score_bottom > s.bar_top);
  const first = steps.find((s) => s.shown);
  out.r08 = { positions: steps.length, bar_over_score: covering.length, first_shown_at_scroll: first?.y ?? null,
    score_bottom_then: first?.score_bottom ?? null, bar_top: first?.bar_top ?? null };
  await page.evaluate((y) => window.scrollTo(0, y), (first?.y ?? 60) + 10);
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(SHOTS, "home-390-bar-first-scroll.png") });
  await ctx.close();
}

// R09
out.r09 = {};
for (const [label, opts] of [["1440", { viewport: { width: 1440, height: 900 } }], ["390", PHONE]]) {
  const { ctx, page } = await ctxPage(opts);
  await home(page);
  await page.getByTestId("show-all").click();
  await page.waitForTimeout(500);
  out.r09[label] = await page.evaluate(() => {
    const rows = [...document.querySelectorAll('ol[aria-label="More cities"] > li')];
    return { rows: rows.length, with_out_of_100: rows.filter((r) => r.querySelector('[data-testid="score-out-of"]')?.textContent === "/100").length };
  });
  await ctx.close();
}
{
  const { ctx, page } = await ctxPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(BASE + "/compare/austin-texas/denver-colorado");
  out.r09.compare = await page.getByTestId("compare-score").allInnerTexts();
  out.r14 = {
    who_lives_here: (await page.locator('[data-diff-for="who_lives_here"]').innerText()).trim(),
    balance: (await page.locator('[data-diff-for="balance"]').innerText()).trim(),
  };
  await page.screenshot({ path: path.join(SHOTS, "compare-1440-austin-denver.png"), fullPage: true });
  await ctx.close();
}

// R07
{
  const { ctx, page } = await ctxPage({ viewport: { width: 1440, height: 900 } });
  const robots = await page.request.get(BASE + "/robots.txt");
  const sitemap = await page.request.get(BASE + "/sitemap.xml");
  const xml = await sitemap.text();
  const canon = {};
  for (const [label, p] of Object.entries(PAGES)) {
    await page.goto(BASE + p);
    canon[label] = await page.locator('link[rel="canonical"]').getAttribute("href").catch(() => null);
  }
  await page.goto(BASE + "/no-such-page");
  out.r07 = { robots: [robots.status(), robots.headers()["content-type"]], sitemap: [sitemap.status(), sitemap.headers()["content-type"]],
    sitemap_urls: (xml.match(/<loc>/g) ?? []).length, sitemap_city_urls: (xml.match(/<loc>[^<]*\/city\//g) ?? []).length,
    pages: Object.keys(PAGES).length, pages_with_canonical: Object.values(canon).filter(Boolean).length,
    canonical_404: await page.locator('link[rel="canonical"]').count(), canonical: canon };
  await ctx.close();
}

// screenshots: a row's detail with the item sub-rows; a cold city page; the
// city page's two buttons; San Jose's card and band
{
  const { ctx, page } = await ctxPage({ viewport: { width: 1440, height: 900 } });
  await home(page, "?ic=a&iw=a&ir=n");
  const li = page.locator('li[data-slug="austin-texas"]');
  const card = (await li.getAttribute("data-testid")) === "featured-card";
  await li.getByTestId(card ? "card-toggle" : "row-toggle").locator("visible=true").click();
  await page.waitForTimeout(600);
  await rest(page);
  await (card ? page.getByTestId("card-detail") : li.getByTestId("row-detail")).screenshot({ path: path.join(SHOTS, "detail-1440-austin-items.png") });
  await page.goto(BASE + "/city/virginia-beach-virginia");
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: path.join(SHOTS, "city-1440-virginia-beach-cold.png") });
  await page.goto(BASE + "/city/austin-texas?ic=a");
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: path.join(SHOTS, "city-1440-austin-buttons.png"), clip: { x: 0, y: 0, width: 1440, height: 420 } });
  await page.goto(BASE + "/city/san-jose-california");
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);
  const band = page.getByTestId("city-photo");
  await band.scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  await band.screenshot({ path: path.join(SHOTS, "city-1440-san-jose-band.png") });
  await ctx.close();
}
for (const [label, opts] of [["1440", { viewport: { width: 1440, height: 900 } }], ["390", PHONE]]) {
  const { ctx, page } = await ctxPage(opts);
  await home(page);
  const sj = page.locator('li[data-slug="san-jose-california"]');
  if ((await sj.getAttribute("data-testid")) !== "featured-card") {
    // San Jose is #5 by default; men with a graduate degree put it first
    await home(page, "?edu=graduate");
  }
  const el = page.locator('li[data-slug="san-jose-california"]');
  await el.scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);
  await el.screenshot({ path: path.join(SHOTS, `card-${label}-san-jose.png`) });
  await ctx.close();
}
{
  const { ctx, page } = await ctxPage(PHONE);
  await page.goto(BASE + "/city/virginia-beach-virginia");
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: path.join(SHOTS, "city-390-virginia-beach-cold.png") });
  await page.goto(BASE + "/compare/austin-texas/denver-colorado");
  await page.screenshot({ path: path.join(SHOTS, "compare-390-austin-denver.png") });
  await home(page);
  await page.getByTestId("age-token").focus();
  await page.keyboard.press("Tab");
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(SHOTS, "home-390-keyboard-bar.png") });
  await ctx.close();
}
await browser.close();
writeFileSync("phase7_measure.json", JSON.stringify(out, null, 1) + "\n");
console.log(JSON.stringify({ r03: out.r03, r08: out.r08, r09: out.r09, r14: out.r14,
  r07: { ...out.r07, canonical: undefined } }, null, 1));
