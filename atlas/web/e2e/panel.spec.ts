import { expect, test } from "@playwright/test";

/** Phase 5 (replacing Phase 2d items 1 + 2): from 1120px the search rail
 * sits beside the results, sticky — and, after the Phase 5 report
 * (Nathan), scrolls inside itself, no taller than the window, so its last
 * controls never wait for the page's end; below 1120px it lives in a sheet (phones) or a
 * drawer (tablets) opened by the sticky "Adjust your search" bar, which
 * appears once the hero's quick search has scrolled away. The slider
 * explanation is a real button that opens on hover AND focus AND tap and
 * closes on Escape and blur. */

for (const size of [{ w: 1440, h: 900 }, { w: 1280, h: 720 }]) {
  test(`the rail sticks beside the results and scrolls inside itself at ${size.w}×${size.h}`, async ({ page }) => {
    await page.setViewportSize({ width: size.w, height: size.h });
    await page.goto("/");
    await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
    const rail = page.getByTestId("rail");
    const style = await rail.evaluate((el) => {
      const cs = getComputedStyle(el);
      return { position: cs.position, overflowY: cs.overflowY, height: el.getBoundingClientRect().height };
    });
    expect(style.position).toBe("sticky");
    expect(style.overflowY).toBe("auto");
    expect(style.height).toBeLessThanOrEqual(size.h - 32);
    // open both groups: the rail grows taller than the window, and its
    // last control is reached by scrolling the RAIL, the page standing still
    await page.getByRole("button", { name: "Narrow it down", exact: true }).click();
    await page.getByRole("button", { name: "Sharpen compatibility", exact: true }).click();
    expect(await rail.evaluate((el) => el.scrollHeight > el.clientHeight)).toBe(true);
    const pageY = await page.evaluate(() => window.scrollY);
    const railBox = (await rail.boundingBox())!;
    await page.mouse.move(railBox.x + railBox.width / 2, railBox.y + railBox.height / 2);
    await page.mouse.wheel(0, 3000);
    await expect.poll(() => rail.evaluate((el) => el.scrollTop)).toBeGreaterThan(0);
    await expect(page.getByTestId("self-race")).toBeInViewport();
    expect(await page.evaluate(() => window.scrollY)).toBe(pageY);
  });
}

test("the rail stays pinned as the page scrolls, and its information box opens over the cards", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
  const rail = page.getByTestId("rail");
  // the slider's box reaches past the rail's edge, over the first card:
  // it is drawn on top (Nathan: "should not be covered by the card")
  await page.getByTestId("slider-info").hover();
  const note = page.getByTestId("slider-info-note");
  await expect(note).toBeVisible();
  const box = (await note.boundingBox())!;
  const railRight = (await rail.boundingBox())!.x + (await rail.boundingBox())!.width;
  expect(box.x + box.width).toBeGreaterThan(railRight);
  const onTop = await page.evaluate(([x, y]) =>
    !!document.elementFromPoint(x, y)?.closest('[data-testid="slider-info-note"]'),
  [box.x + box.width - 8, box.y + box.height / 2]);
  expect(onTop).toBe(true);
  await page.mouse.move(10, 10);

  // scrolling the page down leaves the rail pinned in view (the fixture's
  // list is short: scroll within the results, not past them)
  const results = (await page.getByTestId("ranked-list").boundingBox())!;
  await page.mouse.move(results.x + 40, 300);
  await page.mouse.wheel(0, 500);
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(400);
  const pinned = await rail.boundingBox();
  expect(pinned!.y).toBeGreaterThanOrEqual(0);
  expect(pinned!.y).toBeLessThan(40);
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
    // Phase 6 (F05): Show results lands on the results heading, focused
    await expect(page.getByTestId("list-heading")).toBeFocused();
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

test("the slider explanation opens on hover, Enter and tap (not on focus alone), closes on Escape and blur", async ({ page }) => {
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

  // focus alone no longer opens it (Phase 6, F17); Enter does
  await btn.focus();
  await page.waitForTimeout(150);
  await expect(note).toHaveCount(0);
  await page.keyboard.press("Enter");
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
