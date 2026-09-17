import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/** WCAG 2.1 AA on the new palette (Phase 2d gate 2): axe across home,
 * results, city, compare, a stat page and How it works — serious and
 * critical violations fail. Plus the two-handle control's separate
 * labels. */

const PAGES = [
  { name: "home", url: "/" },
  {
    name: "results narrowed",
    url: "/?self_sex=female&self_age=32&age=30-40&marital=never&edu=graduate&inc=100000",
  },
  {
    name: "city page",
    url: "/city/provo-utah?self_sex=female&self_age=30&age=28-40&marital=never,previously",
  },
  {
    name: "narrow search",
    url: "/?self_sex=female&self_age=30&age=25-35&marital=never&edu=graduate&inc=250000&race=nhpi_nh",
  },
  {
    name: "compare",
    url: "/compare/provo-utah/austin-texas?self_sex=female&self_age=30&age=28-40&marital=never,previously",
  },
  { name: "compare landing", url: "/compare" },
  { name: "stat page", url: "/stats/median_gross_rent" },
  { name: "what we measure", url: "/what-we-measure" },
  { name: "how it works", url: "/how-it-works" },
];

for (const p of PAGES) {
  test(`axe: ${p.name}`, async ({ page }) => {
    await page.goto(p.url);
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const serious = results.violations.filter((v) =>
      ["serious", "critical"].includes(v.impact ?? ""),
    );
    expect(
      serious.map((v) => `${v.id}: ${v.nodes.length} nodes — ${v.help}`),
    ).toEqual([]);
  });
}

test("each age handle is separately labelled and tab-reachable", async ({ page }) => {
  await page.goto("/");
  const younger = page.getByLabel("Youngest age");
  const older = page.getByLabel("Oldest age");
  await expect(younger).toHaveCount(1);
  await expect(older).toHaveCount(1);
  // both reachable by Tab alone, in order
  let sawYounger = false;
  let sawOlder = false;
  for (let i = 0; i < 30 && !(sawYounger && sawOlder); i++) {
    await page.keyboard.press("Tab");
    const label = await page.evaluate(
      () => document.activeElement?.getAttribute("aria-label") ?? "",
    );
    if (label === "Youngest age") sawYounger = true;
    if (label === "Oldest age") {
      expect(sawYounger, "younger handle comes first in tab order").toBe(true);
      sawOlder = true;
    }
  }
  expect(sawYounger && sawOlder).toBe(true);
  // visible focus on the handle input
  const outline = await page.evaluate(() => {
    const el = document.activeElement as HTMLElement;
    return getComputedStyle(el).outlineStyle;
  });
  expect(outline === "none").toBe(false);
});
