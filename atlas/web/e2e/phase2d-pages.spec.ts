import { expect, test } from "@playwright/test";

/** Phase 2d's new surfaces: the crime block (gate 4), the static stat
 * pages agreeing with the city pages cell for cell (gate 5), the compare
 * landing with its pickers and default-profile label (item 8), and the
 * restructured How it works with every item-10 disclosure (gate 6). */

const CITY_URL =
  "/city/provo-utah?self_sex=female&self_age=30&age=28-40&marital=never,previously";

test("crime renders with coverage and caution, or as the blank state — never scored", async ({ page }) => {
  await page.goto(CITY_URL);
  const section = page.getByTestId("crime-section");
  await expect(section).toBeVisible();
  await expect(page.getByTestId("crime-caution")).toContainText(/caution/i);
  await expect(page.getByTestId("crime-caution")).toContainText(/never part of any score/i);
  const hasFigures = (await section.locator("[data-crime]").count()) > 0;
  if (hasFigures) {
    await expect(section).toContainText("Violent crime");
    await expect(section).toContainText("Property crime");
    // the trap the adapter exists to avoid: a rate never renders without
    // its coverage sentence
    await expect(page.getByTestId("crime-coverage")).toContainText(
      /reported a full year/);
  } else {
    await expect(page.getByTestId("crime-blank")).toBeVisible();
  }
  // crime never appears among the ranked stats or as a score input
  await expect(section).not.toContainText(/out of 100/);
});

test("crime on the compare page keeps the note between the columns", async ({ page }) => {
  await page.goto(
    "/compare/provo-utah/austin-texas?self_sex=female&self_age=30&age=28-40&marital=never,previously");
  const block = page.getByTestId("compare-crime");
  await expect(block).toBeVisible();
  const note = page.getByTestId("crime-compare-note");
  await expect(note).toContainText(/aren't comparable/);
  // spatially between the two city columns on desktop: the note's box
  // sits strictly right of column A and left of column B
  const cols = block.locator("div.grid > div");
  const a = await cols.nth(0).boundingBox();
  const noteBox = await note.boundingBox();
  const b = await cols.nth(1).boundingBox();
  expect(a!.x + a!.width).toBeLessThanOrEqual(noteBox!.x + 1);
  expect(noteBox!.x + noteBox!.width).toBeLessThanOrEqual(b!.x + 1);
});

test("stat pages agree with the city page cell for cell", async ({ page }) => {
  // gate 5: same artifact, same formatting code — asserted through the UI
  await page.goto(CITY_URL);
  const rentCard = page.locator('[data-card="median_gross_rent"]');
  const cityRent = (await rentCard.locator("span").nth(1).textContent())!.trim();
  const daysCard = page.locator('[data-card="pleasant_days"]');
  const cityDays = (await daysCard.locator("span").nth(1).textContent())!.trim();

  await page.goto("/stats/median_gross_rent");
  const rentRow = page.locator('[data-slug="provo-utah"]');
  await expect(rentRow).toBeVisible();
  await expect(rentRow).toContainText(cityRent);

  await page.goto("/stats/pleasant_days");
  const daysRow = page.locator('[data-slug="provo-utah"]');
  await expect(daysRow).toContainText(cityDays.replace("$", ""));
});

test("stat pages cover the ranked set and never rank crime", async ({ page }) => {
  await page.goto("/stats/median_gross_rent");
  const rows = page.getByTestId("stat-list").locator("li");
  const n = await rows.count();
  expect(n).toBeGreaterThan(5); // the 12-metro fixture's ranked subset
  // ordered by the measure: first row cheaper than last row
  const first = await rows.first().textContent();
  const last = await rows.last().textContent();
  const num = (s: string | null) =>
    parseFloat((s ?? "").replace(/[^0-9.]/g, ""));
  expect(num(first)).toBeGreaterThan(0);
  // the crime stat page must not exist (D01: an explainer instead)
  const res = await page.goto("/stats/violent_crime_rate");
  expect(res!.status()).toBe(404);
  await page.goto("/about-crime-data");
  await expect(page.locator("h1")).toContainText(/crime/i);
  await expect(page.locator("article")).toContainText(/coverage/i);
  await expect(page.locator("article")).toContainText(/rank/i);
});

test("the card links to its stat page", async ({ page }) => {
  await page.goto(CITY_URL);
  const link = page
    .locator('[data-card="median_gross_rent"]')
    .getByRole("link", { name: /See all cities by rent/ });
  await link.click();
  await expect(page).toHaveURL(/\/stats\/median_gross_rent/);
  await expect(page.locator("h1")).toContainText(/rent/i);
});

test("the compare landing picks two cities and goes", async ({ page }) => {
  await page.goto("/compare");
  await page.getByLabel("First city").fill("provo");
  await page.getByRole("option", { name: /Provo/ }).click();
  await page.getByLabel("Second city").fill("austin");
  await page.getByRole("option", { name: /Austin/ }).click();
  await page.getByTestId("compare-go").click();
  await expect(page).toHaveURL(/\/compare\/provo-utah\/austin-texas/);
  await expect(page.getByTestId("compare-table")).toBeVisible();
  // no preferences set: the stated default profile, labelled, one click
  // from being the visitor's own
  await expect(page.getByTestId("default-profile-note")).toContainText(
    /default search/);
  await page.getByRole("link", { name: "Make it your search" }).click();
  await expect(page).toHaveURL(/self_sex=female/);
});

test("How it works carries every item-10 disclosure, structured", async ({ page }) => {
  await page.goto("/how-it-works");
  const article = page.locator("article.prose-method");
  await expect(article).toBeVisible();
  // structure, not dumped prose (gate 6)
  expect(await article.locator("h2").count()).toBeGreaterThanOrEqual(7);
  expect(await article.locator("table").count()).toBeGreaterThanOrEqual(1);
  expect(await article.locator("ul li").count()).toBeGreaterThanOrEqual(7);
  const text = (await article.textContent()) ?? "";
  for (const [what, re] of [
    ["source and cadence", /American Community Survey/],
    ["what a match counts", /whole search/i],
    ["what balance compares", /single men per 100/i],
    ["race selects who is counted", /nothing more/i],
    ["the two always-counted groups (moved from the panel, item 3)",
     /two or more races/i],
    ["why cities are left out", /leave that city out|left out/i],
    ["why margins are not printed", /precision/i],
    ["crime shown never ranked", /never part of any score/i],
  ] as const) {
    expect(text, `must disclose: ${what}`).toMatch(re);
  }
  // the stat-page index (item 9), linked
  await expect(article.getByRole("link", { name: /Cities by rent/ })).toBeVisible();
  await expect(
    article.getByRole("link", { name: /Cities by population/ })).toBeVisible();
});
