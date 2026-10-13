import { expect, test, type Page } from "@playwright/test";

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
