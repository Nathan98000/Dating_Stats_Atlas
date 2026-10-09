/** Phase 6 (F31): the home page's link-preview image, public/og/home.png —
 * 1200x630, the site's headline (the registry's home_title) set in
 * Fraunces on --paper, with the site's name above it. No
 * photograph, so no credit. Made by screenshotting a small page laid out
 * over the running site (BASE, default http://localhost:3300), which
 * supplies the two web fonts as next/font serves them; the strings are the
 * registry's (API, default http://127.0.0.1:8000). The PNG is committed.
 *
 *     node scripts/og_home.mjs
 */
import { chromium } from "@playwright/test";
import { mkdirSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const here = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(here, "..", "public", "og", "home.png");
const BASE = process.env.BASE ?? "http://localhost:3300";
const API = process.env.API ?? "http://127.0.0.1:8000";

const meta = await (await fetch(`${API}/v1/meta`)).json();
const s = meta.policy_strings;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
// the 404 page: the site's fonts and tokens, little else to clear away
await page.goto(`${BASE}/no-such-page`, { waitUntil: "networkidle" });
await page.evaluate(({ site, title }) => {
  document.body.innerHTML = "";
  document.body.style.margin = "0";
  const card = document.createElement("div");
  card.style.cssText = "box-sizing:border-box;width:1200px;height:630px;background:var(--paper);"
    + "padding:84px 96px;display:flex;flex-direction:column;justify-content:space-between;";
  const brand = document.createElement("div");
  brand.textContent = site;
  brand.style.cssText = "font-family:var(--font-fraunces),Georgia,serif;font-variation-settings:'SOFT' 30;"
    + "font-weight:600;font-size:34px;letter-spacing:-0.01em;color:var(--ink);";
  const head = document.createElement("div");
  head.textContent = title;
  head.style.cssText = "font-family:var(--font-fraunces),Georgia,serif;font-variation-settings:'SOFT' 30;"
    + "font-weight:600;font-size:88px;line-height:96px;letter-spacing:-0.02em;color:var(--ink);max-width:960px;";
  const rule = document.createElement("div");
  rule.style.cssText = "width:120px;height:8px;border-radius:999px;background:var(--accent);";
  card.append(brand, head, rule);
  document.body.append(card);
}, { site: s.title_site, title: s.home_title });
await page.evaluate(() => document.fonts.ready);
await page.waitForTimeout(300);
mkdirSync(path.dirname(OUT), { recursive: true });
await page.screenshot({ path: OUT, clip: { x: 0, y: 0, width: 1200, height: 630 } });
await browser.close();
console.log(`og image -> ${path.relative(path.join(here, ".."), OUT)}`);
