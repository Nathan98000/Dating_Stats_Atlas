// m6: reflow and motion.
//  - 200% zoom at 1440 (a 720x450 CSS viewport at device scale 2) and 320 wide: sideways
//    scroll on every page, and screenshots of the home page and sheet;
//  - prefers-reduced-motion: reduce — animations and transitions running during a
//    weight change, the sheet opening, a row opening and the progress line.
//   node m6_reflow_motion.mjs -> m6_reflow_motion.json
import { launch, BASE, PAGES, settle } from "./common.mjs";
import { writeFileSync } from "fs";

const browser = await launch();
const out = { zoom200: {}, w320: {}, motion: {} };
const Z = { viewport: { width: 720, height: 450 }, deviceScaleFactor: 2 };
const W320 = { viewport: { width: 320, height: 640 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true };
for (const [label, opts] of [["zoom200", Z], ["w320", W320]]) {
  for (const [name, url] of Object.entries(PAGES)) {
    const ctx = await browser.newContext(opts);
    const page = await ctx.newPage();
    await page.goto(BASE + url); await settle(page, 300);
    out[label][name] = await page.evaluate(() => ({ scroll_width: document.documentElement.scrollWidth, client_width: document.documentElement.clientWidth }));
    if (["home", "city-sf", "compare-pair"].includes(name)) {
      await page.screenshot({ path: `shots/${name}-${label === "zoom200" ? "1440z200" : "320"}-top.png` });
      await page.screenshot({ path: `shots/${name}-${label === "zoom200" ? "1440z200" : "320"}-full.png`, fullPage: true });
    }
    if (name === "home") {
      // the sheet or drawer at this size
      await page.evaluate(() => window.scrollTo(0, 1600)); await page.waitForTimeout(400);
      const b = page.getByRole("button", { name: "Adjust your search" });
      if (await b.isVisible()) {
        await b.click(); await page.waitForTimeout(500);
        out[label].sheet = await page.evaluate(() => { const d = document.querySelector("dialog[open] .sheet-panel"); const r = d.getBoundingClientRect(); return { w: Math.round(r.width), h: Math.round(r.height), body_scroll: document.querySelector("dialog[open] .sheet-body").scrollHeight }; });
        await page.screenshot({ path: `shots/home-${label === "zoom200" ? "1440z200" : "320"}-sheet.png` });
      }
    }
    await ctx.close();
  }
}

// motion
for (const rm of ["reduce", "no-preference"]) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: rm });
  const page = await ctx.newPage();
  await page.goto(BASE + "/"); await settle(page, 300);
  await page.evaluate(() => {
    window.__anim = new Set(); window.__trans = [];
    document.addEventListener("transitionrun", (e) => window.__trans.push(`${e.target.tagName}.${String(e.target.className).slice(0, 30)} ${e.propertyName} ${e.elapsedTime}`), true);
    document.addEventListener("animationstart", (e) => window.__anim.add(`${e.target.tagName}.${String(e.target.className).slice(0, 30)} ${e.animationName}`), true);
    window.__poll = setInterval(() => { for (const a of document.getAnimations()) window.__anim.add(`${a.constructor.name} ${a.animationName || a.transitionProperty || ""} on ${a.effect?.target?.tagName}.${String(a.effect?.target?.className || "").slice(0, 30)} dur=${a.effect?.getTiming().duration}`); }, 16);
  });
  await page.locator('[data-testid=search-panel] [aria-label="Cost of living importance"]').getByText("A lot").first().click();
  await page.waitForTimeout(1500);
  await page.locator('li[data-rank="4"] [data-testid=row-toggle]').locator("visible=true").first().click();
  await page.waitForTimeout(600);
  await page.locator('[data-testid=card-photo-link]').first().hover();
  await page.waitForTimeout(500);
  const r = await page.evaluate(() => ({ animations: [...window.__anim], transitions: window.__trans.slice(0, 30), transition_count: window.__trans.length }));
  out.motion[rm] = r;
  await ctx.close();
}
// sheet motion at 390
for (const rm of ["reduce", "no-preference"]) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: rm });
  const page = await ctx.newPage();
  await page.goto(BASE + "/"); await settle(page, 300);
  await page.evaluate(() => window.scrollTo(0, 1500)); await page.waitForTimeout(400);
  await page.evaluate(() => { window.__a = []; window.__poll = setInterval(() => { for (const a of document.getAnimations()) window.__a.push(`${a.animationName || a.transitionProperty} on ${a.effect?.target?.className?.toString().slice(0, 30)}`); }, 10); });
  await page.getByRole("button", { name: "Adjust your search" }).tap();
  await page.waitForTimeout(800);
  out.motion[`sheet-${rm}`] = await page.evaluate(() => [...new Set(window.__a)]);
  await ctx.close();
}
await browser.close();
writeFileSync("m6_reflow_motion.json", JSON.stringify(out, null, 1));
const bad = (o) => Object.entries(o).filter(([k, v]) => v.scroll_width > v.client_width).map(([k, v]) => `${k} ${v.scroll_width}/${v.client_width}`);
console.log("zoom200 sideways:", bad(out.zoom200), "\n320 sideways:", bad(out.w320), "\nsheet:", out.zoom200.sheet, out.w320.sheet);
console.log(JSON.stringify(out.motion, null, 1));
