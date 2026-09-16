import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/** WCAG 2.1 AA (gate 4), checked by axe-core on the three page shapes plus
 * the identity-filtered ranking. Serious and critical violations fail. */

const PAGES = [
  { name: "ranking", url: "/" },
  {
    name: "ranking with race filter",
    url: "/?self_sex=female&self_age=29&age=28-38&marital=never,previously&race=black_nh",
  },
  {
    name: "metro page",
    url: "/metro/35620?self_sex=female&self_age=30&age=28-40&marital=never,previously",
  },
  { name: "methodology", url: "/methodology" },
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

test("the margin has a screen-reader rendering that cannot read as precise", async ({ page }) => {
  await page.goto("/");
  const first = page.getByTestId("ranked-list").locator("li").first();
  await expect(first).toBeVisible();
  const sr = await first.locator("[data-figure='pool'] .sr-only").first().textContent();
  expect(sr).toContain("at least plus or minus");
  expect(sr).toContain("not a precise figure");
});
