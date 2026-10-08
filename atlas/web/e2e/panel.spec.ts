import { expect, test } from "@playwright/test";

/** Phase 5 (replacing Phase 2d items 1 + 2): from 1120px the search rail
 * sits beside the results, sticky, and never scrolls inside itself — it
 * fits a 1440×900 screen; below 1120px it lives in a sheet (phones) or a
 * drawer (tablets) opened by the sticky "Adjust your search" bar, which
 * appears once the hero's quick search has scrolled away. The slider
 * explanation is a real button that opens on hover AND focus AND tap and
 * closes on Escape and blur. */

test("the rail sticks beside the results and fits 1440×900 without its own scroll", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
  const rail = page.getByTestId("rail");
  const style = await rail.evaluate((el) => {
    const cs = getComputedStyle(el);
    return { position: cs.position, overflowY: cs.overflowY,
             fits: el.scrollHeight === el.clientHeight, height: el.getBoundingClientRect().height };
  });
  expect(style.position).toBe("sticky");
  expect(style.overflowY).toBe("visible");
  expect(style.fits).toBe(true);
  expect(style.height).toBeLessThanOrEqual(900 - 16);

  // scrolling the page down leaves the rail pinned in view (the fixture's
  // list is short: scroll within the results, not past them)
  await page.mouse.wheel(0, 500);
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(400);
  const box = await rail.boundingBox();
  expect(box!.y).toBeGreaterThanOrEqual(0);
  expect(box!.y).toBeLessThan(40);
  await expect(page.getByRole("radiogroup", { name: "Weather importance" })).toBeInViewport();
});

for (const size of [{ w: 390, h: 844, name: "sheet" }, { w: 1024, h: 768, name: "drawer" }]) {
  test(`below 1120px the search lives in a ${size.name}, opened from the sticky bar`, async ({ page }) => {
    await page.setViewportSize({ width: size.w, height: size.h });
    await page.goto("/");
    await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
    await expect(page.getByTestId("rail")).toHaveCount(0);
    const bar = page.getByTestId("bottom-bar");
    await expect(bar).toBeHidden();
    await page.mouse.wheel(0, 1600);
    await expect(bar).toBeVisible();
    const adjust = bar.getByRole("button", { name: "Adjust your search" });
    await adjust.click();
    const sheet = page.getByRole("dialog", { name: "Adjust your search" });
    await expect(sheet).toBeVisible();
    await expect(sheet.getByRole("radiogroup", { name: "Cost of living importance" })).toBeVisible();
    // the page behind does not scroll
    expect(await page.evaluate(() => getComputedStyle(document.documentElement).overflow)).toBe("hidden");
    // a change applies live, and Show results closes the sheet
    await sheet.getByRole("radiogroup", { name: "Cost of living importance" })
      .getByRole("radio", { name: "A lot" }).click();
    await expect(page).toHaveURL(/ic=a/);
    await sheet.getByRole("button", { name: "Show results" }).click();
    await expect(sheet).toBeHidden();
    await expect(adjust).toBeFocused();
  });
}

test("the sheet traps focus, closes on Escape and returns focus", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
  await page.mouse.wheel(0, 1600);
  const adjust = page.getByTestId("bottom-bar").getByRole("button", { name: "Adjust your search" });
  await adjust.click();
  const sheet = page.getByRole("dialog", { name: "Adjust your search" });
  await expect(sheet).toBeVisible();
  for (let i = 0; i < 40; i++) {
    await page.keyboard.press("Tab");
    const inside = await page.evaluate(() =>
      !!document.activeElement?.closest("dialog[open]") || document.activeElement === document.body);
    expect(inside, `tab ${i} stays in the sheet`).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(sheet).toBeHidden();
  await expect(adjust).toBeFocused();
  await expect.poll(() => page.evaluate(() => getComputedStyle(document.documentElement).overflow))
    .not.toBe("hidden");
});

test("the slider explanation opens on hover, focus and tap, closes on Escape and blur", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const btn = page.getByTestId("slider-info");
  const note = page.getByTestId("slider-info-note");
  await expect(btn).toBeVisible();
  await expect(btn).toHaveAttribute("aria-expanded", "false");
  await expect(note).toHaveCount(0);

  // hover — Nathan's slider copy (ADR 0009; rewritten in Phase 4b, and
  // held to the registry string exactly in phase4b.spec.ts)
  await btn.hover();
  await expect(note).toBeVisible();
  await expect(note).toContainText(/size favors larger cities/);
  await expect(note).toContainText(/compatibility favors cities with people who match your search more closely/);
  await page.mouse.move(10, 10);
  await expect(note).toHaveCount(0);

  // focus
  await btn.focus();
  await expect(note).toBeVisible();
  await expect(btn).toHaveAttribute("aria-expanded", "true");
  await expect(btn).toHaveAttribute("aria-describedby", /.+/);

  // Escape closes without losing focus
  await page.keyboard.press("Escape");
  await expect(note).toHaveCount(0);
  await expect(btn).toBeFocused();

  // tap/click toggles
  await btn.click();
  await expect(note).toBeVisible();

  // blur closes
  await page.keyboard.press("Tab");
  await expect(note).toHaveCount(0);
});
