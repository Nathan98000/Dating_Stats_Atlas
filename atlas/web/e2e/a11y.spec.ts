import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/** WCAG 2.1 AA on the new palette (Phase 2d gate 2): serious and critical
 * violations fail. Every page at its default search is scanned at the desk
 * and the phone by phase5.spec.ts ("axe: <path>", with best-practice too);
 * these are the two searches it doesn't load. Plus the two-handle
 * control's separate labels. */

const PAGES = [
  {
    name: "results narrowed",
    url: "/?sex=male&self_age=32&age=30-40&marital=never&edu=graduate&inc=100000",
  },
  {
    name: "narrow search",
    url: "/?sex=male&self_age=30&age=25-35&marital=never&edu=graduate&inc=250000&race=nhpi_nh",
  },
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
  // Phase 6 (F02): the popover's exact-age fields share their thumbs'
  // names, so the handles are counted by role
  const younger = page.getByRole("slider", { name: "Youngest age", includeHidden: true });
  const older = page.getByRole("slider", { name: "Oldest age", includeHidden: true });
  await expect(younger).toHaveCount(1);
  await expect(older).toHaveCount(1);
  // both reachable by the keyboard alone, in order (Phase 5: Tab to the
  // age range's button, Enter opens its popover on the first handle)
  let sawYounger = false;
  let sawOlder = false;
  for (let i = 0; i < 30 && !(sawYounger && sawOlder); i++) {
    const current = await page.evaluate(
      () => document.activeElement?.getAttribute("aria-label") ?? "",
    );
    await page.keyboard.press(current.startsWith("Their age") ? "Enter" : "Tab");
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
