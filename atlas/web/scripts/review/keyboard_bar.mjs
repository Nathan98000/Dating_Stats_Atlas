// Phase 7 (R01): the hand-run Tab sequence behind the round-4 review's
// measure/keyboard_bar.txt, as a script, so the baseline, commit A's test and
// the after-run use the same steps. Is "Refine your search" ever focused by Tab?
//
//   1. Tab, 390x844, 80 presses (two full loops)
//   2. Tab, 1024x768, 50 presses
//   3. 390x844: 22 Tabs into the list, then 16 Shift+Tabs
//
// Each line: the focused element | the page's scroll position | whether the
// bar is shown (rendered and its top inside the window). Writes
// keyboard_bar.txt and keyboard_bar.json to the current directory.
//
//   cd atlas/results/phase7/before && node ../../../web/scripts/review/keyboard_bar.mjs
import { chromium } from "@playwright/test";
import { writeFileSync } from "fs";

const BASE = process.env.BASE || "http://127.0.0.1:3400";
const BAR = "Refine your search";

const VIEW = {
  390: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true },
  1024: { viewport: { width: 1024, height: 768 } },
};

/** What has focus, and whether the bar shows: read in the page. */
const probe = (page) => page.evaluate(() => {
  const el = document.activeElement;
  let name = "";
  if (el && el !== document.body) {
    name = el.getAttribute("aria-label")
      || (el.tagName === "SELECT" ? el.selectedOptions[0]?.textContent : "")
      || (el.innerText || "").replace(/\s+/g, " ").trim()
      || el.tagName;
  }
  const bar = document.querySelector("[data-testid=bottom-bar]");
  let shown = false;
  if (bar) {
    const r = bar.getBoundingClientRect();
    shown = getComputedStyle(bar).display !== "none" && r.height > 0 && r.top < window.innerHeight - 1;
  }
  return { name, scrollY: Math.round(window.scrollY), shown };
});

async function run(browser, width, presses, { into = 0 } = {}) {
  const ctx = await browser.newContext(VIEW[width]);
  const page = await ctx.newPage();
  await page.goto(BASE + "/");
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);
  const steps = [];
  const press = async (key) => {
    await page.keyboard.press(key);
    await page.waitForTimeout(120);
    steps.push(await probe(page));
  };
  if (into) {
    for (let i = 0; i < into; i++) await page.keyboard.press("Tab");
    await page.waitForTimeout(200);
    steps.push(await probe(page));
    for (let i = 0; i < presses; i++) await press("Shift+Tab");
  } else {
    for (let i = 0; i < presses; i++) await press("Tab");
  }
  await ctx.close();
  return steps;
}

const browser = await chromium.launch();
const runs = [
  ["Tab, 390x844, 80 presses", await run(browser, 390, 80), "forward"],
  ["Tab, 1024x768, 50 presses", await run(browser, 1024, 50), "forward"],
  ["390x844: 22 Tabs into the list, then Shift+Tab", await run(browser, 390, 15, { into: 22 }), "back"],
];
await browser.close();

const hits = (steps) => steps.filter((s) => s.name === BAR).length;
const forward = runs.filter((r) => r[2] === "forward").reduce((n, r) => n + hits(r[1]), 0);
const all = runs.reduce((n, r) => n + hits(r[1]), 0);
const lines = [
  `# R01: is "${BAR}" ever focused by Tab? ${BASE}, headless Chromium, ${new Date().toISOString().slice(0, 10)}.`,
  "# Each line: the focused element | the page's scroll position | whether the bar is shown.",
  `# Lines where "${BAR}" has focus: ${all} (forward Tab: ${forward})`,
];
for (const [title, steps] of runs) {
  lines.push(`== ${title}`);
  for (const s of steps) lines.push(`${s.name} | scrollY=${s.scrollY} | bar ${s.shown ? "shown" : "hidden"}`);
}
writeFileSync("keyboard_bar.txt", lines.join("\n") + "\n");
writeFileSync("keyboard_bar.json", JSON.stringify({
  base: BASE, bar: BAR, focused_total: all, focused_forward: forward,
  runs: runs.map(([title, steps, dir]) => ({ title, dir, focused: hits(steps), steps })),
}, null, 1) + "\n");
console.log(`"${BAR}" focused: ${all} (forward ${forward})`);
