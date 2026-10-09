// m2: speed. Largest contentful paint, layout shift, first paint, and the delay after a
// weight change before the list settles.
//  - 390x844 phone, touch, with Lighthouse's mobile profile: 150ms RTT, 1.6 Mbps down,
//    750 kbps up (Chrome DevTools network emulation) and 4x CPU slowdown;
//  - 1440x900 unthrottled.
// Each run is a cold context (empty cache). Five runs per condition; medians reported.
// The weight change is "Cost of living: A lot" — in the rail at 1440, in the sheet at 390.
//   node m2_speed.mjs [base]   -> m2_speed[_label].json
import { launch } from "./common.mjs";
import { writeFileSync } from "fs";

const BASE = process.argv[2] || "http://localhost:3300";
const LABEL = process.argv[3] || "local";
const RUNS = Number(process.env.RUNS || 5);
const browser = await launch();

const INIT = () => {
  window.__perf = { lcp: [], cls: 0, shifts: [], fcp: null };
  new PerformanceObserver((l) => {
    for (const e of l.getEntries())
      window.__perf.lcp.push({ t: e.startTime, size: e.size, el: e.element ? (e.element.tagName + "." + String(e.element.className).slice(0, 40) + " " + (e.element.currentSrc || e.element.innerText || "").slice(0, 60)) : e.url });
  }).observe({ type: "largest-contentful-paint", buffered: true });
  new PerformanceObserver((l) => {
    for (const e of l.getEntries()) if (!e.hadRecentInput) {
      window.__perf.cls += e.value;
      window.__perf.shifts.push({ t: Math.round(e.startTime), v: +e.value.toFixed(4), src: (e.sources || []).map((s) => s.node ? (s.node.nodeName + "." + String(s.node.className || "").slice(0, 30)) : "?").slice(0, 3) });
    }
  }).observe({ type: "layout-shift", buffered: true });
  new PerformanceObserver((l) => {
    for (const e of l.getEntries()) if (e.name === "first-contentful-paint") window.__perf.fcp = e.startTime;
  }).observe({ type: "paint", buffered: true });
};

