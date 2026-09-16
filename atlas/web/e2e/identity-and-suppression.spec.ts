import { expect, test } from "@playwright/test";

/** §10.4 counterweight, suppression visibility (gate 3), the few-metros
 * notice, and the suppressed metro page's explicit state. */

const RACE_QUERY =
  "/?self_sex=female&self_age=29&age=28-38&marital=never,previously&race=black_nh";
const BELOW_BAR =
  "/?self_sex=female&self_age=30&age=25-35&marital=never&edu=graduate&inc=250000&race=nhpi_nh";

test("a race filter renders the counterweight beside the pool", async ({ page }) => {
  await page.goto(RACE_QUERY);
  const rows = page.getByTestId("ranked-list").locator("li");
  await expect(rows.first()).toBeVisible();
  const n = await rows.count();
  let withValue = 0;
  for (let i = 0; i < n; i++) {
    const text = (await rows.nth(i).textContent()) ?? "";
    // every ranked row carries the counterweight: a measured rate with its
    // margin, or the explicit suppression note — never silence, never "0%"
    const hasValue = /partnered outside their group\s*±[\d.]+pp/.test(text);
    const hasNote = /pairing rate:/.test(text);
    expect(hasValue || hasNote, `row ${i} carries the counterweight`).toBe(true);
    if (hasValue) withValue++;
    expect(text).not.toMatch(/\b0\.0%\s*partnered/);
  }
  expect(withValue).toBeGreaterThan(0);
});

test("identity controls are off by default, in a secondary group", async ({ page }) => {
  await page.goto("/");
  const identity = page.getByTestId("identity-controls");
  expect(await identity.getAttribute("open")).toBeNull();
  await identity.locator("summary").click(); // open to inspect the checkboxes
  const boxes = identity.locator("input[type=checkbox]");
  for (let i = 0; i < (await boxes.count()); i++) {
    await expect(boxes.nth(i)).not.toBeChecked();
  }
  // religion is absent entirely — not a greyed tease, not a coming-soon note
  await expect(page.getByText(/religion/i)).toHaveCount(0);
});

test("a suppressing query shows footer counts with reasons and the notice", async ({ page }) => {
  await page.goto(BELOW_BAR);
  const footer = page.getByTestId("suppression-footer");
  await expect(footer).toBeVisible();
  await expect(footer).toContainText(/metros are suppressed/);
  // each count carries its reason string verbatim (on the 12-metro fixture
  // this stress query empties every pool)
  await expect(footer).toContainText(
    /No one in this sample matches\.|Too few people in this sample to estimate\./,
  );
  await expect(footer).toContainText("How suppression is decided");
  // "0 metros shown but not ranked" never renders (ADR 0002)
  await expect(footer).not.toContainText(/0 metros are shown/);
  await expect(footer).not.toContainText(/shown with its margin/);
  // the fixture ranks fewer than 40 here, so the §5.2 notice fires
  await expect(page.getByTestId("few-metros-notice")).toBeVisible();
});

test("a suppressed metro's page renders its explicit state", async ({ page }) => {
  await page.goto(`/metro/39340${BELOW_BAR.slice(1)}`);
  const state = page.getByTestId("suppressed-state");
  await expect(state).toBeVisible();
  await expect(state).toContainText("Not enough sample to rank");
  await expect(state).toContainText(/effective respondents/);
  // the objective profile still stands below it
  await expect(page.locator("#objective")).toContainText("The place itself");
  await expect(page.getByTestId("crime-context")).toContainText(
    "never part of any score",
  );
  // no pool figure leaks for a suppressed metro
  await expect(state).not.toContainText(/margin at least/);
});

test("provenance is one click from any number (gate 2)", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Every stat" }).first().click();
  const src = page.getByRole("link", { name: /^source/ }).first();
  await expect(src).toBeVisible();
  await src.click();
  await expect(page).toHaveURL(/\/methodology#f-/);
  await expect(page.locator("h2", { hasText: "Provenance register" })).toBeVisible();
  await expect(page.locator("#f-pool_size")).toContainText("census_acs");
});
