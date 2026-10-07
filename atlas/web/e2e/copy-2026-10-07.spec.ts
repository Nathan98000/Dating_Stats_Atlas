import { expect, test } from "@playwright/test";
import { fetchMeta, photoOnDisk } from "./helpers";
import statImages from "../src/data/stat-images.json";

/** Nathan's copy changes of 2026-10-07: the compatibility sentence on What
 * we measure, the crime explainer's sections, and the Privacy and Terms
 * pages in his words (each page renders its docs/*.md; the registry
 * sentence is read back through /v1/meta), and the everyday prices page's
 * new photograph. The About page's own changes — its name, the political
 * lean source, the overall score's heading — are in about-us.spec.ts. */

const COMPATIBILITY =
  "How closely the people who match your search resemble the people who actually pair with someone like you, on age, education, and background, where 100 is the US average";

test("What we measure carries the compatibility sentence in Nathan's new words", async ({ page, request }) => {
  const meta = await fetchMeta(request);
  expect(meta.pillars.match.definition).toBe(COMPATIBILITY);
  expect(meta.features.match_propensity.definition).toBe(COMPATIBILITY);
  await page.goto("/what-we-measure");
  const people = page.locator('[data-group="people"]');
  const text = ((await people.textContent()) ?? "").replace(/\s+/g, " ");
  expect(text).toContain(COMPATIBILITY);
  expect(text).not.toMatch(/if you include yours/);
});

test("the crime explainer reads in three sections, coverage folded into why cities aren't compared", async ({ page }) => {
  await page.goto("/about-crime-data");
  const article = page.locator("article.prose-method");
  await expect(article.getByRole("heading", { level: 2 })).toHaveText([
    "What the numbers are",
    "Why cities aren't compared on crime",
    "Where it comes from",
  ]);
  const text = ((await article.textContent()) ?? "").replace(/\s+/g, " ");
  expect(text).toMatch(/making cross-city comparisons potentially misleading\. It is optional for police agencies to report to the FBI\./);
  expect(text).toMatch(/based on the crimes in geographic regions covered by reporting agencies, not whole metros/);
  expect(text).not.toMatch(/Coverage is the share of a metro's people/);
});

test("Privacy is Nathan's 2026-10-07 copy, in its four sections", async ({ page }) => {
  await page.goto("/privacy");
  const article = page.locator("article.prose-method");
  await expect(article.locator("h1")).toHaveText("Privacy");
  await expect(article.getByRole("heading", { level: 2 })).toHaveText(
    ["Your search", "The cookie", "Our host", "No tracking"]);
  const text = ((await article.textContent()) ?? "").replace(/\s+/g, " ");
  expect(text).toMatch(/There is no account needed to use this site, we don't track you, and what you select stays in your browser\./);
  expect(text).toMatch(/One cookie, called dsa_prefs,/);
  expect(text).toMatch(/The server keeps no record of your visits, not your IP address, and not the pages you look at\./);
});

test("the terms carry the new date and Nathan's 2026-10-07 summary", async ({ page }) => {
  await page.goto("/terms");
  const article = page.locator("article.prose-method");
  const text = ((await article.textContent()) ?? "").replace(/\s+/g, " ");
  expect(text).toMatch(/Last updated: October 7, 2026/);
  expect(text).toMatch(/don't treat a figure as a fact about an individual/);
  expect(text).toMatch(/Estimates, not recommendations/);
  expect(text).toMatch(/Questions about these terms go to dating\.stats\.atlas@gmail\.com\./);
});

test("everyday prices shows Nathan's grocery photograph, credited in Sources and credits", async ({ page }) => {
  const img = (statImages as unknown as Record<string, { file: string; alt: string; author: string;
    license: string; source_url: string; title: string; cropped: boolean }>).everyday_prices;
  expect(img.source_url).toBe(
    "https://www.needpix.com/photo/885923/grocery-store-supermarket-vegetable-shop-tomato-fruit-store-market-groceries");
  expect(img.license).toBe("CC0");
  expect(img.cropped).toBe(false);
  await page.goto("/stats/everyday_prices");
  const shown = page.locator(`img[src="/stats/${img.file}"]`);
  if (!photoOnDisk(`stats/${img.file}`)) {
    // a checkout without the (gitignored) file, CI's: no file, no photo
    await expect(page.locator("h1")).toBeVisible();
    await expect(shown).toHaveCount(0);
    return;
  }
  await expect(shown).toBeVisible();
  await expect(shown).toHaveAttribute("alt", img.alt);
  expect(await page.locator("body").innerText()).not.toContain(img.author);
  await page.goto("/about");
  await page.getByTestId("credits-photos-more").locator("summary").click();
  const credit = page.locator(`[data-credit="${img.file}"]`);
  await expect(credit).toHaveCount(1);
  await expect(credit).toContainText(img.title);
  await expect(credit).toContainText(img.author);
  await expect(credit).toContainText("CC0");
  await expect(credit.getByRole("link", { name: "source" })).toHaveAttribute("href", img.source_url);
});
