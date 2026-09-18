import { expect, test } from "@playwright/test";

/** Phase 2d's new surfaces: the crime block (gate 4), the static stat
 * pages agreeing with the city pages cell for cell (gate 5), the compare
 * landing with its pickers and default-profile label (item 8), and the
 * restructured How it works with every item-10 disclosure (gate 6). */

const CITY_URL =
  "/city/provo-utah?self_sex=female&self_age=30&age=28-40&marital=never,previously";

test("crime is two cards in the stats grid, detail in the popover — never scored", async ({ page }) => {
  // Phase 2e item 2: rate + five-band position on the face, coverage and
  // the FBI's caution INSIDE the accessible popover, with the explainer
  // link; nothing about agencies or panels on the card face
  await page.goto(CITY_URL);
  const violent = page.locator('[data-card="violent_crime_rate"]');
  const property = page.locator('[data-card="property_crime_rate"]');
  await expect(violent).toBeVisible();
  await expect(property).toBeVisible();
  const face = (await violent.textContent()) ?? "";
  // the face carries rate, unit and band — never NIBRS, agencies,
  // panels or coverage talk (that lives in the popover)
  expect(face).not.toMatch(/NIBRS|agenc|panel|coverage|full year/i);
  // the ⓘ opens on hover AND focus, closes on Escape (the Phase 2d
  // pattern, shared component)
  const info = violent.getByTestId("crime-info-violent_crime_rate");
  await info.hover();
  const note = page.getByTestId("crime-info-violent_crime_rate-note");
  await expect(note).toBeVisible();
  // Phase 2f item 5.3: the approved caution, with "See more details" as
  // the link; the per-city coverage sentence left this surface
  await expect(note).toContainText(/FBI cautions against using this number/);
  await expect(note).not.toContainText(/reported a full year/);
  await expect(
    note.getByRole("link", { name: "See more details" })).toBeVisible();
  await info.focus();
  await page.keyboard.press("Escape");
  await expect(note).toHaveCount(0);
  // a figure card also carries its five-band position
  if (!face.includes("Not enough")) {
    await expect(violent).toContainText(
      /Far lower|Lower than|About average|Higher than|Far higher/);
  }
});

test("compare-page crime: two plain numbers and one banner, detail one click away", async ({ page }) => {
  // Phase 2e item 11
  await page.goto(
    "/compare/provo-utah/austin-texas?self_sex=female&self_age=30&age=28-40&marital=never,previously");
  const block = page.getByTestId("compare-crime");
  await expect(block).toBeVisible();
  const banner = page.getByTestId("crime-compare-banner");
  // Phase 2f item 6.4: the approved caution wording, verbatim
  await expect(banner).toContainText(
    /FBI cautions against using these numbers to compare cities/);
  await expect(
    banner.getByRole("link", { name: "See more details" })).toBeVisible();
  // beyond the banner: numbers with their per-100,000 unit (item 6.5) —
  // still no coverage percentages, no agency talk, no paragraph
  const table = (await block.locator("table").textContent()) ?? "";
  expect(table).not.toMatch(/coverage|agenc|panel|%/i);
  await expect(block).toContainText("Violent crime");
  await expect(block).toContainText("Property crime");
  expect(table).toContain("reported per 100,000 people a year");
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
  // the stat index moved to What we measure in Phase 2e, taking its
  // seven bullets with it; real lists remain
  expect(await article.locator("ul li").count()).toBeGreaterThanOrEqual(2);
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
  // Phase 2e item 12: the index moved to What we measure; How it works
  // LINKS to it instead of repeating it
  await expect(
    article.getByRole("link", { name: /What we measure/ })).toBeVisible();
  expect(text).not.toMatch(/Cities by rent/);
  // and the m2.2.0 race disclosure describes summable arithmetic, with
  // no always-counted claim anywhere
  expect(text).toMatch(/eight boxes/i);
  expect(text).not.toMatch(/always (counted|included)/i);
});
