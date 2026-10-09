// m5: keyboard only. Tab order and visible focus through the home page at 1440 and 390;
// whether a focused element is hidden behind a sticky/fixed layer; then the sheet, the
// info boxes, the age popover, the menu and the header search: what Tab, Escape and an
// outside click do, and where focus lands.   node m5_keyboard.mjs -> m5_keyboard.json
import { launch, BASE, VIEWPORTS, settle } from "./common.mjs";
import { writeFileSync, mkdirSync } from "fs";
mkdirSync("shots", { recursive: true });

const browser = await launch();
const out = {};
const FOCUS = () => {
  const e = document.activeElement;
  if (!e || e === document.body) return { tag: "BODY" };
  const r = e.getBoundingClientRect();
  const cs = getComputedStyle(e);
  const ring = (cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0) || (cs.boxShadow && cs.boxShadow !== "none");
  const cx = Math.min(Math.max(r.left + r.width / 2, 0), innerWidth - 1), cy = Math.min(Math.max(r.top + r.height / 2, 0), innerHeight - 1);
  const top = document.elementFromPoint(cx, cy);
  const obscured = !!top && !(e === top || e.contains(top) || top.contains(e) || (e.labels && [...e.labels].some((l) => l.contains(top))));
  const name = (e.getAttribute("aria-label") || e.innerText || e.value || e.placeholder || "").trim().replace(/\s+/g, " ").slice(0, 50);
  return {
    tag: e.tagName, role: e.getAttribute("role"), name, testid: e.dataset?.testid || e.closest("[data-testid]")?.dataset.testid || null,
    in_view: r.bottom > 0 && r.top < innerHeight, ring, obscured, by: obscured && top ? (top.closest("[data-testid]")?.dataset.testid || top.tagName) : null,
    y: Math.round(r.top), h: Math.round(r.height),
  };
};

async function tabWalk(w, max) {
  const ctx = await browser.newContext(VIEWPORTS[w]);
  const page = await ctx.newPage();
  await page.goto(BASE + "/"); await settle(page, 400);
  const seq = [];
  for (let i = 0; i < max; i++) {
    await page.keyboard.press("Tab");
    await page.waitForTimeout(60);
    const f = await page.evaluate(FOCUS);
    seq.push(f);
    if (i === 0 || f.obscured || !f.ring) await page.screenshot({ path: `shots/kbd-${w}-${String(i).padStart(2, "0")}.png` }).catch(() => {});
  }
  await ctx.close();
  return seq;
}

out.tab_1440 = await tabWalk("1440", 90);
out.tab_390 = await tabWalk("390", 60);

// the sheet at 390, keyboard only
{
  const ctx = await browser.newContext(VIEWPORTS["390"]);
  const page = await ctx.newPage();
  await page.goto(BASE + "/"); await settle(page, 400);
  await page.evaluate(() => window.scrollTo(0, 1500)); await page.waitForTimeout(400);
  const btn = page.getByRole("button", { name: "Adjust your search" });
  await btn.focus();
  await page.keyboard.press("Enter"); await page.waitForTimeout(500);
  const r = { opened: await page.evaluate(() => !!document.querySelector("dialog[open]")), first_focus: await page.evaluate(FOCUS) };
  const cycle = [];
  for (let i = 0; i < 45; i++) { await page.keyboard.press("Tab"); await page.waitForTimeout(40); cycle.push(await page.evaluate(FOCUS)); }
  r.cycle = cycle;
  r.focus_left_dialog = await page.evaluate(() => !document.querySelector("dialog[open]")?.contains(document.activeElement));
  await page.keyboard.press("Escape"); await page.waitForTimeout(400);
  r.after_escape = { open: await page.evaluate(() => !!document.querySelector("dialog[open]")), focus: await page.evaluate(FOCUS), scrollY: await page.evaluate(() => scrollY) };
  out.sheet_390 = r;
  await ctx.close();
}

