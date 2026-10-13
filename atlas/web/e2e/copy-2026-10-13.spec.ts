import { expect, test, type Locator, type Page } from "@playwright/test";
import { fetchMeta } from "./helpers";

/** Nathan's change of 13 October 2026: on the home page, the expanded
 * detail of a card or a row no longer draws the item bars Phase 7 put under
 * Cost of living and Social life (Rent, Everyday prices; Walkability,
 * Places to go out). "What moved the score" is one bar per pillar again,
 * each named as its pillar alone, and the chips stay as they are. */

const ITEMS = ["Rent", "Everyday prices", "Walkability", "Places to go out"];

async function home(page: Page) {
  await page.goto("/");
  await expect(page.locator('li[data-rank="1"]')).toBeVisible();
}

/** The open detail's bars: one list item per pillar, nothing nested, no
 * item named, no chip words beside a pillar's name. */
async function onePerPillar(detail: Locator, pillarNames: string[]) {
  const bars = detail.getByTestId("moved-bars");
  await expect(bars).toBeVisible();
  const labels = await bars.locator("[data-pillar]").allInnerTexts();
  expect(labels.length).toBeGreaterThan(0);
  expect(await bars.locator("li").count()).toBe(labels.length);
  await expect(bars.locator("ul, [data-unit]")).toHaveCount(0);
  for (const l of labels) expect(pillarNames).toContain(l.trim());
  const text = await bars.innerText();
  expect(text).not.toContain("·");
  for (const item of ITEMS) expect(text).not.toContain(item);
}

for (const size of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
  test(`${size.width}: a card's and a row's detail draw one bar per pillar, no item bars; the chips stay`, async ({ page, request }) => {
    const meta = await fetchMeta(request);
    const pillarNames = [
      meta.features.pool_size.chip_label!, meta.features.match_propensity.chip_label!,
      ...["cost", "reach", "students", "weather"].map((p) => meta.pillars[p].display_name),
    ];
    await page.setViewportSize(size);
    await home(page);

    // card #1: its detail (one panel under the cards from 768px, inside
    // the card below)
    await page.locator('li[data-rank="1"]').getByTestId("card-toggle").click();
    await onePerPillar(page.getByTestId("card-detail"), pillarNames);

    // a row from the fourth on
    const row = page.locator('li[data-rank="4"]');
    await row.getByTestId("row-toggle").locator("visible=true").click();
    await onePerPillar(row.getByTestId("row-detail"), pillarNames);

    // the chips are unchanged: still the served lifestyle movers, items
    // named (the fixture's top cities carry them)
    const chips = page.getByTestId("why-chips").locator("[data-key]");
    expect(await chips.count()).toBeGreaterThan(0);
    const words = await chips.allInnerTexts();
    expect(words.some((w) => ITEMS.includes(w.trim()))).toBe(true);
  });
}
