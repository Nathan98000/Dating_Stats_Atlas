import { expect, test, type Page } from "@playwright/test";
import type { Meta } from "../src/lib/types";
import { fetchMeta } from "./helpers";

/** Phase 7 (the round-4 design review of 12 October 2026, built from
 * atlas/PHASE7_PROMPT.md). Each test sets its own window. The checks that
 * need the real build's metros (Denver, Virginia Beach) run when
 * P7_REAL_BASE names its production site (e.g. http://127.0.0.1:3400) and
 * are skipped otherwise, as CI's fixture build has neither. */
const REAL = process.env.P7_REAL_BASE;

const PHONE = { width: 390, height: 844 };
const TABLET = { width: 1024, height: 768 };

async function home(page: Page, qs = "") {
  await page.goto(`/${qs}`);
  await expect(page.locator('li[data-rank="1"]')).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}

/** Waits until the page's scroll position holds still for 150ms. */
async function settleScroll(page: Page) {
  let last = -1;
  for (let i = 0; i < 40; i++) {
    const y = await page.evaluate(() => window.scrollY);
    if (y === last) return;
    last = y;
    await page.waitForTimeout(150);
  }
}

const refine = (page: Page) =>
  page.getByTestId("bottom-bar").getByRole("button", { name: "Refine your search" });

// ---------------------------------------------------------------- A (R01)

test.describe("the bar is reachable by Tab (R01)", () => {
  for (const [name, size, scale] of [
    ["390", PHONE, 3],
    ["1024", TABLET, 1],
    ["1440 at 200% zoom", { width: 720, height: 450 }, 2],
  ] as const) {
    test(`${name}: the Tab after "Their age" lands on Refine your search, in view; Enter opens the sheet`, async ({ browser }) => {
      const ctx = await browser.newContext({ viewport: size, deviceScaleFactor: scale });
      const page = await ctx.newPage();
      await home(page);
      await page.getByTestId("age-token").focus();
      await page.keyboard.press("Tab");
      const btn = refine(page);
      await expect(btn).toBeFocused();
      await expect(btn).toBeVisible();
      await expect(btn).toBeInViewport({ ratio: 1 });
      await page.keyboard.press("Enter");
      await expect(page.getByRole("dialog", { name: "Refine your search" })).toBeVisible();
      await ctx.close();
    });
  }

  test("390: across two full Tab loops the bar is focused at least twice (the review's keyboard_bar sequence)", async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: PHONE, deviceScaleFactor: 3, isMobile: true, hasTouch: true });
    const page = await ctx.newPage();
    await home(page);
    let hits = 0;
    for (let i = 0; i < 80; i++) {
      await page.keyboard.press("Tab");
      if (await page.evaluate(() => document.activeElement?.textContent?.trim() === "Refine your search")) hits++;
    }
    expect(hits).toBeGreaterThanOrEqual(2);
    await ctx.close();
  });
});

// ---------------------------------------------------------------- A (R03)

test.describe("the opened detail comes into view (R03)", () => {
  for (const size of [{ width: 1440, height: 900 }, { width: 768, height: 1024 }]) {
    test(`${size.width}x${size.height}: clicking card #1 leaves its panel's top inside the window`, async ({ page }) => {
      await page.setViewportSize(size);
      await home(page);
      await page.locator('li[data-rank="1"]').getByTestId("card-body").click({ position: { x: 8, y: 60 } });
      const panel = page.getByTestId("card-detail");
      await expect(panel).toBeVisible();
      // the page has moved (smoothly) and come to rest
      await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
      await settleScroll(page);
      const { top, bottom } = await panel.evaluate((el) => el.getBoundingClientRect().toJSON());
      expect(top).toBeGreaterThanOrEqual(0);
      expect(top).toBeLessThan(size.height);
      // the whole panel, or (were it taller than the window) its top
      if (bottom - top <= size.height) expect(bottom).toBeLessThanOrEqual(size.height + 1);
    });
  }

  test("under reduced motion the scroll is instant", async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
    const page = await ctx.newPage();
    await home(page);
    expect(await page.evaluate(() => window.scrollY)).toBe(0);
    await page.locator('li[data-rank="1"]').getByTestId("card-body").click({ position: { x: 8, y: 60 } });
    // two frames: the detail renders, then the page moves, with no animation
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
    const y1 = await page.evaluate(() => window.scrollY);
    expect(y1).toBeGreaterThan(0);
    await page.waitForTimeout(400);
    expect(await page.evaluate(() => window.scrollY)).toBe(y1);
    await ctx.close();
  });

  test("a detail already in view doesn't move the page", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await home(page);
    await page.evaluate(() => window.scrollTo(0, 600));
    await page.locator('li[data-rank="1"]').getByTestId("card-toggle").click();
    await expect(page.getByTestId("card-detail")).toBeInViewport({ ratio: 1 });
    await page.waitForTimeout(300);
    expect(await page.evaluate(() => window.scrollY)).toBe(600);
  });
});

