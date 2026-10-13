// m10: where the #1 result sits, and row heights, at every width (home, default search).
import { launch, BASE, VIEWPORTS, settle } from "./common.mjs";
import { writeFileSync } from "fs";
const browser = await launch(); const out = {};
for (const [w, o] of Object.entries(VIEWPORTS)) {
  const ctx = await browser.newContext(o); const page = await ctx.newPage();
  await page.goto(BASE + "/"); await settle(page, 300);
  out[w] = await page.evaluate(() => {
    const c = document.querySelector('[data-rank="1"]'); const r = c.getBoundingClientRect();
    const score = c.querySelector("[data-testid=score]").getBoundingClientRect();
    const rows = [...document.querySelectorAll("li[data-rank]")].filter((li) => +li.dataset.rank >= 4 && +li.dataset.rank <= 10).map((li) => Math.round(li.getBoundingClientRect().height));
    const r4 = document.querySelector('li[data-rank="4"]').getBoundingClientRect();
    return { first_top: Math.round(r.top + scrollY), first_score_bottom: Math.round(score.bottom + scrollY), first_bottom: Math.round(r.bottom + scrollY), row4_top: Math.round(r4.top + scrollY), rows_4_10: rows, viewport_h: innerHeight };
  });
  await ctx.close();
}
await browser.close();
writeFileSync("m10_geometry.json", JSON.stringify(out, null, 1));
console.log(out);
