import { expect, test } from "@playwright/test";
import { fetchMeta, photoOnDisk } from "./helpers";
import statPages from "../src/data/stat-pages.json";
import statImages from "../src/data/stat-images.json";

/** Phase 4e (Nathan's five changes): the walkability page's note, the nav's
 * "Home", the two new stat-page photos and the new nice-day definition.
 * Every string is the registry's (read back through /v1/meta or the stat
 * pages' build JSON), never re-typed here. */

const QS = "?sex=male&self_age=30&age=28-40&marital=never,previously";
const PAGES = statPages as unknown as { order: string[]; pages: Record<string, { note?: string }> };

test("the walkability note sits under the definition on its stat page, and nowhere else", async ({ page, request }) => {
  const meta = await fetchMeta(request);
  const walk = meta.features.resident_walkability_index;
  const note = walk.stat_page_note!;
  expect(note).toBeTruthy();
  // the definition used everywhere else is untouched
  expect(walk.definition).toBe("A walkability index of where the city's residents live, from 1 to 20.");
  expect(PAGES.pages.resident_walkability_index.note).toBe(note);

  await page.goto("/stats/resident_walkability_index");
  await expect(page.getByText(walk.definition, { exact: true })).toBeVisible();
  await expect(page.getByTestId("stat-page-note")).toHaveText(note);
  // it follows the definition
  const order = await page.locator("main p").evaluateAll((ps) => ps.map((p) => p.textContent));
  expect(order.indexOf(note)).toBe(order.indexOf(walk.definition) + 1);

  // no other stat page carries a note, and no other page shows this one
  for (const fid of PAGES.order.filter((f) => f !== "resident_walkability_index")) {
    expect(PAGES.pages[fid].note, fid).toBeUndefined();
    await page.goto(`/stats/${fid}`);
    await expect(page.getByTestId("stat-page-note"), fid).toHaveCount(0);
  }
  for (const path of ["/", "/city/pittsburgh-pennsylvania", "/compare?cities=pittsburgh-pennsylvania",
                      "/what-we-measure", "/about"]) {
    await page.goto(`${path}${path.includes("?") ? "&" : "?"}${QS.slice(1)}`);
    await expect(page.locator("header").first()).toBeVisible();
    await page.waitForLoadState("networkidle");
    expect(await page.locator("body").innerText(), path).not.toContain(note);
  }
});

test("the nav reads Rankings, Compare, How it works", async ({ page }) => {
  await page.goto(`/${QS}`);
  const header = page.locator("header").first();
  // the brand link first, then the three destinations in order (Phase 5,
  // Nathan's decision 2: Rankings, Compare, How it works)
  await expect(header.getByRole("link")).toHaveText(
    ["Dating Stats Atlas", "Rankings", "Compare", "How it works"]);
  await expect(header.getByRole("link", { name: "Rankings" })).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("link", { name: "Browse cities" })).toHaveCount(0);
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "How it works", exact: true }).click();
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Rankings", exact: true }).click();
  await expect(page).toHaveURL(/127\.0\.0\.1:3100\/\?/);
});

type Img = { file: string; alt: string | null; author: string | null; title: string; cropped: boolean };
const IMAGES = statImages as unknown as Record<string, Img>;

for (const fid of ["who_lives_here", "political_lean"]) {
  test(`${fid}'s new photo renders on its stat page, credited only in Sources and credits`, async ({ page }) => {
    const img = IMAGES[fid];
    expect(img, fid).toBeTruthy();
    expect(img.cropped).toBe(false);       // the stat page scales, never crops
    await page.goto(`/stats/${fid}`);
    const shown = page.locator(`img[src="/stats/${img.file}"]`);
    if (!photoOnDisk(`stats/${img.file}`)) {
      // a checkout without the (gitignored) file, CI's: no file, no photo,
      // and no credit for it
      await expect(page.locator("h1")).toBeVisible();
      await expect(shown).toHaveCount(0);
      await page.goto("/about");
      await expect(page.getByTestId("sources-and-credits")).toBeVisible();
      await expect(page.locator(`[data-credit="${img.file}"]`)).toHaveCount(0);
      return;
    }
    await expect(shown).toBeVisible();
    await expect(shown).toHaveAttribute("alt", img.alt!);
    expect(await shown.evaluate((el: HTMLImageElement) => el.naturalWidth)).toBeGreaterThan(0);
    // no credit on the page itself: no caption, no author, no Commons title
    await expect(page.locator("figure figcaption")).toHaveCount(0);
    const body = await page.locator("body").innerText();
    expect(body).not.toContain(img.author!);
    expect(body).not.toContain(img.title);
    // the credit is in About us, Sources and credits, once
    await page.goto("/about");
    const credit = page.locator(`[data-credit="${img.file}"]`);
    await expect(credit).toHaveCount(1);
    await page.getByTestId("credits-photos-more").locator("summary").click();
    await expect(credit).toContainText(img.author!);
    // the stat page shows it uncropped; since Phase 6 (ADR 0012 amended) its
    // 1200x630 link preview is a crop, so once that exists the credit says so
    if (photoOnDisk(`stats/og/${fid}.jpg`)) await expect(credit).toContainText("cropped");
    else await expect(credit).not.toContainText("cropped");
    await expect(credit.getByRole("link", { name: "source" })).toHaveAttribute("href", /^https:\/\/commons\.wikimedia\.org\//);
  });
}

test("nice days carries the new definition, and its unit line stays", async ({ page, request }) => {
  const meta = await fetchMeta(request);
  const f = meta.features.pleasant_days;
  expect(f.definition).toBe(
    "Days a year that average between 55 and 75°F, stay below 85°F and above 45°F, and have no more than a light shower and no snow");
  expect(f.unit).toBe("days that are mild and dry enough to be outside");
  await page.goto("/stats/pleasant_days");
  await expect(page.getByText(f.definition, { exact: true })).toBeVisible();
  await page.goto("/what-we-measure");
  await expect(page.getByText(f.definition)).toBeVisible();
  // the old thresholds are stated nowhere on these pages
  for (const path of ["/stats/pleasant_days", "/what-we-measure", "/about"]) {
    await page.goto(path);
    const body = await page.locator("body").innerText();
    expect(body, path).not.toMatch(/55 and 85|below 40°F|dip below/);
  }
});
