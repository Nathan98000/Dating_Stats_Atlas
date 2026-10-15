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
    // the rank line says cities, as the home page's count does (Nathan, 15 October 2026)
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

// ---------------------------------------------------------------- C (R17)

test.describe("link previews and tabs (R17)", () => {
  test("a page that isn't there says so in its tab, whichever address", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    const title = fill(ps.title_template, { page: ps.not_found_title });
    for (const u of ["/no-such-page", "/city/no-such-city", "/compare/austin-texas/no-such-city", "/stats/no_such_stat"]) {
      const res = await page.goto(u);
      expect(res?.status(), u).toBe(404);
      await expect(page, u).toHaveTitle(title);
    }
  });

  test("the pages without a description of their own carry the home page's subtitle", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    for (const u of ["/about", "/privacy", "/terms", "/what-we-measure", "/no-such-page"]) {
      await page.goto(u);
      await expect(page.locator('meta[name="description"]'), u).toHaveAttribute("content", ps.home_subtitle);
    }
  });

  test("a compare pair's link preview is the first city's", async ({ page }) => {
    test.skip(!photoOnDisk("cities/austin-texas.jpg"), "no photographs on this checkout");
    await page.goto("/compare/austin-texas/san-jose-california");
    await expect(page.locator('meta[property="og:image"]')).toHaveAttribute("content", /\/cities\/og\/austin-texas\.jpg$/);
    await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute("content", "summary_large_image");
  });
});

// ---------------------------------------------------------------- C (R19)

test("no page names an original photograph, only its copies (R19)", async ({ browser }) => {
  test.skip(!photoOnDisk("cities/austin-texas.jpg"), "no photographs on this checkout");
  for (const [w, scale] of [[1440, 2], [390, 3]] as const) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: scale });
    const page = await ctx.newPage();
    const asked: string[] = [];
    page.on("request", (r) => {
      const u = new URL(r.url()).pathname;
      if (/^\/(cities|stats)\/[^/]+\.(jpe?g|png|webp)$/i.test(u)) asked.push(u);
    });
    for (const u of ["/", "/city/austin-texas", "/stats/rent_1br", "/about"]) {
      await page.goto(u);
      await page.waitForLoadState("networkidle");
      const html = await page.content();
      expect(html.match(/\/(cities|stats)\/[^/"'\s?,]+\.(jpe?g|png|webp)\b/gi) ?? [], `${u} at ${w}`).toEqual([]);
    }
    expect(asked).toEqual([]);
    await ctx.close();
  }
});

// ---------------------------------------------------------------- C (R21)

test("390: a row's chips run under the score too; its chevron sits under the score, on the pool's line (R21)", async ({ browser }) => {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true });
  const page = await ctx.newPage();
  await home(page);
  const rows = page.locator('ol[aria-label] > li[data-rank]').filter({ has: page.getByTestId("row-grid") });
  const n = Math.min(await rows.count(), 12);
  expect(n).toBeGreaterThan(0);
  for (let i = 0; i < n; i++) {
    const g = await rows.nth(i).evaluate((li) => {
      const r = (e: Element | null) => e?.getBoundingClientRect() ?? null;
      const btn = [...li.querySelectorAll<HTMLElement>('[data-testid="row-toggle"]')].find((b) => b.offsetParent !== null)!;
      return { li: r(li)!, h3: r(li.querySelector("h3"))!, chips: r(li.querySelector('[data-testid="why-chips"]')),
        score: r(li.querySelector('[data-testid="row-score"]'))!, pool: r(li.querySelector("h3 + p"))!, btn: r(btn)! };
    });
    if (g.chips) {
      // the chips' line starts under the name and ends under the score
      expect(Math.round(g.chips.left)).toBe(Math.round(g.h3.left));
      expect(g.chips.right).toBeGreaterThan(g.score.left);
      expect(g.chips.top).toBeGreaterThan(g.pool.bottom - 1);
    }
    // the chevron: in the score's column, level with the pool line
    const mid = (b: DOMRect) => (b.top + b.bottom) / 2;
    expect(Math.abs(mid(g.btn) - mid(g.pool))).toBeLessThan(4);
    expect(g.btn.right).toBeGreaterThan(g.score.left);
  }
  // a click on it still opens the row
  const first = rows.first();
  await first.getByRole("button", { name: /^Details for/ }).click();
  await expect(first.getByTestId("row-detail")).toBeVisible();
  await ctx.close();
});

// ---------------------------------------------------------------- C (R22)

test.describe("the city card's What moved the score (R22)", () => {
  for (const size of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    test(`${size.width}: closed until asked; open, the same bars as the home row's detail`, async ({ page, request }) => {
      const ps = (await fetchMeta(request)).policy_strings;
      await page.setViewportSize(size);
      await home(page);
      // the home row's detail for a city in the list, its bars as text
      const row = await expandRow(page, 4);
      const slug = await row.getAttribute("data-slug");
      const homeBars = await row.getByTestId("moved-bars").locator("li").allInnerTexts();
      await page.goto(`/city/${slug}`);
      const det = page.getByTestId("city-moved");
      await expect(det).not.toHaveAttribute("open", "");
      await expect(det.getByTestId("moved-bars")).toBeHidden();
      const summary = det.locator("summary");
      await expect(summary).toHaveText(ps.moved_heading);
      await summary.click();
      await expect(det.getByTestId("moved-bars")).toBeVisible();
      await expect(det.getByTestId("moved-caption")).toHaveText(ps.moved_caption);
      const norm = (xs: string[]) => xs.map((x) => x.replace(/\s+/g, " ").trim());
      expect(norm(await det.getByTestId("moved-bars").locator("li").allInnerTexts())).toEqual(norm(homeBars));
      // the keyboard closes it again
      await summary.focus();
      await page.keyboard.press("Enter");
      await expect(det.getByTestId("moved-bars")).toBeHidden();
    });
  }
});

// ------------------------------------------- after the report (Nathan, 15 October 2026)

test.describe("after the report: places are cities; the stat pages' titles", () => {
  test("no page calls a place a metro area but How it works, which says what a city means", async ({ page }) => {
    for (const u of ["/", "/city/austin-texas", "/city/new-york-new-york", "/city/eagle-pass-texas",
      "/compare", "/compare/austin-texas/san-jose-california", "/stats/who_lives_here", "/stats/political_lean",
      "/what-we-measure", "/about-crime-data", "/privacy", "/terms", "/no-such-page"]) {
      await page.goto(u);
      await expect(page.locator("main")).toBeVisible();
      const text = await page.locator("body").innerText();
      expect(text.match(/\bmetro\w*/gi) ?? [], u).toEqual([]);
    }
    await page.goto("/about");
    await expect(page.locator("main")).toContainText("A city on this site means its whole metro area");
  });

  test("a stat page's tab title starts with a capital", async ({ page }) => {
    for (const [fid, title] of [["resident_walkability_index", "Walkability by city"], ["who_lives_here", "Population by city"],
      ["rent_1br", "Rent by city"]]) {
      await page.goto(`/stats/${fid}`);
      await expect(page).toHaveTitle(new RegExp(`^${title} · `));
    }
  });

  test("the locator map's description is the registry's", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/city/austin-texas");
    await expect(page.getByTestId("locator-map")).toHaveAttribute("alt", fill(ps.map_alt, { city: "Austin, Texas" }));
  });
});
