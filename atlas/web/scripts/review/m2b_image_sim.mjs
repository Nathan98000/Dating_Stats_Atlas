// m2b: what the phone's largest paint would be with right-sized photographs. Same profile
// as m2 (390x844, 150ms RTT, 1.6 Mbps, 4x CPU), through the gzip stand-in (:3301), with
// every /cities/*.jpg answered by img_proxy.mjs (:3302) with a 720px-wide WebP at quality 72
// (the size a 356px card slot needs at 2x). A simulation of the recommendation only.
//   node m2b_image_sim.mjs -> m2b_image_sim.json
import { launch } from "./common.mjs";
import { writeFileSync } from "fs";

const BASE = "http://localhost:3302";
const browser = await launch();
const runs = [];
for (let i = 0; i < 5; i++) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true });
  await ctx.addInitScript(() => {
    window.__lcp = [];
    new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__lcp.push([e.startTime, e.element ? e.element.tagName : e.url]); }).observe({ type: "largest-contentful-paint", buffered: true });
  });
  const page = await ctx.newPage();
  const bytes = [];
  page.on("requestfinished", async (r) => { if (r.url().includes("/cities/")) bytes.push((await r.sizes()).responseBodySize); });
  const cdp = await ctx.newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: (1638.4 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 });
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
  await page.goto(BASE + "/", { waitUntil: "load", timeout: 120000 });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(1500);
  const lcp = await page.evaluate(() => window.__lcp.at(-1));
  runs.push({ lcp: Math.round(lcp[0]), el: lcp[1], image_bytes: bytes });
  console.log(runs.at(-1));
  await ctx.close();
}
await browser.close();
const s = runs.map((r) => r.lcp).sort((a, b) => a - b);
writeFileSync("m2b_image_sim.json", JSON.stringify({ note: "img_proxy.mjs (:3302) answers /cities/*.jpg with 720px WebP q72 over the gzip stand-in; same throttling as m2", median_lcp: s[2], runs }, null, 1));
console.log("median", s[2]);