// ---------------------------------------------------------------- A (R08)

test("390x844: the bar waits until #1's score is above its top edge; at the top it hides (R08)", async ({ browser }) => {
  const ctx = await browser.newContext({ viewport: PHONE, deviceScaleFactor: 3, isMobile: true, hasTouch: true });
  const page = await ctx.newPage();
  await home(page);
  const bar = page.getByTestId("bottom-bar");
  await expect(bar).not.toBeInViewport();
  const geometry = () => page.evaluate(() => {
    const score = document.querySelector('[data-testid="featured-card"] [data-testid="card-score"]')!;
    const b = document.querySelector<HTMLElement>('[data-testid="bottom-bar"]')!;
    return { scoreBottom: score.getBoundingClientRect().bottom, barTop: window.innerHeight - b.offsetHeight };
  });
  for (const y of [20, 40]) {
    await page.evaluate((y) => window.scrollTo(0, y), y);
    await page.waitForTimeout(250);
    const g = await geometry();
    if (g.scoreBottom > g.barTop) await expect(bar).not.toBeInViewport();
  }
  await page.evaluate(() => window.scrollTo(0, 20));
  await page.waitForTimeout(250);
  await expect(bar).not.toBeInViewport();
  // scroll on until the score is clear of the bar's top edge
  let y = 20;
  for (;;) {
    const g = await geometry();
    if (g.scoreBottom <= g.barTop) break;
    y += 4;
    await page.evaluate((y) => window.scrollTo(0, y), y);
  }
  await expect(bar).toBeInViewport();
  // it never covers the score: the score sits above the bar's top
  const g = await geometry();
  expect(g.scoreBottom).toBeLessThanOrEqual(g.barTop);
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect(bar).not.toBeInViewport();
  await ctx.close();
});

// ---------------------------------------------------------------- A (R09)

test.describe('"/100" after every score (R09)', () => {
  for (const size of [{ width: 1440, height: 900 }, PHONE]) {
    test(`${size.width}: every row shows "/100"; its accessible text reads the score once`, async ({ page }) => {
      await page.setViewportSize(size);
      await home(page);
      const showAll = page.getByTestId("show-all");
      if (await showAll.count()) await showAll.click();
      const rows = page.locator('ol[aria-label="More cities"] > li');
      const n = await rows.count();
      expect(n).toBeGreaterThan(0);
      for (let i = 0; i < n; i++) {
        const score = rows.nth(i).getByTestId("row-score");
        await expect(score.getByTestId("score-out-of")).toHaveText("/100");
        await expect(score.getByTestId("score-out-of")).toBeVisible();
        const aria = await score.ariaSnapshot();
        expect(aria).toMatch(/^- paragraph: Overall score \d+ out of 100$/);
      }
    });
  }

  test("Compare's Overall score row shows /100 after both values", async ({ page }) => {
    await page.goto("/compare/austin-texas/san-jose-california");
    const cells = page.getByTestId("compare-score");
    await expect(cells).toHaveCount(2);
    for (const c of await cells.all()) await expect(c).toHaveText(/^\d+\/100$/);
  });
});

// ---------------------------------------------------------------- B (R05)

/** Every chip of the rows ranked `ranks` against its own bar in the opened
 * detail: its item's under cost of living and social life, or, for a
 * single-item pillar (weather, student life), the pillar's. Returns how
 * many chips it checked. */
