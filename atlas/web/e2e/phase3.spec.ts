import { expect, test } from "@playwright/test";

/** Phase 3 (m3.0.0, ADR 0009), renamed in m4.0.0 (ADR 0018): the slider's
 * second pole is compatibility; the "about you" inputs, kept in the
 * browser and never sent (since Phase 4b race is one select, "Prefer not
 * to say" by default); the match figure on rows, the city page and the
 * compare table (since Phase 4b with no information box and no band
 * words); balance still displayed everywhere it was and scored nowhere;
 * the plain-words account on About us. Every string comes from the
 * registry through /v1/meta. */

const DEFAULT_QS = "sex=male&self_age=30&age=28-40&marital=never,previously";

test("the slider's poles are pool size and compatibility, from the registry", async ({ page }) => {
  await page.goto("/");
  const poles = page.getByTestId("slider-poles");
  await expect(poles).toContainText("Dating pool size");
  await expect(poles).toContainText("Compatibility");
  await expect(poles).not.toContainText("balance");
  await expect(poles).not.toContainText(/chances of matching/i);
  const slider = page.locator("input.svo").first();
  await expect(slider).toHaveAttribute("aria-valuetext", /toward compatibility/);
});

test("the details about you stay in the browser: no request, URL or cookie carries them, and they select the figures", async ({ page, context }) => {
  const rankCalls: string[] = [];
  page.on("request", (req) => {
    if (req.url().includes("/api/rank")) rankCalls.push(req.postData() ?? "");
  });
  await page.goto("/");
  const edu = page.getByTestId("self-edu");
  const race = page.getByTestId("self-race");
  await expect(edu).toHaveValue("");
  // Phase 4b: race is one select, "Prefer not to say" by default — no
  // switch and no note beside it
  await expect(race).toHaveValue("");
  await expect(race).toBeEnabled();
  await expect(page.getByTestId("self-race-switch")).toHaveCount(0);
  await expect(page.getByTestId("self-race-note")).toHaveCount(0);
  await expect(page.getByTestId("about-you-note")).toHaveCount(0);
  // the "unset" option and the four levels are registry strings
  await expect(edu.locator("option").first()).toHaveText("Prefer not to say");
  await expect(edu.locator("option")).toHaveCount(5);
  await expect(race.locator("option").first()).toHaveText("Prefer not to say");
  await expect(race.locator("option")).toHaveCount(9);
  const rows = page.getByTestId("ranked-list").locator("li");
  await expect(rows.first()).toBeVisible();
  const figures = async () => JSON.stringify(await rows.evaluateAll((els) =>
    els.map((e) => `${e.getAttribute("data-cbsa")}:${e.querySelector('[data-testid="match-figure"]')?.textContent ?? ""}`)));
  const before = await figures();
  // disclose education and race: the figures change at once, with no
  // request at all — the response already held every variant
  await edu.selectOption("graduate");
  await race.selectOption("asian_nh");
  await expect.poll(figures, { timeout: 10_000 }).not.toBe(before);
  expect(rankCalls).toEqual([]);
  // nothing about the visitor in the address, the cookie or storage keys
  // other than the one the browser keeps
  expect(page.url()).not.toMatch(/self_(sex|edu|race)|graduate|asian_nh/);
  for (const c of await context.cookies()) {
    expect(decodeURIComponent(c.value)).not.toMatch(/self_(sex|edu|race)|graduate|asian_nh/);
  }
  const stored = await page.evaluate(() => window.localStorage.getItem("dsa_about_you"));
  expect(JSON.parse(stored ?? "{}")).toEqual({ edu: "graduate", race: "asian_nh" });
  // a reload keeps them and shows the same figures
  const disclosed = await figures();
  await page.reload();
  await expect(rows.first()).toBeVisible();
  await expect.poll(figures).toBe(disclosed);
  await expect(page.getByTestId("self-edu")).toHaveValue("graduate");
  await expect(page.getByTestId("self-race")).toHaveValue("asian_nh");
  // "Prefer not to say" removes the race from the browser too
  await page.getByTestId("self-race").selectOption("");
  const after = await page.evaluate(() => window.localStorage.getItem("dsa_about_you"));
  expect(JSON.parse(after ?? "{}")).toEqual({ edu: "graduate" });
});

test("every ranked row shows the compatibility figure — no band words, no information box — and balance beside it", async ({ page }) => {
  await page.goto(`/?${DEFAULT_QS}`);
  const first = page.getByTestId("ranked-list").locator("li").first();
  await expect(first).toBeVisible();
  const fig = first.getByTestId("match-figure");
  await expect(fig).toContainText("Compatibility");
  await expect(fig).toContainText(/\d+/);
  await expect(fig).toContainText("where 100 is the US average");
  // Phase 4b (ADR 0018 amended): the number against 100 says it
  await expect(fig).not.toContainText(
    /Far below most cities|Below most cities|About average|Above most cities|Far above most cities/);
  await expect(fig.getByTestId("match-band")).toHaveCount(0);
  await expect(fig.getByRole("button")).toHaveCount(0);
  await expect(first.getByTestId("match-info")).toHaveCount(0);
  // balance still renders, in the API's words
  await expect(first.getByTestId("balance-tally")).toContainText("Dating pool balance");
  await expect(first.getByTestId("balance-tally")).toContainText(/per 100/);
});

test("the city page and the compare table carry the figure; balance keeps its tally", async ({ page }) => {
  await page.goto(`/city/provo-utah?${DEFAULT_QS}`);
  const card = page.getByTestId("ranked-card");
  await expect(card.getByTestId("match-figure")).toContainText("Compatibility");
  await expect(card).toContainText(/per 100/);
  await page.goto(`/compare/provo-utah/austin-texas?${DEFAULT_QS}`);
  const table = page.getByTestId("compare-table");
  await expect(table).toContainText("Compatibility");
  await expect(table).toContainText("Dating pool balance");
  await expect(table.locator('[data-diff-for="match_propensity"]')).toBeVisible();
  await expect(table.locator('[data-diff-for="balance"]')).toBeVisible();
});

test("What we measure lists compatibility as a people measure and balance as a statistic", async ({ page }) => {
  await page.goto("/what-we-measure");
  const people = page.locator('[data-group="people"]');
  const text = ((await people.textContent()) ?? "").replace(/\s+/g, " ");
  expect(text).toMatch(/Dating pool size/);
  expect(text).toMatch(/Compatibility/);
  expect(text).toMatch(/How closely the people who match your search resemble the people who actually pair with someone like you/);
  expect(text).toMatch(/Dating pool balance/);
  expect(text).toMatch(/Number of single men per 100 single women/);
});

test("About us gives the one account of the figure, in Nathan's words", async ({ page }) => {
  // Nathan's About us copy (after Phase 4e, 2026-10-06): the figure's
  // account, the same-sex paragraph, and the slider between pool size and
  // compatibility; the old "chances of matching" never comes back, and the
  // figure's anchors survive for old links
  await page.goto("/about");
  const article = page.locator("article.prose-method");
  const text = ((await article.textContent()) ?? "").replace(/\s+/g, " ");
  expect(text).toMatch(/how often each age gap, education pairing, and racial\/ethnic pairing actually occurs/);
  expect(text).toMatch(/where 100 is the US average/);
  expect(text).toMatch(/Racial and ethnic pairings aren't used/);
  expect(text).toMatch(/between pool size and compatibility/);
  expect(text).not.toMatch(/chances of matching/i);
  expect(text).not.toMatch(/carry its weight/);
  await expect(page.locator("#compatibility")).toHaveCount(1);
  await expect(page.locator("#chances-of-matching")).toHaveCount(1);
});

