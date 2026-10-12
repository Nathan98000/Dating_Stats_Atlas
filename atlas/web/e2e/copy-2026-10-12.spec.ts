import { expect, test } from "@playwright/test";

/** Nathan's changes of 2026-10-12: below 1120px the sticky bar reads
 * "Refine your search" (the sheet it opens too), and it shows as soon as
 * the page scrolls down, while the quick search (sex and age) is still on
 * screen, so a phone learns early that the search goes further; back at the
 * very top it hides again. */
for (const size of [{ w: 390, h: 844, name: "phone" }, { w: 1024, h: 768, name: "tablet" }]) {
  test(`${size.name}: the bar reads Refine your search and shows on the first scroll`, async ({ page }) => {
    await page.setViewportSize({ width: size.w, height: size.h });
    await page.goto("/");
    await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
    const bar = page.getByTestId("bottom-bar");
    await expect(bar).toBeHidden();
    await page.mouse.wheel(0, 60);
    await expect(bar).toBeVisible();
    // earlier than before: the quick search's first control is still in view
    await expect(page.getByTestId("self-sex")).toBeInViewport();
    const refine = bar.getByRole("button", { name: "Refine your search" });
    await expect(refine).toBeVisible();
    await refine.click();
    const sheet = page.getByRole("dialog", { name: "Refine your search" });
    await expect(sheet).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(sheet).toBeHidden();
    // back at the very top, the first screen is the hero's again
    await page.evaluate(() => window.scrollTo(0, 0));
    await expect(bar).toBeHidden();
    await expect(page.getByText("Adjust your search")).toHaveCount(0);
  });
}

/** The same day: the count line drops "each scored out of 100", and the
 * "Results updated" line folds away after six seconds, leaving no gap (it
 * used to keep its empty slot). */
test("the count line ends at 'ranked for your search'; the update line leaves no gap when it goes", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
  const count = page.getByTestId("results-count");
  await expect(count).toHaveText(/^\d[\d,]* metro areas ranked for your search$/);
  const header = count.locator("..");
  const before = (await header.boundingBox())!.height;
  await page.getByRole("radiogroup", { name: "Cost of living importance" }).getByRole("radio", { name: "A lot" }).click();
  const notice = page.getByTestId("results-notice");
  await expect(notice).toBeVisible();
  expect((await header.boundingBox())!.height).toBeGreaterThan(before);
  await expect(notice).toHaveCount(0, { timeout: 9000 });
  expect((await header.boundingBox())!.height).toBe(before);
});