async function chipsAgainstBars(page: Page, meta: Meta, ranks: number[]) {
  let checked = 0;
  for (const rank of ranks) {
    const li = page.locator(`li[data-rank="${rank}"]`);
    const card = (await li.getAttribute("data-testid")) === "featured-card";
    const toggle = li.getByTestId(card ? "card-toggle" : "row-toggle").locator("visible=true");
    await toggle.click();
    const detail = card ? page.getByTestId("card-detail") : li.getByTestId("row-detail");
    await expect(detail).toBeVisible();
    for (const chip of await li.getByTestId("why-chips").locator("[data-key]").all()) {
      const key = (await chip.getAttribute("data-key"))!;
      const sign = (await chip.getAttribute("data-sign")) === "plus" ? "1" : "-1";
      const item = detail.locator(`[data-testid="moved-item"]:has([data-unit="${key}"])`);
      const bar = (await item.count()) ? item
        : detail.locator(`[data-testid="moved-pillar"]:has([data-pillar="${meta.features[key].pillar}"])`);
      await expect(bar, `#${rank} ${key}`).toHaveAttribute("data-sign", sign);
      checked++;
    }
    await toggle.click();
  }
  return checked;
}

test.describe('"What moved the score" by item (R05)', () => {
  test("cost of living and social life show their items, named by their chips; the pillar rows drop the suffix", async ({ page, request }) => {
    const meta = await fetchMeta(request);
    await page.setViewportSize({ width: 1440, height: 900 });
    await home(page);
    await page.locator('li[data-rank="4"]').getByTestId("row-toggle").locator("visible=true").click();
    const detail = page.locator('li[data-rank="4"]').getByTestId("row-detail");
    for (const [pillar, keys] of [["cost", ["rent_1br", "rpp_goods"]],
      ["reach", ["resident_walkability_index", "venues_per_100k"]]] as const) {
      const block = detail.getByTestId("moved-bars").locator(":scope > li").filter({
        has: page.locator(`[data-pillar="${pillar}"]`) });
      await expect(block.locator(`[data-pillar="${pillar}"]`)).toHaveText(meta.pillars[pillar].display_name);
      const items = block.getByTestId("moved-item");
      await expect(items).toHaveCount(2);
      for (const k of keys) await expect(block.locator(`[data-unit="${k}"]`)).toHaveText(meta.features[k].chip_label!);
      // the screen reader hears the items as a list inside the pillar's item
      await expect(block.getByRole("list")).toHaveCount(1);
      await expect(block.getByRole("list").getByRole("listitem")).toHaveCount(2);
    }
    // weather and student life stay single rows
    for (const pillar of ["weather", "students"]) {
      const block = detail.getByTestId("moved-bars").locator(":scope > li").filter({
        has: page.locator(`[data-pillar="${pillar}"]`) });
      await expect(block.getByTestId("moved-item")).toHaveCount(0);
    }
    // an item's bar is about two-thirds the height of its pillar's
    const h = async (sel: string) => (await detail.locator(sel).first().boundingBox())!.height;
    const ratio = await h('[data-testid="moved-item"] [data-testid="moved-bar"]') /
      await h('[data-testid="moved-pillar"] [data-testid="moved-bar"]');
    expect(ratio).toBeGreaterThan(0.6);
    expect(ratio).toBeLessThan(0.8);
  });

  test("every chip's sign is its own bar's, on every ranked city of the default search", async ({ page, request }) => {
    const meta = await fetchMeta(request);
    await page.setViewportSize({ width: 1440, height: 900 });
    await home(page);
    const n = await page.locator("li[data-rank]").count();
    const checked = await chipsAgainstBars(page, meta, Array.from({ length: Math.min(n, 20) }, (_, i) => i + 1));
    expect(checked).toBeGreaterThan(0);
  });

  test("the desk column heading names the chips", async ({ page, request }) => {
    const meta = await fetchMeta(request);
    expect(meta.policy_strings.col_city).toBe("City · lifestyle pluses and minus");
    await page.setViewportSize({ width: 1440, height: 900 });
    await home(page);
    await expect(page.getByText("City · lifestyle pluses and minus")).toBeVisible();
  });

  test.describe("on the real build (P7_REAL_BASE)", () => {
    test.skip(!REAL, "set P7_REAL_BASE to the real build's production site");
    test("Austin after Cost and Weather 'A lot', Social life 'Not much': Rent minus, Everyday prices plus", async ({ page, request }) => {
      const meta = await fetchMeta(request);
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto(`${REAL}/?ic=a&iw=a&ir=n`);
      const austin = page.locator('li[data-slug="austin-texas"]');
      await expect(austin).toBeVisible();
      const card = (await austin.getAttribute("data-testid")) === "featured-card";
      await austin.getByTestId(card ? "card-toggle" : "row-toggle").locator("visible=true").click();
      const detail = card ? page.getByTestId("card-detail") : austin.getByTestId("row-detail");
      const cost = detail.getByTestId("moved-bars").locator(":scope > li").filter({ has: page.locator('[data-pillar="cost"]') });
      await expect(cost.locator('[data-testid="moved-item"]:has([data-unit="rent_1br"])')).toHaveAttribute("data-sign", "-1");
      await expect(cost.locator('[data-testid="moved-item"]:has([data-unit="rpp_goods"])')).toHaveAttribute("data-sign", "1");
      void meta;
    });

    test("the top 20 of the default search: every chip's sign is its own bar's", async ({ page, request }) => {
      const meta = await fetchMeta(request);
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto(`${REAL}/`);
      await expect(page.locator('li[data-rank="1"]')).toBeVisible();
      await page.getByTestId("show-more").click();
      const checked = await chipsAgainstBars(page, meta, Array.from({ length: 20 }, (_, i) => i + 1));
      expect(checked).toBeGreaterThan(30);
    });
  });
});

