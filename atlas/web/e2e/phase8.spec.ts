import { expect, test, type Page } from "@playwright/test";
import { expandRow, fetchMeta, photoOnDisk } from "./helpers";

/** Phase 8 (the round-4 review's remaining findings, Nathan's go of 15
 * October 2026). Each test sets its own window. */

async function home(page: Page, qs = "") {
  await page.goto(`/${qs}`);
  await expect(page.locator('li[data-rank="1"]')).toBeVisible();
}

const fill = (t: string, slots: Record<string, string | number>) =>
  t.replace(/\{(\w+)\}/g, (m, k: string) => (k in slots ? String(slots[k]) : m));

// ---------------------------------------------------------------- A (R15)

test.describe("the pages' words are the registry's (R15)", () => {
  test("the city page: its card's heading, its rank line, its buttons and headings", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/city/austin-texas?ic=a");
    const card = page.getByTestId("ranked-card");
    await expect(card.getByRole("heading", { level: 2 })).toHaveText(fill(ps.city_card_heading, { city: "Austin" }));
    // the rank line says metro areas, as the home page's count does
    await expect(card.getByTestId("city-spot").locator("p").first())
      .toHaveText(new RegExp(`^${ps.city_rank_sr} \\d+${fill(ps.city_rank_of, { n: "\\d+" })}$`));
    await expect(page.getByRole("link", { name: ps.change_search })).toBeVisible();
    await expect(page.getByRole("button", { name: ps.compare_with_another, exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: ps.compare_cities, exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: fill(ps.city_like_heading, { city: "Austin" }) })).toBeVisible();
    await expect(page.getByText(fill(ps.city_compare_prompt, { city: "Austin" }))).toBeVisible();
  });

  test("Compare: the heading, the search line, the spot row and the crime heading", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await page.goto("/compare/austin-texas/san-jose-california");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(`Austin ${ps.compare_and} San Jose`);
    await expect(page.getByRole("rowheader", { name: ps.compare_spot })).toBeVisible();
    await expect(page.getByRole("heading", { name: ps.crime_heading })).toBeVisible();
    await page.goto("/compare");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(ps.compare_heading);
    await expect(page.getByRole("button", { name: ps.compare_go })).toBeVisible();
    await expect(page.getByRole("combobox", { name: ps.compare_first_city })).toHaveAttribute("placeholder", ps.city_input_placeholder);
  });

  test("the home page: the quick search's choices, the sort control, the skip link and the header's search", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await page.setViewportSize({ width: 1440, height: 900 });
    await home(page);
    await expect(page.getByTestId("self-sex").locator("option")).toHaveText([ps.sex_woman, ps.sex_man]);
    await expect(page.getByTestId("seek-sex").locator("option")).toHaveText([ps.sex_men, ps.sex_women]);
    const sort = page.getByRole("radiogroup", { name: ps.sort_label }).first();
    await expect(sort.getByRole("radio")).toHaveText([ps.sort_best, ps.sort_worst]);
    await expect(page.getByRole("link", { name: ps.skip_to_results })).toHaveCount(1);
    await expect(page.getByRole("combobox", { name: ps.find_city, exact: true })).toHaveAttribute("placeholder", ps.find_city);
    await expect(page.getByRole("radiogroup", { name: fill(ps.importance_group, { pillar: "Weather" }) })).toBeVisible();
  });

  test("a stat page's heading is the registry's template", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await page.goto("/stats/rent_1br");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(new RegExp(`^${fill(ps.stat_cities_by, { stat: ".+" })}$`));
  });
});

// ---------------------------------------------------------------- A (R16)

test.describe("a heading reads its own name; its ⓘ sits beside it (R16)", () => {
  test("a row's detail: the heading is 'Balance', the button 'About balance', outside it", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await page.setViewportSize({ width: 1440, height: 900 });
    await home(page);
    const row = await expandRow(page, 4);
    const detail = row.getByTestId("row-detail");
    await expect(detail.getByRole("heading", { name: ps.balance_label, exact: true })).toHaveCount(1);
    const btn = detail.getByRole("button", { name: ps.balance_info_label });
    await expect(btn).toHaveCount(1);
    expect(await btn.evaluate((el) => el.closest("h1,h2,h3,h4,h5,h6") === null)).toBe(true);
  });

  test("the city card: the same", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await page.goto("/city/austin-texas?ic=a");
    const card = page.getByTestId("ranked-card");
    await expect(card.getByRole("heading", { name: ps.balance_label, exact: true })).toHaveCount(1);
    const btn = card.getByRole("button", { name: ps.balance_info_label });
    expect(await btn.evaluate((el) => el.closest("h1,h2,h3,h4,h5,h6") === null)).toBe(true);
  });
});

// ---------------------------------------------------------------- B (R18)

test.describe("lighter pages: the phone's photographs and the site's font (R18)", () => {
  for (const [w, h, scale, copy] of [[390, 844, 3, 720], [390, 844, 2, 720], [1440, 900, 1, 480]] as const) {
    test(`${w} at ${scale}x: card #1 shows the ${copy}px copy`, async ({ browser }) => {
      test.skip(!photoOnDisk("cities/new-york-new-york.jpg") && !photoOnDisk("cities/new-york-new-york.png"),
        "no photographs on this checkout");
      const phone = w < 768;
      const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: scale,
        isMobile: phone, hasTouch: phone });
      const page = await ctx.newPage();
      await home(page);
      const img = page.locator('li[data-rank="1"]').getByTestId("card-photo");
      await expect.poll(() => img.evaluate((e) => (e as HTMLImageElement).currentSrc))
        .toMatch(new RegExp(`-${copy}\\.webp$`));
      await ctx.close();
    });
  }

  test("Fraunces: one file, this site's own, under 64 KB; until it arrives, the stand-in Google's carried", async ({ page }) => {
    const fonts: { url: string; bytes: number }[] = [];
    page.on("response", async (r) => {
      if (/\.woff2$/.test(new URL(r.url()).pathname)) fonts.push({ url: r.url(), bytes: (await r.body()).length });
    });
    await page.setViewportSize({ width: 1440, height: 900 });
    await home(page);
    await page.evaluate(() => document.fonts.ready);
    await expect.poll(() => fonts.filter((f) => /fraunces/i.test(f.url)).length).toBe(1);
    const f = fonts.find((x) => /fraunces/i.test(x.url))!;
    expect(new URL(f.url).origin).toBe(new URL(page.url()).origin);
    expect(f.bytes).toBeLessThan(64 * 1024);
    expect(await page.getByRole("heading", { level: 1 }).evaluate((e) => getComputedStyle(e).fontFamily))
      .toMatch(/^"?fraunces"?, "Fraunces Fallback", Georgia, serif$/);
    const standIn = await page.evaluate(() => {
      for (const sheet of document.styleSheets) {
        for (const rule of sheet.cssRules) {
          if (rule instanceof CSSFontFaceRule && rule.style.getPropertyValue("font-family").includes("Fraunces Fallback"))
            return rule.style.getPropertyValue("size-adjust");
        }
      }
      return null;
    });
    expect(standIn).toBe("115.45%");
  });
});
