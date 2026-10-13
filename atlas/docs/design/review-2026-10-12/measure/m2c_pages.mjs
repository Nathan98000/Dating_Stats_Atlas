// Round 4 (12 October 2026): largest paint and layout shift on the pages round 3 timed
// only for weight: a city page (San Francisco), a compare pair and a stat page. 390 on the
// slow-phone profile (150 ms RTT, 1.6 Mbps down, 750 kbps up, 4x CPU) and 1440 unthrottled,
// cold contexts. RUNS (default 3) per page and condition; medians reported.
//   node m2c_pages.mjs [base] [label]  -> m2c_pages_<label>.json
import { launch } from "./common.mjs";
import { writeFileSync } from "fs";

const BASE = process.argv[2] || "http://127.0.0.1:3400";
const LABEL = process.argv[3] || "local";
const RUNS = Number(process.env.RUNS || 3);
const PAGES = { "city-sf": "/city/san-francisco-california", "compare-pair": "/compare/austin-texas/denver-colorado", "stat-rent": "/stats/rent_1br" };
const INIT = () => {
  window.__p = { lcp: [], cls: 0, fcp: null };
  new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__p.lcp.push({ t: e.startTime, el: e.element ? e.element.tagName + " " + (e.element.currentSrc || e.element.innerText || "").slice(0, 50) : e.url }); }).observe({ type: "largest-contentful-paint", buffered: true });
  new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__p.cls += e.value; }).observe({ type: "layout-shift", buffered: true });
  new PerformanceObserver((l) => { for (const e of l.getEntries()) if (e.name === "first-contentful-paint") window.__p.fcp = e.startTime; }).observe({ type: "paint", buffered: true });
};
const browser = await launch();
const med = (a) => { const s = a.filter((x) => x != null).sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : null; };
const out = { base: BASE, label: LABEL, runs: RUNS, generated: new Date().toISOString(), pages: {} };
for (const [name, path] of Object.entries(PAGES)) {
  for (const cond of ["1440", "390"]) {
    const runs = [];
    for (let i = 0; i < RUNS; i++) {
      const phone = cond === "390";
      const ctx = await browser.newContext(phone ? { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true } : { viewport: { width: 1440, height: 900 } });
      await ctx.addInitScript(INIT);
      const page = await ctx.newPage();
      if (phone) {
        const cdp = await ctx.newCDPSession(page);
        await cdp.send("Network.enable");
        await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: (1638.4 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 });
        await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
      }
      await page.goto(BASE + path, { waitUntil: "load", timeout: 120000 });
      await page.waitForLoadState("networkidle", { timeout: 120000 }).catch(() => {});
      await page.waitForTimeout(1500);
      const p = await page.evaluate(() => window.__p);
      const ttfb = await page.evaluate(() => Math.round(performance.getEntriesByType("navigation")[0].responseStart));
      const lcp = p.lcp.at(-1);
      runs.push({ ttfb, fcp: p.fcp && Math.round(p.fcp), lcp: lcp && Math.round(lcp.t), lcp_el: lcp && lcp.el, cls: +p.cls.toFixed(4) });
      await ctx.close();
      process.stdout.write(`${name}@${cond} run ${i + 1}: lcp ${runs.at(-1).lcp} (${runs.at(-1).lcp_el}) cls ${runs.at(-1).cls}\n`);
    }
    out.pages[`${name}@${cond}`] = { median: { ttfb: med(runs.map((r) => r.ttfb)), fcp: med(runs.map((r) => r.fcp)), lcp: med(runs.map((r) => r.lcp)), cls: med(runs.map((r) => r.cls)) }, runs };
  }
}
await browser.close();
writeFileSync(`m2c_pages_${LABEL}.json`, JSON.stringify(out, null, 1));
console.log(JSON.stringify(Object.fromEntries(Object.entries(out.pages).map(([k, v]) => [k, v.median])), null, 1));