// ---------------------------------------------------------------- C (R04)

test.describe("a city page says when it shows the starting search (R04)", () => {
  test("cold (no query, no cookie): the note, Make it your search, and ← See the rankings to /", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await page.goto("/city/austin-texas");
    const note = page.getByTestId("city-default-note");
    await expect(note).toBeVisible();
    await expect(note).toContainText(ps.city_default_note.split("{search}")[0]);
    await expect(note.getByRole("link", { name: ps.make_it_your_search })).toBeVisible();
    const back = page.getByTestId("back-to-results");
    await expect(back).toHaveText(ps.back_to_rankings);
    await expect(back).toHaveAttribute("href", "/");
    // the note sits above the card
    const noteBox = (await note.boundingBox())!;
    const card = (await page.getByTestId("ranked-card").or(page.getByTestId("city-narrow-card")).first().boundingBox())!;
    expect(noteBox.y).toBeLessThan(card.y);
    // Compare's neutral colours: --ink-2 on --sunken, no border
    const st = await note.evaluate((el) => {
      const c = getComputedStyle(el);
      return { color: c.color, bg: c.backgroundColor, border: c.borderTopWidth };
    });
    expect(st.color).toBe("rgb(90, 82, 87)");
    expect(st.bg).toBe("rgb(243, 236, 232)");
    expect(st.border).toBe("0px");
  });

  test("with a search in the query, or in the cookie: neither", async ({ page, context, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await page.goto("/city/austin-texas?ic=a");
    await expect(page.getByTestId("city-default-note")).toHaveCount(0);
    await expect(page.getByTestId("back-to-results")).toHaveText(ps.back_to_results);
    await context.addCookies([{ name: "dsa_prefs", value: encodeURIComponent("ic=a"), url: page.url() }]);
    await page.goto("/city/austin-texas");
    await expect(page.getByTestId("city-default-note")).toHaveCount(0);
    await expect(page.getByTestId("back-to-results")).toHaveText(ps.back_to_results);
  });

  test("Compare's note links with the registry's words", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await page.goto("/compare/austin-texas/san-jose-california");
    await expect(page.getByTestId("default-profile-note").getByRole("link", { name: ps.make_it_your_search })).toBeVisible();
    await expect(page.getByTestId("back-to-results")).toHaveText(ps.back_to_results);
  });

  test.describe("on the real build (P7_REAL_BASE)", () => {
    test.skip(!REAL, "set P7_REAL_BASE to the real build's production site");
    test("/city/virginia-beach-virginia, cold: the note and ← See the rankings", async ({ page }) => {
      await page.goto(`${REAL}/city/virginia-beach-virginia`);
      await expect(page.getByTestId("city-default-note")).toBeVisible();
      await expect(page.getByTestId("back-to-results")).toHaveText("← See the rankings");
    });
  });
});

