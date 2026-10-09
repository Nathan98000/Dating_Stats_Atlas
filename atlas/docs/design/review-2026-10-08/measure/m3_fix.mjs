// re-run of the three home states whose selectors needed fixing in m3_axe.mjs
import AxeBuilder from "/home/claude/rv/repo/atlas/web/node_modules/@axe-core/playwright/dist/index.mjs";
import { launch, BASE, VIEWPORTS, settle } from "./common.mjs";
import { HOME_STATES } from "./states.mjs";
import { readFileSync, writeFileSync } from "fs";
const out = JSON.parse(readFileSync("m3_axe.json", "utf8"));
const browser = await launch();
for (const w of ["1440", "390"]) for (const state of ["slider-info", "find-typed", "header-search"]) {
  const ctx = await browser.newContext(VIEWPORTS[w]); const page = await ctx.newPage();
  await page.goto(BASE + "/"); await settle(page, 400);
  await HOME_STATES[state](page);
  const r = await new AxeBuilder({ page }).analyze();
  out[`home:${state}@${w}`] = { violations: r.violations.map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length, targets: v.nodes.slice(0, 4).map((n) => n.target.join(" ")) })), incomplete: r.incomplete.map((v) => `${v.id} (${v.nodes.length})`) };
  console.log(`home:${state}@${w}`, r.violations.map((v) => v.id).join(",") || "clean");
  await page.screenshot({ path: `shots/home-${w}-${state}.png` });
  await ctx.close();
}
await browser.close();
writeFileSync("m3_axe.json", JSON.stringify(out, null, 1));
