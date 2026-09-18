import { expect, test } from "@playwright/test";

/** Phase 2g's surfaces: the renamed rent feature and its redirect (gate
 * 5), the HUD source line with the intact "with utilities" wording, the
 * all-excluded screen's new body reading as a sentence at both widths
 * with a surviving route to How it works (gate 7), and the replaced
 * crime explainer (gate 8). */

const BELOW_BAR =
  "/?self_sex=female&self_age=30&age=25-35&marital=never&edu=graduate&inc=250000&race=nhpi_nh";

test("the old rent path redirects; the new id is everywhere (gate 5)", async ({ page }) => {
  const res = await page.goto("/stats/median_gross_rent");
  expect(res!.ok()).toBe(true);
  await expect(page).toHaveURL(/\/stats\/rent_1br$/);
  // the unit line's "with utilities" wording is intact — HUD's gross
  // rent includes tenant-paid utilities, so the sentence stays true
  await page.goto(
    "/city/provo-utah?self_sex=female&self_age=30&age=28-40&marital=never,previously");
  await expect(page.locator('[data-card="rent_1br"]')).toContainText(
    "median 1-bedroom monthly rent, with utilities");
});

test("the all-excluded body reads as a sentence at 1280 and 375 (gate 7)", async ({ page }) => {
  for (const width of [1280, 375]) {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
    await page.goto(BELOW_BAR);
    const narrow = page.getByTestId("narrow-state");
    await expect(narrow).toBeVisible();
    const text = (await narrow.textContent()) ?? "";
    expect(text, `at ${width}px`).toMatch(
      /Men \d+–\d+[^.]* is a very small group in any city\./);
    // the note box is gone; the nav still routes to the explainer
    await expect(narrow).not.toContainText(/The narrower the search/);
    await expect(
      page.getByRole("link", { name: "How it works" })).toBeVisible();
  }
});

test("the crime explainer is Nathan's rewrite (gate 8)", async ({ page }) => {
  await page.goto("/about-crime-data");
  const article = page.locator("article.prose-method");
  await expect(article).toBeVisible();
  await expect(page.locator("h1")).toHaveText("About the crime figures");
  const text = (await article.textContent()) ?? "";
  expect(text).toMatch(/Raw crime figures can be misleading/);
  expect(text).toMatch(/It is optional for police agencies to report/);
  expect(text).toMatch(/provided as context, but not used in the calculations/);
  expect(text).toMatch(/The reference year is shown with the figures/);
  // the two figure bullets keep their bold lead-ins
  expect(await article.locator("li strong").count()).toBeGreaterThanOrEqual(2);
});
