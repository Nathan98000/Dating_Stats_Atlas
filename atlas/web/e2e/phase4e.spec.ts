import { expect, test } from "@playwright/test";
import { fetchMeta } from "./helpers";
import statPages from "../src/data/stat-pages.json";

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
    await expect(page.locator("header")).toBeVisible();
    await page.waitForLoadState("networkidle");
    expect(await page.locator("body").innerText(), path).not.toContain(note);
  }
});

test("the nav reads Home, Compare cities, About us", async ({ page }) => {
  await page.goto(`/${QS}`);
  const header = page.locator("header").first();
  // the brand link first, then the three destinations in order
  await expect(header.getByRole("link")).toHaveText(
    ["Dating Stats Atlas", "Home", "Compare cities", "About us"]);
  await expect(page.getByRole("link", { name: "Browse cities" })).toHaveCount(0);
  await page.getByRole("link", { name: "About us", exact: true }).click();
  await page.getByRole("link", { name: "Home", exact: true }).click();
  await expect(page).toHaveURL(/127\.0\.0\.1:3100\/\?/);
});
