// m8: full-page screenshots of every page at 1440 and 390 (cold), for the visual pass.
import { launch, BASE, PAGES, VIEWPORTS, settle } from "./common.mjs";
import { mkdirSync } from "fs";
mkdirSync("shots/full", { recursive: true });
const browser = await launch();
for (const w of ["1440", "390"]) for (const [name, url] of Object.entries(PAGES)) {
  const o = { ...VIEWPORTS[w] }; if (w === "390") o.deviceScaleFactor = 2;
  const ctx = await browser.newContext(o); const page = await ctx.newPage();
  await page.goto(BASE + url); await settle(page, 400);
  await page.screenshot({ path: `shots/full/${name}-${w}-full.png`, fullPage: true });
  await ctx.close();
}
await browser.close();
