import { expect, test } from "@playwright/test";

/** Phase 2d items 1 + 2 (gates 1 + 2): the panel follows the page and
 * scrolls inside itself — keyboard included — at both test viewports and
 * goes back to a normal block at phone width; the slider explanation is
 * a real button that opens on hover AND focus AND tap and closes on
 * Escape and blur. */

for (const size of [{ w: 1280, h: 720 }, { w: 1280, h: 900 }]) {
  test(`the panel sticks and scrolls inside itself at ${size.w}×${size.h}`, async ({ page }) => {
    await page.setViewportSize({ width: size.w, height: size.h });
    await page.goto("/");
    await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
    const panel = page.getByTestId("search-panel");
    const style = await panel.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { position: cs.position, overflowY: cs.overflowY,
               maxHeight: cs.maxHeight };
    });
    expect(style.position).toBe("sticky");
    expect(style.overflowY).toBe("auto");
    expect(style.maxHeight).not.toBe("none");

    // scrolling the PAGE far down leaves the panel pinned in view — the
    // page is never trapped by a panel taller than the viewport
    await page.mouse.wheel(0, 2500);
    await expect
      .poll(() => page.evaluate(() => window.scrollY))
      .toBeGreaterThan(1200);
    const box = await panel.boundingBox();
    expect(box!.y).toBeGreaterThanOrEqual(0);
    expect(box!.y).toBeLessThan(40);

    // the scroll container is keyboard-reachable and scrollable: focus
    // it and page through it without moving the page
    await panel.focus();
    const pageYBefore = await page.evaluate(() => window.scrollY);
    const innerBefore = await panel.evaluate((el) => el.scrollTop);
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("ArrowDown");
    if (size.h === 720) {
      // at 720 the panel overflows, so arrows must scroll ITS content
      await expect.poll(() => panel.evaluate((el) => el.scrollTop))
        .toBeGreaterThan(innerBefore);
    }
    expect(await page.evaluate(() => window.scrollY)).toBe(pageYBefore);

    // every control stays reachable inside the panel's own scroll — the
    // last importance row can always be brought into view
    const lastRow = page.getByRole("radiogroup", { name: "Weather importance" });
    await lastRow.getByRole("radio", { name: "Some" }).focus();
    await expect(lastRow).toBeInViewport();
  });
}

test("at phone width the panel is a normal block above the results", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
  const panel = page.getByTestId("search-panel");
  const style = await panel.evaluate((el) => getComputedStyle(el).position);
  expect(style).toBe("static");
  const panelBox = await panel.boundingBox();
  const listBox = await page.getByTestId("ranked-list").boundingBox();
  expect(panelBox!.y).toBeLessThan(listBox!.y);
  // the chips bar brings Change search back once the panel scrolls away
  await page.mouse.wheel(0, panelBox!.height + 800);
  await expect(page.getByTestId("chips-bar")).toBeVisible();
  await expect(page.getByRole("button", { name: "Change search" })).toBeVisible();
});

test("the slider explanation opens on hover, focus and tap, closes on Escape and blur", async ({ page }) => {
  await page.goto("/");
  const btn = page.getByTestId("slider-info");
  const note = page.getByTestId("slider-info-note");
  await expect(btn).toBeVisible();
  await expect(btn).toHaveAttribute("aria-expanded", "false");
  await expect(note).toHaveCount(0);

  // hover — the Phase 2f slider copy, verbatim (item 4.4)
  await btn.hover();
  await expect(note).toBeVisible();
  await expect(note).toContainText(/size favors larger cities/);
  await expect(note).toContainText(/balance favors cities with a larger share/);
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
