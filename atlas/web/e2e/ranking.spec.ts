import { expect, test } from "@playwright/test";

/** Core ranking-page behavior against the pinned fixture build: URL state,
 * margins in the row in the required words, the slider visibly reordering
 * the list, and a hydration-clean first load. */

test("first ranking is server-rendered with margins in every row", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  const t0 = Date.now();
  await page.goto("/");
  await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
  const firstPaintMs = Date.now() - t0;
  test.info().annotations.push({
    type: "time-to-first-ranking-ms",
    description: String(firstPaintMs),
  });

  // gate 1: every row carries its margin, in the policy's words — never a
  // bare "±", never behind a tooltip
  const rows = page.getByTestId("ranked-list").locator("li");
  const n = await rows.count();
  expect(n).toBeGreaterThan(0);
  for (let i = 0; i < n; i++) {
    await expect(rows.nth(i)).toContainText(/margin at least ±[\d,]+/);
  }
  // the served CV never sits in the row — detail only
  await expect(rows.first()).not.toContainText(/CV/);

  // no hydration mismatch on a fresh load (the class of defect the dev
  // pass caught by hand)
  expect(errors.filter((e) => e.includes("hydrat"))).toEqual([]);
});

test("the URL is the state and round-trips", async ({ page }) => {
  await page.goto("/?self_sex=male&self_age=41&age=32-45&marital=never,previously&inc=50000");
  await expect(page.locator("#main h2").first()).toContainText("a man, 41");
  await expect(page.locator("#main h2").first()).toContainText("32–45");
  // the income select reflects the URL, offering only band edges
  const income = page.getByLabel("Income (minimum)");
  await expect(income).toHaveValue("50000");
  const options = await income.locator("option").allTextContents();
  expect(options.join(" ")).not.toMatch(/60,000/);
});

test("moving the slider reorders the list and rewrites the URL", async ({ page }) => {
  await page.goto("/");
  const rows = page.getByTestId("ranked-list").locator("li");
  await expect(rows.first()).toBeVisible();
  const order = () =>
    rows.evaluateAll((els) => els.map((e) => e.getAttribute("data-cbsa")));
  const slider = page.locator("input.svo").first();
  await slider.focus();
  await page.keyboard.press("Home"); // s = 0, most options
  await expect(page).toHaveURL(/[?&]s=0/);
  await expect.poll(async () => (await order()).length, { timeout: 10_000 }).toBeGreaterThan(0);
  await page.waitForTimeout(400); // debounce + fetch settle
  const atOptions = await order();
  await page.keyboard.press("End"); // s = 1, best odds
  await expect(page).toHaveURL(/[?&]s=1/);
  await expect
    .poll(async () => (await order())[0], { timeout: 10_000 })
    .not.toBe(atOptions[0]);
  const atOdds = await order();
  expect(atOdds).not.toEqual(atOptions);
});

test("the top movers change with the weights (ADR 0003b)", async ({ page }) => {
  await page.goto("/");
  const firstRow = page.getByTestId("ranked-list").locator("li").first();
  await expect(firstRow).toBeVisible();
  const moversBefore = await firstRow.textContent();
  const slider = page.locator("input.svo").first();
  await slider.focus();
  await page.keyboard.press("End");
  // the list reorders; compare the SAME metro's mover text before/after
  const cbsa = await firstRow.getAttribute("data-cbsa");
  await expect
    .poll(async () => {
      const row = page.locator(`li[data-cbsa="${cbsa}"]`);
      const txt = (await row.count()) ? await row.textContent() : null;
      return txt !== moversBefore;
    }, { timeout: 10_000 })
    .toBe(true);
});

test("keyboard-only path through the hero control", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
  // tab from the top: skip link, masthead links, search, then the slider
  let reached = false;
  for (let i = 0; i < 15; i++) {
    await page.keyboard.press("Tab");
    const cls = await page.evaluate(() => document.activeElement?.className ?? "");
    if (cls.includes("svo")) {
      reached = true;
      break;
    }
  }
  expect(reached, "slider reachable by Tab alone").toBe(true);
  // focus is visible (keyboard focus sets :focus-visible on the input)
  const outline = await page.evaluate(() => {
    const el = document.activeElement as HTMLElement;
    return getComputedStyle(el).outlineStyle;
  });
  expect(outline, "a visible focus ring on the slider").not.toBe("none");
  const url0 = page.url();
  await page.keyboard.press("ArrowRight");
  await expect.poll(() => page.url()).not.toBe(url0);
  // and a row expands from the keyboard
  const btn = page.getByRole("button", { name: "Every stat" }).first();
  await btn.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("table").first()).toBeVisible();
});
