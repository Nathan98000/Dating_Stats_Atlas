import { expect, test } from "@playwright/test";

/** Phase 2f's surfaces: the four tones rendering by band × direction
 * (gate 2), preferences following the visitor with explicit parameters
 * always winning (gate 3), the popover that stays open long enough to
 * use (gate 4), every compare difference equal to the subtraction of
 * the two displayed values with the grey rules and the em dash (gate
 * 5), aligned card indicators (gate 6, screenshots in the shoot
 * script), and the reworked stat pages (gate 8). */

const CITY_URL =
  "/city/provo-utah?self_sex=female&self_age=30&age=28-40&marital=never,previously";
const DEFAULTISH =
  "?self_sex=female&self_age=30&age=28-40&marital=never,previously";

const RGB = {
  good_strong: "rgb(27, 94, 75)",
  good: "rgb(46, 125, 107)",
  neutral: "rgb(90, 82, 87)", // --ink-2
  poor: "rgb(176, 84, 62)",
  poor_strong: "rgb(138, 43, 24)",
  grey: "rgb(117, 107, 112)", // --ink-3, the diff column's no-judgement
};

test("all four coloured tones render, extremes darker, position × direction only", async ({ page }) => {
  // Provo: walkability sits in the top band of a good_high feature
  // (good_strong), nice days in the bottom band (poor_strong), rent in
  // band four of a good_low feature (poor), students top band but
  // neutral-by-registry
  await page.goto(CITY_URL);
  const label = (card: string) =>
    page.locator(`[data-card="${card}"] [data-testid="band-label"]`);
  await expect(label("resident_walkability_index")).toHaveText(
    "Among the most walkable");
  await expect(label("resident_walkability_index")).toHaveCSS(
    "color", RGB.good_strong);
  await expect(label("pleasant_days")).toHaveText("Far fewer than most cities");
  await expect(label("pleasant_days")).toHaveCSS("color", RGB.poor_strong);
  await expect(label("median_gross_rent")).toHaveText("Pricier than most cities");
  await expect(label("median_gross_rent")).toHaveCSS("color", RGB.poor);
  await expect(label("students_per_1k_adults")).toHaveText(
    "Far more than most cities");
  await expect(label("students_per_1k_adults")).toHaveCSS("color", RGB.neutral);

  // Austin carries the light green: walkable band four of good_high
  await page.goto(`/city/austin-texas${DEFAULTISH}`);
  await expect(label("resident_walkability_index")).toHaveCSS("color", RGB.good);
  // the lit indicator segment takes the label's colour (item 1)
  const lit = page.locator(
    '[data-card="median_gross_rent"] div[aria-hidden] span',
  ).nth(4); // Austin rent: highest band lit
  await expect(lit).toHaveCSS("background-color", RGB.poor_strong);
});

test("the popover survives the pointer's trip into the note, link clickable (item 3)", async ({ page }) => {
  await page.goto(CITY_URL);
  const info = page.getByTestId("crime-info-violent_crime_rate");
  await info.scrollIntoViewIfNeeded();
  await info.hover();
  const note = page.getByTestId("crime-info-violent_crime_rate-note");
  await expect(note).toBeVisible();
  // move the pointer from the button INTO the note — the old
  // button-mouseleave close killed it in the 8px gap
  const box = (await note.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + 4, { steps: 6 });
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 4 });
  await expect(note).toBeVisible();
  const link = note.getByRole("link", { name: "See more details" });
  await expect(link).toBeVisible();
  await link.click();
  await expect(page).toHaveURL(/about-crime-data/);
});

test("Tab reaches the note's link from the button (item 3)", async ({ page }) => {
  await page.goto(CITY_URL);
  const info = page.getByTestId("crime-info-violent_crime_rate");
  await info.focus();
  const note = page.getByTestId("crime-info-violent_crime_rate-note");
  await expect(note).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(note.getByRole("link", { name: "See more details" })).toBeFocused();
  await expect(note).toBeVisible();
  // and tabbing on out of the note closes it
  await page.keyboard.press("Tab");
  await expect(note).toHaveCount(0);
});

