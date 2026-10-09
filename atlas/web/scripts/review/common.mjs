// Shared setup for the round-3 review's measurements (Phase 6 review, 8 October 2026).
// Runs against a local production build: `next start` on :3300 over the API on build
// 63c4e5fa51bf. Playwright from atlas/web, driving its own Chromium.
// Ported to this Mac in Phase 6 (commit R): bare imports resolve from atlas/web/node_modules;
// each script writes its output to the current directory, so run it from the output folder.
import { chromium } from "@playwright/test";

export const BASE = process.env.BASE || "http://localhost:3300";
export const launch = () => chromium.launch();

export const PERMALINK =
  "/r/63c4e5fa51bf/m4.2.1/eyJpbXBvcnRhbmNlIjp7ImNvc3QiOiJzb21lIiwicmVhY2giOiJzb21lIiwic3R1ZGVudHMiOiJzb21lIiwid2VhdGhlciI6InNvbWUifSwicG9vbF92c19tYXRjaCI6MC40NTQ1LCJzZWVraW5nIjp7ImFnZSI6WzI4LDQwXSwibWFyaXRhbCI6WyJuZXZlcl9tYXJyaWVkIiwicHJldmlvdXNseV9tYXJyaWVkIl0sInNleCI6Im1hbGUifSwic2VsZiI6eyJhZ2UiOjMwfX0";

export const PAGES = {
  home: "/",
  "city-sf": "/city/san-francisco-california",
  "city-deltona": "/city/deltona-florida",
  "city-abilene": "/city/abilene-texas",
  "city-champaign": "/city/champaign-illinois",
  compare: "/compare",
  "compare-pair": "/compare/austin-texas/denver-colorado",
  "compare-floor": "/compare/austin-texas/abilene-texas",
  about: "/about",
  "what-we-measure": "/what-we-measure",
  "about-crime": "/about-crime-data",
  "stat-rent": "/stats/rent_1br",
  "stat-prices": "/stats/everyday_prices",
  "stat-lean": "/stats/political_lean",
  "stat-venues": "/stats/venues_per_100k",
  privacy: "/privacy",
  terms: "/terms",
  permalink: PERMALINK,
  "404": "/no-such-page",
};

export const VIEWPORTS = {
  1440: { viewport: { width: 1440, height: 900 } },
  1280: { viewport: { width: 1280, height: 720 } },
  1120: { viewport: { width: 1120, height: 800 } },
  1119: { viewport: { width: 1119, height: 800 } },
  1024: { viewport: { width: 1024, height: 768 } },
  768: { viewport: { width: 768, height: 1024 }, hasTouch: true },
  390: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true },
  320: { viewport: { width: 320, height: 640 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
};

export const settle = async (page, ms = 300) => {
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(ms);
};

export const kind = (url, type) => {
  const u = url.split("?")[0];
  if (type === "document") return "html";
  if (/\.woff2?$/.test(u)) return "font";
  if (/\.(jpe?g|png|webp|avif|gif|svg)$/.test(u)) return "image";
  if (/\.css$/.test(u)) return "css";
  if (/\.js$/.test(u)) return "js";
  if (u.includes("/api/")) return "api";
  if (type === "fetch" || type === "xhr") return "rsc/fetch";
  return type || "other";
};
