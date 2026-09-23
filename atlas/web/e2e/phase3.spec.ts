import { expect, test } from "@playwright/test";

/** Phase 3 (m3.0.0, ADR 0009): the slider's second pole is chances of
 * matching; two optional "about you" inputs; the match figure with its
 * information box on rows, the city page and the compare table; balance
 * still displayed everywhere it was and scored nowhere; the plain-words
 * account on How it works, reachable from the information box. Every
 * string comes from the registry through /v1/meta. */

const DEFAULT_QS = "self_sex=female&self_age=30&age=28-40&marital=never,previously";

test("the slider's poles are pool size and chances of matching, from the registry", async ({ page }) => {
  await page.goto("/");
  const poles = page.getByTestId("slider-poles");
  await expect(poles).toContainText("Dating pool size");
  await expect(poles).toContainText("Chances of matching");
  await expect(poles).not.toContainText("balance");
  const slider = page.locator("input.svo").first();
  await expect(slider).toHaveAttribute("aria-valuetext", /toward chances of matching/);
});

test("the two optional inputs default unset, carry the URL and the cookie, and never gate a ranking", async ({ page, context }) => {
  await page.goto("/");
  const edu = page.getByTestId("self-edu");
  const race = page.getByTestId("self-race");
  await expect(edu).toHaveValue("");
  await expect(race).toHaveValue("");
  await expect(page.getByTestId("about-you-note")).toContainText(/Optional/);
  // the "unset" option and the four levels are registry strings
  await expect(edu.locator("option").first()).toHaveText("Prefer not to say");
  await expect(edu.locator("option")).toHaveCount(5);
  await expect(race.locator("option")).toHaveCount(9);
  const rows = page.getByTestId("ranked-list").locator("li");
  await expect(rows.first()).toBeVisible();
  const before = await rows.evaluateAll((els) =>
    els.map((e) => e.querySelector('[data-testid="match-figure"]')?.textContent ?? ""));
  expect(before.every((t) => t.length > 0)).toBe(true);
  // disclose both: the URL carries them, the ranking still answers, the
  // figures change (the disclosure gap the report measures)
  await edu.selectOption("graduate");
  await expect(page).toHaveURL(/self_edu=graduate/);
  await race.selectOption("asian_nh");
  await expect(page).toHaveURL(/self_race=asian_nh/);
  await expect
    .poll(async () => JSON.stringify(await rows.evaluateAll((els) =>
      els.map((e) => e.querySelector('[data-testid="match-figure"]')?.textContent ?? ""))),
      { timeout: 10_000 })
    .not.toBe(JSON.stringify(before));
  await expect(rows.first()).toBeVisible();
  const cookie = (await context.cookies()).find((c) => c.name === "dsa_prefs");
  expect(decodeURIComponent(cookie?.value ?? "")).toMatch(/self_edu=graduate/);
  expect(decodeURIComponent(cookie?.value ?? "")).toMatch(/self_race=asian_nh/);
  // unset again: the parameters leave the URL
  await edu.selectOption("");
  await expect(page).not.toHaveURL(/self_edu=/);
});

test("every ranked row shows chances of matching with its band and information box, and balance beside it", async ({ page }) => {
  await page.goto(`/?${DEFAULT_QS}`);
  const first = page.getByTestId("ranked-list").locator("li").first();
  await expect(first).toBeVisible();
  const fig = first.getByTestId("match-figure");
  await expect(fig).toContainText("Chances of matching");
  await expect(fig).toContainText(/\d+/);
  await expect(fig).toContainText("where 100 is the US average");
  await expect(fig.getByTestId("match-band")).toContainText(
    /Far below most cities|Below most cities|About average|Above most cities|Far above most cities/);
  // balance still renders, in the API's words
  await expect(first.getByTestId("balance-tally")).toContainText("Dating pool balance");
  await expect(first.getByTestId("balance-tally")).toContainText(/per 100/);
  // the information box: Nathan's text and the link to the account
  const btn = first.getByTestId("match-info");
  await btn.focus();
  const note = first.getByTestId("match-info-note");
  await expect(note).toBeVisible();
  await expect(note).toContainText(/pattern of who actually forms couples in Census data/);
  await expect(note.getByRole("link", { name: "How this is measured" })).toHaveAttribute(
    "href", /how-it-works#chances-of-matching/);
});

test("the city page and the compare table carry the figure; balance keeps its tally", async ({ page }) => {
  await page.goto(`/city/provo-utah?${DEFAULT_QS}`);
  const card = page.getByTestId("ranked-card");
  await expect(card.getByTestId("match-figure")).toContainText("Chances of matching");
  await expect(card).toContainText(/per 100/);
  await page.goto(`/compare/provo-utah/austin-texas?${DEFAULT_QS}`);
  const table = page.getByTestId("compare-table");
  await expect(table).toContainText("Chances of matching");
  await expect(table).toContainText("Dating pool balance");
  await expect(table.locator('[data-diff-for="match_propensity"]')).toBeVisible();
  await expect(table.locator('[data-diff-for="balance"]')).toBeVisible();
});

test("What we measure lists chances of matching as a people measure and balance as a statistic", async ({ page }) => {
  await page.goto("/what-we-measure");
  const people = page.locator('[data-group="people"]');
  const text = ((await people.textContent()) ?? "").replace(/\s+/g, " ");
  expect(text).toMatch(/Dating pool size/);
  expect(text).toMatch(/Chances of matching/);
  expect(text).toMatch(/How closely the people who match your search resemble the people who actually pair with someone like you/);
  expect(text).toMatch(/Dating pool balance/);
  expect(text).toMatch(/Number of single men per 100 single women/);
});

test("How it works names the three inputs in one account and no longer calls balance part of the score", async ({ page }) => {
  await page.goto("/how-it-works");
  const article = page.locator("article.prose-method");
  const text = ((await article.textContent()) ?? "").replace(/\s+/g, " ");
  expect(text).toMatch(/each age gap, each education pairing and each racial or ethnic pairing/);
  expect(text).toMatch(/aggregate pattern from recent unions, not a prediction about any one person/);
  expect(text).toMatch(/between pool size and chances of matching/);
  expect(text).toMatch(/not part of the score/);
  expect(text).not.toMatch(/carry its weight/);
  await expect(page.locator("#chances-of-matching")).toHaveCount(1);
});