test("Escape closes the popover and returns focus to the button (item 3)", async ({ page }) => {
  await page.goto(CITY_URL);
  const info = page.getByTestId("crime-info-violent_crime_rate");
  await info.focus();
  await expect(
    page.getByTestId("crime-info-violent_crime_rate-note")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(
    page.getByTestId("crime-info-violent_crime_rate-note")).toHaveCount(0);
  await expect(info).toBeFocused();
});

test("preferences follow the visitor; explicit parameters always win (item 2)", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
  // change something real: Cost of living -> A lot (writes the cookie)
  await page.getByRole("radiogroup", { name: "Cost of living importance" })
    .getByRole("radio", { name: "A lot" }).click();
  await expect(page).toHaveURL(/ic=a/);
  // the nav carries the query to every destination and back
  await page.getByRole("link", { name: "What we measure" }).click();
  await expect(page).toHaveURL(/what-we-measure\?.*ic=a/);
  await page.getByRole("link", { name: "Compare cities" }).click();
  await expect(page).toHaveURL(/compare\?.*ic=a/);
  await page.getByRole("link", { name: "Browse cities" }).click();
  await expect(page).toHaveURL(/\/\?.*ic=a/);
  await expect(
    page.getByRole("radiogroup", { name: "Cost of living importance" })
      .getByRole("radio", { name: "A lot" })).toHaveAttribute("aria-checked", "true");
  // a BARE url falls back to the cookie: the panel comes back as left
  await page.goto("/");
  await expect(
    page.getByRole("radiogroup", { name: "Cost of living importance" })
      .getByRole("radio", { name: "A lot" })).toHaveAttribute("aria-checked", "true");
  // explicit parameters always win over the cookie
  await page.goto("/?ic=n");
  await expect(
    page.getByRole("radiogroup", { name: "Cost of living importance" })
      .getByRole("radio", { name: "Not much" })).toHaveAttribute("aria-checked", "true");
});

test("a reproduction link is never overridden by a conflicting cookie (item 2 / gate 3)", async ({ page, context }) => {
  const res = await page.request.post("/api/rank", {
    data: {
      self: { sex: "male", age: 33 },
      seeking: { age: [26, 38], marital: ["never_married"] },
    },
  });
  expect(res.ok()).toBe(true);
  const body = await res.json();
  await context.addCookies([{
    name: "dsa_prefs",
    value: encodeURIComponent(
      "self_sex=female&self_age=30&age=28-40&marital=never,previously&ic=a"),
    url: "http://127.0.0.1:3100",
  }]);
  await page.goto(body.permalink);
  const rows = page.getByTestId("ranked-list").locator("li");
  await expect(rows.first()).toBeVisible();
  expect(await rows.first().getAttribute("data-cbsa")).toBe(body.ranked[0].cbsa);
  // the panel shows the TOKEN's search, not the cookie's
  await expect(page.getByTestId("my-age")).toHaveValue("33");
});

test("every compare difference equals the subtraction of the two displayed values (gate 5)", async ({ page }) => {
  await page.goto(`/compare/provo-utah/austin-texas${DEFAULTISH}`);
  const table = page.getByTestId("compare-table");
  await expect(table).toBeVisible();
  const rows = await table.locator("tr:has([data-diff-for])").evaluateAll((trs) =>
    trs.map((tr) => {
      const cells = [...tr.querySelectorAll("td")];
      const diffTd = tr.querySelector("[data-diff-for]")!;
      return {
        id: diffTd.getAttribute("data-diff-for")!,
        a: cells[0]?.textContent ?? "",
        b: cells[1]?.textContent ?? "",
        diff: diffTd.textContent?.trim() ?? "",
        color: getComputedStyle(diffTd).color,
      };
    }),
  );
  const firstNumber = (s: string): number => {
    const m = s.replace(/,/g, "").match(/-?\d+(\.\d+)?( million)?/);
    if (!m) return NaN;
    const v = parseFloat(m[0]);
    return / million/.test(m[0]) ? v * 1_000_000 : v;
  };
  expect(rows.length).toBeGreaterThanOrEqual(10);
  for (const r of rows) {
    const a = firstNumber(r.a);
    const b = firstNumber(r.b);
    const decimals = (r.diff.split(".")[1] ?? "").replace(/\D/g, "").length;
    const sign = r.diff.startsWith("−") ? -1 : 1;
    const shown = firstNumber(r.diff.replace(/[+−$]/g, "")) * sign;
    const want = a - b;
    expect(Math.abs(shown - want), `${r.id}: ${r.a} − ${r.b} -> ${r.diff}`)
      .toBeLessThanOrEqual(0.5 * 10 ** -decimals + 1e-9);
  }
  // rent carries $ after the sign (item 6.2); population stays grey
  const byId = Object.fromEntries(rows.map((r) => [r.id, r]));
  expect(byId.median_gross_rent.diff).toMatch(/^[+−]\$/);
  expect(byId.who_lives_here.color).toBe(RGB.grey);
  // the legend line explains the colours, from the registry (item 6.3)
  await expect(page.getByTestId("diff-legend")).toContainText(
    /Green means the difference favors Provo/);
});

