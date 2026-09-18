import { expect, test } from "@playwright/test";

/** The narrow-search state (never a zero), the city page, balance
 * surviving suppression, and the banned-vocabulary sweep (gate 2). */

const BELOW_BAR =
  "/?self_sex=female&self_age=30&age=25-35&marital=never&edu=graduate&inc=250000&race=nhpi_nh";

test("the narrow state leads with the shape of the problem, never a count", async ({ page }) => {
  await page.goto(BELOW_BAR);
  const narrow = page.getByTestId("narrow-state");
  await expect(narrow).toBeVisible();
  await expect(narrow).toContainText("This one’s a tall order almost anywhere");
  // Phase 2g item 2.2: Nathan's body, with the search phrase opening the
  // sentence; too-few-in-the-survey is still not too-few-in-the-country
  await expect(narrow).toContainText(/doesn’t mean nobody matches that description/);
  await expect(narrow).toContainText(/unable to find enough people in the Census data/);
  await expect(narrow).toContainText(/Try expanding your search/);
  // item 2.3: the note box under the wideners is gone
  await expect(narrow).not.toContainText(/The narrower the search/);
  const text = (await narrow.textContent()) ?? "";
  expect(text).not.toMatch(/\b0\b/);
  expect(text).not.toMatch(/\bzero\b/i);
  expect(text).not.toMatch(/\d+ cities/);
  // the body reads as a sentence: the capitalised search phrase leads
  expect(text).toMatch(/Men \d+–\d+.* is a very small group in any city/);
  // the screen still offers a route to the explainer (the header nav)
  await expect(page.getByRole("link", { name: "How it works" })).toBeVisible();
  // the wideners restate the loosened query and apply it in one click.
  // On the 12-metro fixture one loosening may still be too narrow — the
  // guarantee is the state changed honestly, not that any search recovers.
  const widen = narrow.getByRole("button").first();
  await expect(widen).toContainText(/Widen the ages to \d+–\d+/);
  await widen.click();
  await expect.poll(() => page.url()).toMatch(/age=22-40/);
  const recovered = page.getByTestId("ranked-list").locator("li").first();
  const stillNarrow = page.getByTestId("narrow-state");
  await expect(recovered.or(stillNarrow).first()).toBeVisible({ timeout: 10_000 });
});

test("the city page: description, cards with bands, ranked card", async ({ page }) => {
  await page.goto("/city/provo-utah?self_sex=female&self_age=30&age=28-40&marital=never,previously");
  await expect(page.locator("h1")).toHaveText("Provo, Utah");
  // the one-line description arrives from the build (gate 4)
  await expect(page.getByTestId("city-description")).toContainText(/college town|city of about/);
  await expect(page.getByTestId("ranked-card")).toBeVisible();
  // every card shows value, unit line and a band label from the API
  for (const id of ["rent_1br", "pleasant_days", "who_lives_here"]) {
    const card = page.locator(`[data-card="${id}"]`);
    await expect(card).toBeVisible();
    const t = (await card.textContent()) ?? "";
    expect(t.length).toBeGreaterThan(10);
  }
  const rent = page.locator('[data-card="rent_1br"]');
  // five bands since m2.1.0 (item 6)
  await expect(rent).toContainText(
    /Far cheaper than most cities|Cheaper than most cities|About average for rent|Pricier than most cities|Among the priciest cities/,
  );
  await expect(rent.getByRole("link", { name: /See all cities by rent/ })).toBeVisible();
});

test("balance renders on the city page when the pool is suppressed", async ({ page }) => {
  await page.goto(`/city/provo-utah${BELOW_BAR.slice(1)}`);
  await expect(page.getByTestId("city-narrow-card")).toBeVisible();
  await expect(page.getByTestId("city-narrow-card")).toContainText(
    "A search this specific is hard to answer here",
  );
  const t = (await page.getByTestId("city-narrow-card").textContent()) ?? "";
  expect(t).not.toMatch(/\b0\b/);
  // the separately-gated balance still shows (ADR 0004)
  await expect(page.getByTestId("balance-survives")).toBeVisible();
  await expect(page.getByTestId("balance-survives")).toContainText(/per 100/);
});

const BANNED_PAGE_PATTERNS: [RegExp, string][] = [
  [/\b(odds|rivals?|markets?|supply|inventory|competitors?)\b/i, "banned vocabulary"],
  [/margin of error|±/u, "a margin"],
  [/\bCV\b/, "a CV"],
  [/\bCBSA\b|\bPUMA/i, "a geography code"],
  [/\bm\d+\.\d+\.\d+\b/, "a model version"],
  [/\b[0-9a-f]{12}\b/, "a build id"],
  [/permalink/i, "a permalink"],
];

for (const [name, url] of [
  ["home", "/"],
  ["results, narrowed", "/?self_sex=female&self_age=32&age=30-40&marital=never&edu=graduate&inc=100000"],
  ["narrow state", BELOW_BAR],
  ["city page", "/city/provo-utah?self_sex=female&self_age=30&age=28-40&marital=never,previously"],
  ["compare", "/compare/provo-utah/austin-texas?self_sex=female&self_age=30&age=28-40&marital=never,previously"],
  ["compare landing", "/compare"],
  ["stat page", "/stats/rent_1br"],
  ["stat page, population", "/stats/who_lives_here"],
  ["crime explainer", "/about-crime-data"],
  ["what we measure", "/what-we-measure"],
  ["how it works", "/how-it-works"],
] as const) {
  test(`no banned string renders: ${name}`, async ({ page }) => {
    await page.goto(url);
    await page.waitForLoadState("networkidle");
    const text = (await page.locator("body").innerText()) ?? "";
    for (const [re, what] of BANNED_PAGE_PATTERNS) {
      // the how-it-works page may speak about precision, but still never
      // in the banned vocabulary, with a code, or with a version id
      expect(text, `${name} must not render ${what}`).not.toMatch(re);
    }
  });
}