async function run(cond) {
  const phone = cond === "390";
  const ctx = await browser.newContext(phone
    ? { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true }
    : { viewport: { width: 1440, height: 900 } });
  await ctx.addInitScript(INIT);
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  if (phone) {
    await cdp.send("Network.enable");
    await cdp.send("Network.emulateNetworkConditions", {
      offline: false, latency: 150, downloadThroughput: (1638.4 * 1024) / 8, uploadThroughput: (750 * 1024) / 8,
    });
    await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
  }
  const rankSizes = [];
  page.on("requestfinished", async (r) => {
    if (r.url().includes("/api/rank")) {
      const s = await r.sizes(); const t = r.timing();
      rankSizes.push({ body: s.responseBodySize, ms: Math.round(t.responseEnd) });
    }
  });
  const t0 = Date.now();
  await page.goto(BASE + "/", { waitUntil: "load", timeout: 120000 });
  const loadMs = Date.now() - t0;
  await page.waitForLoadState("networkidle", { timeout: 120000 }).catch(() => {});
  await page.waitForTimeout(1500);
  // a tap/click ends LCP; read it first
  const perf = await page.evaluate(() => window.__perf);
  const nav = await page.evaluate(() => {
    const n = performance.getEntriesByType("navigation")[0];
    return { ttfb: Math.round(n.responseStart), dcl: Math.round(n.domContentLoadedEventEnd), load: Math.round(n.loadEventEnd) };
  });

  // the weight change
  let control;
  if (phone) {
    await page.evaluate(() => window.scrollTo(0, 1400));
    await page.waitForTimeout(600);
    await page.getByRole("button", { name: "Adjust your search" }).tap();
    await page.waitForTimeout(800);
    control = page.locator('dialog[open] [aria-label="Cost of living importance"]').getByText("A lot");
  } else {
    control = page.locator('[data-testid=search-panel] [aria-label="Cost of living importance"]').getByText("A lot").first();
  }
  await page.evaluate(() => {
    const sec = document.querySelector("section[aria-labelledby=results-heading]");
    const list = document.querySelector("[data-testid=ranked-list]");
    window.__chg = { muts: [], busyOn: null, busyOff: null, live: null, firstName: null };
    new MutationObserver(() => window.__chg.muts.push(performance.now())).observe(list, { childList: true, subtree: true, characterData: true });
    new MutationObserver(() => {
      const b = sec.getAttribute("aria-busy") === "true";
      if (b && window.__chg.busyOn == null) window.__chg.busyOn = performance.now();
      if (!b && window.__chg.busyOn != null && window.__chg.busyOff == null) window.__chg.busyOff = performance.now();
    }).observe(sec, { attributes: true, attributeFilter: ["aria-busy"] });
    const live = document.querySelector("[data-testid=results-live]");
    new MutationObserver(() => { if (window.__chg.live == null) window.__chg.live = performance.now(); }).observe(live, { childList: true, subtree: true, characterData: true });
    document.addEventListener("pointerdown", (e) => { window.__chg.down = e.timeStamp; }, { capture: true, once: true });
    document.addEventListener("touchstart", (e) => { window.__chg.down = window.__chg.down ?? e.timeStamp; }, { capture: true, once: true });
  });
  if (phone) await control.tap(); else await control.click();
  await page.waitForFunction(() => window.__chg.busyOff != null, null, { timeout: 120000 }).catch(() => {});
  await page.waitForTimeout(1500);
  const chg = await page.evaluate(() => {
    const c = window.__chg; const down = c.down ?? null;
    const last = c.muts.length ? Math.max(...c.muts) : null;
    const anims = document.getAnimations().length;
    return {
      to_pending_ms: c.busyOn != null && down != null ? Math.round(c.busyOn - down) : null,
      to_response_ms: c.busyOff != null && down != null ? Math.round(c.busyOff - down) : null,
      to_live_ms: c.live != null && down != null ? Math.round(c.live - down) : null,
      to_last_list_mutation_ms: last != null && down != null ? Math.round(last - down) : null,
      mutations: c.muts.length, anims_after: anims,
    };
  });
  const lcp = perf.lcp.length ? perf.lcp[perf.lcp.length - 1] : null;
  await ctx.close();
  return {
    load_ms_wall: loadMs, ...nav, fcp: perf.fcp && Math.round(perf.fcp), lcp: lcp && Math.round(lcp.t), lcp_el: lcp && lcp.el,
    lcp_candidates: perf.lcp.map((e) => `${Math.round(e.t)}ms ${e.el}`),
    cls: +perf.cls.toFixed(4), shifts: perf.shifts, change: chg, rank_requests: rankSizes,
  };
}

const med = (a) => { const s = a.filter((x) => x != null).sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : null; };
const out = { base: BASE, label: LABEL, runs: RUNS, generated: new Date().toISOString(), conditions: {} };
for (const cond of ["1440", "390"]) {
  const runs = [];
  for (let i = 0; i < RUNS; i++) { runs.push(await run(cond)); process.stdout.write(`${cond} run ${i + 1}: lcp ${runs.at(-1).lcp} cls ${runs.at(-1).cls} settle ${runs.at(-1).change.to_response_ms}\n`); }
  out.conditions[cond] = {
    median: {
      ttfb: med(runs.map((r) => r.ttfb)), fcp: med(runs.map((r) => r.fcp)), lcp: med(runs.map((r) => r.lcp)),
      load: med(runs.map((r) => r.load)), cls: med(runs.map((r) => r.cls)),
      change_to_pending: med(runs.map((r) => r.change.to_pending_ms)),
      change_to_response: med(runs.map((r) => r.change.to_response_ms)),
      change_to_last_mutation: med(runs.map((r) => r.change.to_last_list_mutation_ms)),
    },
    runs,
  };
}
await browser.close();
writeFileSync(`m2_speed_${LABEL}.json`, JSON.stringify(out, null, 1));
console.log(JSON.stringify(Object.fromEntries(Object.entries(out.conditions).map(([k, v]) => [k, v.median])), null, 1));