test("either side missing gives an em dash (gate 5)", async ({ page }) => {
  // under the stress search both cities' pools suppress: rank, score and
  // pool differences must dash rather than invent a subtraction
  await page.goto(
    "/compare/provo-utah/austin-texas?self_sex=female&self_age=30&age=25-35&marital=never&edu=graduate&inc=250000&race=nhpi_nh");
  const table = page.getByTestId("compare-table");
  await expect(table).toBeVisible();
  for (const id of ["rank", "score", "pool"]) {
    await expect(table.locator(`[data-diff-for="${id}"]`)).toHaveText("—");
  }
});

test("stat pages: source line, header row, no band labels (items 9.2/9.4/9.5)", async ({ page }) => {
  await page.goto("/stats/median_gross_rent");
  const source = page.getByTestId("stat-source");
  await expect(source).toContainText(
    "Source: U.S. Census Bureau's American Community Survey 5-Year Data");
  await expect(source.getByRole("link")).toHaveAttribute(
    "href", "https://www.census.gov/programs-surveys/acs/");
  const header = page.getByTestId("stat-list-header");
  await expect(header).toContainText("City Name");
  await expect(header).toContainText("Rent");
  // the deleted standing intro is gone from every page that carried it
  await expect(page.locator("main")).not.toContainText(
    "Every city this site can rank");
  // no band label beside a city name — the ordering already says it
  const firstRow = page.getByTestId("stat-list").locator("li").first();
  await expect(firstRow).not.toContainText(/than most cities|About average/);
  // nice days carries its 1991–2020 through the source line (item 9.2)
  await page.goto("/stats/pleasant_days");
  await expect(page.getByTestId("stat-source")).toContainText("1991–2020");
});

test("the excluded-cities line and the compare landing speak the new copy", async ({ page }) => {
  await page.goto(
    "/?self_sex=female&self_age=32&age=30-40&marital=never&edu=graduate&inc=100000");
  await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
  await expect(page.getByTestId("excluded-note")).toContainText(
    /make a reliable estimate/);
  await expect(page.getByTestId("excluded-note")).toContainText(
    /Widen your search to see more cities/);
  await page.goto("/compare");
  await expect(page.locator("main")).toContainText(
    "View two cities side by side");
});

test("the slider sits with the importance controls as one group (item 4.5)", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
  const weighting = page.getByTestId("weighting");
  await expect(weighting.locator("input.svo")).toHaveCount(1);
  await expect(weighting.getByTestId("importance")).toBeVisible();
  // the slider comes immediately above "How much do these matter?"
  const sliderBox = (await weighting.locator("input.svo").boundingBox())!;
  const impBox = (await weighting.getByTestId("importance").boundingBox())!;
  expect(sliderBox.y).toBeLessThan(impBox.y);
  // and the race section sits above the whole weighting group
  const raceBox = (await page.getByTestId("race-panel").boundingBox())!;
  expect(raceBox.y).toBeLessThan(sliderBox.y);
});
