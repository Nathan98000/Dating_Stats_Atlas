// m4: sizes and contrast where they are used. On every page, and on the home page's
// interactive states, at 390, 768, 1024 and 1119 (below the desk, where every target must
// be 44x44) and at 1440 (text size and contrast only): targets under 44x44, text under
// 12px, text below its AA contrast against the opaque background actually behind it,
// and control boundaries under 3:1.   node m4_sizes.mjs -> m4_sizes.json
import { launch, BASE, PAGES, VIEWPORTS, settle } from "./common.mjs";
import { HOME_STATES } from "./states.mjs";
import { readFileSync, writeFileSync } from "fs";

const AUDIT = readFileSync(new URL("./audit_in_page.js", import.meta.url), "utf8");
const browser = await launch();
const out = {};
for (const w of ["390", "768", "1024", "1119", "1440"]) {
  const jobs = [
    ...Object.entries(PAGES).map(([name, url]) => [name, async (page) => { await page.goto(BASE + url); await settle(page, 400); }]),
    ...Object.entries(HOME_STATES).filter(([s]) => s !== "default").map(([s, go]) => [`home:${s}`, async (page) => { await page.goto(BASE + "/"); await settle(page, 400); await go(page); }]),
  ];
  for (const [name, go] of jobs) {
    const ctx = await browser.newContext(VIEWPORTS[w]);
    const page = await ctx.newPage();
    try { await go(page); } catch (e) { out[`${name}@${w}`] = { error: String(e).slice(0, 200) }; await ctx.close(); continue; }
    // whole page: scroll through so sticky/fixed items are judged where they sit
    const res = await page.evaluate(AUDIT);
    if (w === "1440") delete res.small_targets;
    out[`${name}@${w}`] = res;
    process.stdout.write(`${name}@${w}: small ${res.small_targets ? res.small_targets.length : "-"} tiny ${res.tiny_text.length} low ${res.low_contrast.length} bounds ${res.weak_boundaries.length}\n`);
    await ctx.close();
  }
}
await browser.close();
writeFileSync("m4_sizes.json", JSON.stringify(out, null, 1));
