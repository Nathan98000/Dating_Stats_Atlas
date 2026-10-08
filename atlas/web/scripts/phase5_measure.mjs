// Phase 5's before/after measurements of the home page, the city page, a
// compare pair and About: where the #1 result sits, page and row heights,
// horizontal overflow, /api/rank's transfer, axe counts, and screenshots.
//
//   node scripts/phase5_measure.mjs <base url> <label>
//     -> ../results/phase5/measure_<label>.json, ../results/phase5/screens/<label>/*.png
//
// Run against a production build (next start) on the real build's API.
import AxeBuilder from "@axe-core/playwright";
import { chromium, devices } from "@playwright/test";
import { mkdirSync, writeFileSync } from "fs";
import path from "path";
import { gzipSync } from "zlib";

const [base, label] = process.argv.slice(2);
if (!base || !label) throw new Error("usage: phase5_measure.mjs <base url> <label>");
const OUT = path.resolve(import.meta.dirname, "..", "..", "results", "phase5");
const SHOTS = path.join(OUT, "screens", label);
mkdirSync(SHOTS, { recursive: true });

const VIEWPORTS = [
  { name: "1440", viewport: { width: 1440, height: 900 } },
  { name: "1024", viewport: { width: 1024, height: 768 } },
  { name: "768", viewport: { width: 768, height: 1024 } },
  { name: "390", ...devices["iPhone 13"], viewport: { width: 390, height: 844 } },
];
const DEFAULT_BODY = {
  self: { age: 30 },
  seeking: { sex: "male", age: [28, 40], marital: ["never_married", "previously_married"] },
  sort: "best_first",
};

const browser = await chromium.launch();
const out = { label, base, generated: new Date().toISOString(), home: {}, pages: {}, axe: {} };

async function open(vp) {
  const { name, ...opts } = vp;
  const ctx = await browser.newContext({ ...opts, reducedMotion: "reduce" });
  const page = await ctx.newPage();
  return { ctx, page };
}

const settle = async (page) => {
  await page.waitForLoadState("networkidle");
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(250);
};

let slugs = [];
for (const vp of VIEWPORTS) {
  const { ctx, page } = await open(vp);
  await page.goto(`${base}/`);
  await settle(page);
  const m = await page.evaluate(() => {
    const first = document.querySelector('[data-rank="1"]');
    const rows = [...document.querySelectorAll("li[data-rank]")]
      .filter((li) => { const r = Number(li.getAttribute("data-rank")); return r >= 4 && r <= 10; })
      .map((li) => Math.round(li.getBoundingClientRect().height));
    return {
      first_result_top: first ? Math.round(first.getBoundingClientRect().top + window.scrollY) : null,
      first_result_bottom: first ? Math.round(first.getBoundingClientRect().bottom + window.scrollY) : null,
      page_height: document.documentElement.scrollHeight,
      scroll_width: document.documentElement.scrollWidth,
      rows_4_10_height: rows,
      slugs: [...document.querySelectorAll("[data-slug]")].slice(0, 2).map((e) => e.getAttribute("data-slug")),
    };
  });
  slugs = m.slugs;
  delete m.slugs;
  out.home[vp.name] = m;
  await page.screenshot({ path: path.join(SHOTS, `home-${vp.name}-top.png`) });
  await page.evaluate(() => window.scrollTo(0, Math.round(window.innerHeight * 1.2)));
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(SHOTS, `home-${vp.name}-scrolled.png`) });
  // a row expanded (the redesign's detail; the old rows have none)
  const toggle = page.locator('li[data-rank="4"] button[aria-expanded]').first();
  if (await toggle.count()) {
    await toggle.click();
    await page.waitForTimeout(300);
    await page.locator('li[data-rank="4"]').scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(SHOTS, `home-${vp.name}-expanded.png`) });
    out.home[vp.name].expanded_shot = true;
  }
  if (vp.name === "390") {
    const adjust = page.getByRole("button", { name: "Adjust your search" });
    if (await adjust.count()) {
      await page.evaluate(() => window.scrollTo(0, 2000));
      await page.waitForTimeout(300);
      await adjust.click();
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(SHOTS, `sheet-390.png`) });
      out.home[vp.name].sheet_shot = true;
    }
  }
  await ctx.close();
}

const PAGES = {
  home: "/",
  city: `/city/${slugs[0]}`,
  compare_pair: `/compare/${slugs[0]}/${slugs[1]}`,
  compare: "/compare",
  about: "/about",
  stat: "/stats/rent_1br",
  privacy: "/privacy",
  terms: "/terms",
  not_found: "/no-such-page",
};
for (const vp of [VIEWPORTS[0], VIEWPORTS[3]]) {
  const { ctx, page } = await open(vp);
  for (const [name, url] of Object.entries(PAGES)) {
    await page.goto(`${base}${url}`);
    await settle(page);
    const info = await page.evaluate(() => ({
      title: document.title,
      scroll_width: document.documentElement.scrollWidth,
      page_height: document.documentElement.scrollHeight,
      main: document.querySelectorAll("main").length,
    }));
    out.pages[`${name}@${vp.name}`] = { url, ...info };
    if (["city", "compare_pair", "about"].includes(name)) {
      await page.screenshot({ path: path.join(SHOTS, `${name}-${vp.name}.png`) });
    }
    const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"]).analyze();
    const count = (imp) => axe.violations.filter((v) => v.impact === imp).reduce((n, v) => n + v.nodes.length, 0);
    out.axe[`${name}@${vp.name}`] = {
      critical: count("critical"), serious: count("serious"),
      moderate: count("moderate"), minor: count("minor"),
      rules: axe.violations.map((v) => `${v.id} (${v.impact}, ${v.nodes.length})`),
    };
  }
  await ctx.close();
}

const r = await fetch(`${base}/api/rank`, {
  method: "POST",
  headers: { "content-type": "application/json", "accept-encoding": "identity" },
  body: JSON.stringify(DEFAULT_BODY),
});
const raw = Buffer.from(await r.arrayBuffer());
out.api_rank = { bytes: raw.length, gzip6_bytes: gzipSync(raw, { level: 6 }).length };

await browser.close();
writeFileSync(path.join(OUT, `measure_${label}.json`), JSON.stringify(out, null, 1) + "\n");
console.log(JSON.stringify({ home: out.home, api_rank: out.api_rank }, null, 1));
console.log(Object.entries(out.axe).map(([k, v]) => `${k}: ${v.critical}c ${v.serious}s ${v.moderate}m ${v.minor}n ${v.rules.join("; ")}`).join("\n"));