// info boxes (row detail) at 1440 and 390: keyboard open, Escape, outside click
for (const w of ["1440", "390"]) {
  const ctx = await browser.newContext(VIEWPORTS[w]);
  const page = await ctx.newPage();
  await page.goto(BASE + "/"); await settle(page, 400);
  const toggle = page.locator('li[data-rank="4"] [data-testid=row-toggle]').locator("visible=true").first();
  await toggle.focus(); await page.keyboard.press("Enter"); await page.waitForTimeout(300);
  const r = { row_expanded: await toggle.getAttribute("aria-expanded"), focus_after_expand: await page.evaluate(FOCUS) };
  // tab to the first info button inside the detail
  const steps = [];
  for (let i = 0; i < 6; i++) { await page.keyboard.press("Tab"); await page.waitForTimeout(40); const f = await page.evaluate(FOCUS); steps.push(f); if (f.name === "Balance") break; }
  r.steps_to_info = steps;
  await page.keyboard.press("Enter"); await page.waitForTimeout(300);
  const box = () => page.evaluate(() => {
    const b = [...document.querySelectorAll("[role=tooltip], [role=dialog], [data-info-box], .info-pop")].find((x) => x.getBoundingClientRect().height > 0 && getComputedStyle(x).visibility !== "hidden");
    return b ? { role: b.getAttribute("role"), text: b.innerText.slice(0, 80), top: Math.round(b.getBoundingClientRect().top) } : null;
  });
  r.open = await box();
  r.focus_while_open = await page.evaluate(FOCUS);
  await page.screenshot({ path: `shots/kbd-${w}-info-open.png` });
  await page.keyboard.press("Escape"); await page.waitForTimeout(300);
  r.after_escape = { box: await box(), focus: await page.evaluate(FOCUS) };
  await page.keyboard.press("Enter"); await page.waitForTimeout(300);
  r.reopened = !!(await box());
  await page.mouse.click(5, 300); await page.waitForTimeout(300);
  r.after_outside_click = { box: await box(), focus: await page.evaluate(FOCUS) };
  await page.keyboard.press("Enter"); await page.waitForTimeout(200);
  await page.keyboard.press("Tab"); await page.waitForTimeout(200);
  r.after_tab_away = { box: await box(), focus: await page.evaluate(FOCUS) };
  out[`info_${w}`] = r;
  await ctx.close();
}

// the age popover and the slider's info box
for (const w of ["1440", "390"]) {
  const ctx = await browser.newContext(VIEWPORTS[w]);
  const page = await ctx.newPage();
  await page.goto(BASE + "/"); await settle(page, 400);
  await page.locator("[data-testid=age-token]").focus();
  await page.keyboard.press("Enter"); await page.waitForTimeout(300);
  const r = { focus_after_open: await page.evaluate(FOCUS) };
  await page.keyboard.press("ArrowRight"); await page.waitForTimeout(150);
  r.value_after_arrow = await page.locator("[data-testid=age-token]").innerText();
  await page.keyboard.press("Escape"); await page.waitForTimeout(300);
  r.after_escape = { popover_visible: await page.locator("[data-testid=age-popover]").isVisible(), focus: await page.evaluate(FOCUS) };
  await page.locator("[data-testid=age-token]").click(); await page.waitForTimeout(300);
  await page.mouse.click(5, 5); await page.waitForTimeout(300);
  r.after_outside_click = await page.locator("[data-testid=age-popover]").isVisible();
  out[`age_${w}`] = r;
  await ctx.close();
}

// the phone menu and header search
{
  const ctx = await browser.newContext(VIEWPORTS["390"]);
  const page = await ctx.newPage();
  await page.goto(BASE + "/"); await settle(page, 400);
  await page.locator("[data-testid=menu-button]").focus(); await page.keyboard.press("Enter"); await page.waitForTimeout(300);
  const r = { menu_focus_after_open: await page.evaluate(FOCUS) };
  await page.screenshot({ path: "shots/kbd-390-menu.png" });
  await page.keyboard.press("Escape"); await page.waitForTimeout(300);
  r.menu_after_escape = { expanded: await page.locator("[data-testid=menu-button]").getAttribute("aria-expanded"), focus: await page.evaluate(FOCUS) };
  await page.locator("[data-testid=header-search-button]").focus(); await page.keyboard.press("Enter"); await page.waitForTimeout(300);
  r.search_focus_after_open = await page.evaluate(FOCUS);
  await page.keyboard.type("Abil"); await page.waitForTimeout(400);
  await page.keyboard.press("ArrowDown"); await page.waitForTimeout(100);
  r.search_option = await page.evaluate(() => document.activeElement.getAttribute("aria-activedescendant"));
  await page.keyboard.press("Escape"); await page.waitForTimeout(200);
  await page.keyboard.press("Escape"); await page.waitForTimeout(300);
  r.search_after_escape = await page.evaluate(FOCUS);
  out.header_390 = r;
  await ctx.close();
}
await browser.close();
writeFileSync("m5_keyboard.json", JSON.stringify(out, null, 1));
const brief = (s) => s.map((f, i) => `${i + 1}. ${f.tag}${f.role ? "/" + f.role : ""} "${f.name}" ${f.ring ? "" : "NO-RING "}${f.obscured ? "OBSCURED by " + f.by : ""}`).join("\n");
console.log("== 1440\n" + brief(out.tab_1440));
console.log("== 390\n" + brief(out.tab_390));
console.log(JSON.stringify({ sheet: { ...out.sheet_390, cycle: brief(out.sheet_390.cycle) }, info_1440: out.info_1440, info_390: out.info_390, age_1440: out.age_1440, age_390: out.age_390, header: out.header_390 }, null, 1));
