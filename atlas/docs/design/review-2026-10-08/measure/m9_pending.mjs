// m9: what a phone shows while a weight change is in flight (390, Lighthouse mobile
// throttling, raw /api/rank as `next start` serves it): the sheet after the tap, then the
// page right after "Show results", then when the list lands.
import { launch, BASE } from "./common.mjs";
const browser = await launch();
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
const page = await ctx.newPage();
await page.goto(BASE + "/"); await page.waitForLoadState("networkidle");
const cdp = await ctx.newCDPSession(page);
await cdp.send("Network.enable");
await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: (1638.4 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 });
await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
await page.evaluate(() => window.scrollTo(0, 2300)); await page.waitForTimeout(500);
await page.getByRole("button", { name: "Adjust your search" }).tap(); await page.waitForTimeout(800);
await page.locator('dialog[open] [aria-label="Cost of living importance"]').getByText("A lot").tap();
await page.waitForTimeout(600);
await page.screenshot({ path: "shots/home-390-pending-sheet.png" });
await page.getByRole("button", { name: "Show results" }).tap(); await page.waitForTimeout(500);
const t = Date.now();
await page.screenshot({ path: "shots/home-390-pending-after-show.png" });
const busy = await page.evaluate(() => document.querySelector("section[aria-labelledby=results-heading]").getAttribute("aria-busy"));
await page.waitForFunction(() => document.querySelector("section[aria-labelledby=results-heading]").getAttribute("aria-busy") === "false", null, { timeout: 60000 });
const res = { busy_after_show: busy, landed_ms_after_show: Date.now() - t, scrollY: await page.evaluate(() => scrollY) };
console.log(res);
(await import("fs")).writeFileSync("m9_pending.json", JSON.stringify(res, null, 1));
await page.waitForTimeout(300);
await page.screenshot({ path: "shots/home-390-pending-landed.png" });
await browser.close();
