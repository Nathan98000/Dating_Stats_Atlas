// m3: axe-core 4.13 on every page at 1440 and 390, with every rule axe runs by default
// (WCAG 2.0/2.1/2.2 A and AA plus best practice; experimental rules too, reported apart),
// and on the home page's interactive states.   node m3_axe.mjs -> m3_axe.json
import AxeBuilder from "@axe-core/playwright";
import { launch, BASE, PAGES, VIEWPORTS, settle } from "./common.mjs";
import { HOME_STATES } from "./states.mjs";
import { writeFileSync } from "fs";

const browser = await launch();
const out = {};
const summarise = (res) => ({
  violations: res.violations.map((v) => ({ id: v.id, impact: v.impact, tags: v.tags.filter((t) => /wcag|best|experimental/.test(t)), nodes: v.nodes.length,
    targets: v.nodes.slice(0, 4).map((n) => n.target.join(" ")), summary: v.nodes[0]?.failureSummary?.slice(0, 300) })),
  incomplete: res.incomplete.map((v) => `${v.id} (${v.nodes.length})`),
});
for (const w of ["1440", "390"]) {
  for (const [name, url] of Object.entries(PAGES)) {
    const ctx = await browser.newContext(VIEWPORTS[w]);
    const page = await ctx.newPage();
    await page.goto(BASE + url); await settle(page, 400);
    const std = await new AxeBuilder({ page }).analyze();
    const exp = await new AxeBuilder({ page }).withTags(["experimental"]).analyze();
    out[`${name}@${w}`] = { ...summarise(std), experimental: summarise(exp).violations };
    process.stdout.write(`${name}@${w}: ${std.violations.map((v) => v.id + "(" + v.nodes.length + ")").join(", ") || "clean"} | exp: ${exp.violations.map((v) => v.id).join(",") || "-"}\n`);
    await ctx.close();
  }
  for (const [state, go] of Object.entries(HOME_STATES)) {
    if (state === "default") continue;
    const ctx = await browser.newContext(VIEWPORTS[w]);
    const page = await ctx.newPage();
    await page.goto(BASE + "/"); await settle(page, 400);
    try { await go(page); } catch (e) { out[`home:${state}@${w}`] = { error: String(e).slice(0, 200) }; await ctx.close(); continue; }
    const std = await new AxeBuilder({ page }).analyze();
    out[`home:${state}@${w}`] = summarise(std);
    process.stdout.write(`home:${state}@${w}: ${std.violations.map((v) => v.id + "(" + v.nodes.length + ")").join(", ") || "clean"}\n`);
    await page.screenshot({ path: `shots/home-${w}-${state}.png` });
    await ctx.close();
  }
}
await browser.close();
writeFileSync("m3_axe.json", JSON.stringify(out, null, 1));