// ---------------------------------------------------------------- C (R14)

test.describe("Compare's unjudged rows (R14)", () => {
  test("Who lives here names the larger city and the gap, in --ink-2, with no ▲", async ({ page }) => {
    await page.goto("/compare/austin-texas/san-jose-california");
    const cell = page.locator('[data-diff-for="who_lives_here"]');
    await expect(cell).toHaveAttribute("data-edge", "0");
    await expect(cell).toHaveText(/^(Austin|San Jose), by [\d,]+$/);
    await expect(cell.locator("svg")).toHaveCount(0);
    expect(await cell.locator("[data-diff-value]").evaluate((el) => getComputedStyle(el).color)).toBe("rgb(90, 82, 87)");
    // political lean still shows no difference
    await expect(page.locator('[data-no-diff="political_lean"]')).toHaveText("");
  });

  test.describe("on the real build (P7_REAL_BASE)", () => {
    test.skip(!REAL, "set P7_REAL_BASE to the real build's production site");
    test("Austin–Denver: Who lives here reads 'Denver, by 600,000'; balance's tie reads 'Same'", async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto(`${REAL}/compare/austin-texas/denver-colorado`);
      const who = page.locator('[data-diff-for="who_lives_here"]');
      await expect(who).toHaveText("Denver, by 600,000");
      await expect(who.locator("svg")).toHaveCount(0);
      const bal = page.locator('[data-diff-for="balance"]');
      await expect(bal).toHaveText("Same");
      await expect(bal.locator("svg")).toHaveCount(0);
    });
  });
});

// ---------------------------------------------------------------- C (button)

test("the city page's 'Compare with another city' is outlined, like 'Change your search'; the foot's 'Compare cities' stays filled", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/city/austin-texas");
  const style = (name: string | RegExp) => page.getByRole("button", { name, exact: true }).first().evaluate((el) => {
    const c = getComputedStyle(el);
    return { bg: c.backgroundColor, color: c.color, border: c.borderTopColor, h: el.getBoundingClientRect().height };
  });
  const top = await style("Compare with another city");
  expect(top.bg).toBe("rgb(255, 255, 255)");
  expect(top.color).toBe("rgb(32, 27, 29)");
  const change = await page.getByRole("link", { name: "Change your search" }).evaluate((el) => {
    const c = getComputedStyle(el);
    return { border: c.borderTopColor, h: el.getBoundingClientRect().height };
  });
  expect(top.border).toBe(change.border);
  expect(top.h).toBe(change.h);
  const foot = await style("Compare cities");
  expect(foot.bg).toBe("rgb(158, 59, 87)");
});

// ---------------------------------------------------------------- C (R02)

const PAGES = ["/", "/about", "/what-we-measure", "/about-crime-data", "/privacy", "/terms",
  "/stats/rent_1br", "/city/austin-texas", "/compare", "/compare/austin-texas/san-jose-california",
  "/no-such-page"];

test("every page links the site's icons, which answer as images; the starter files are gone (R02)", async ({ page, request }) => {
  for (const path of PAGES) {
    await page.goto(path);
    const hrefs = await page.evaluate(() => Object.fromEntries(["icon", "apple-touch-icon"].map((rel) =>
      [rel, [...document.querySelectorAll(`link[rel="${rel}"]`)].map((l) => l.getAttribute("href")!)])));
    expect(hrefs.icon.some((h) => h.startsWith("/favicon.ico")), path).toBe(true);
    expect(hrefs.icon.some((h) => h.startsWith("/icon.png")), path).toBe(true);
    expect(hrefs["apple-touch-icon"].some((h) => h.startsWith("/apple-icon.png")), path).toBe(true);
    for (const h of [...hrefs.icon, ...hrefs["apple-touch-icon"]]) {
      const r = await request.get(h);
      expect(r.status(), h).toBe(200);
      expect(r.headers()["content-type"], h).toMatch(/^image\//);
    }
  }
  for (const gone of ["/next.svg", "/vercel.svg", "/file.svg", "/globe.svg", "/window.svg", "/hero.jpg"]) {
    expect((await request.get(gone)).status(), gone).toBe(404);
  }
});
