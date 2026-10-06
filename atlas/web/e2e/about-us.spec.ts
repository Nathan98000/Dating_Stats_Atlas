import { expect, test } from "@playwright/test";
import { fetchMeta } from "./helpers";
import heroImage from "../src/data/hero.json";

/** Nathan's About us changes (after Phase 4e, 2026-10-06): no What we
 * measure or About crime data button at the top — the account links both
 * in its own words; the data citations collapse; the home page photograph's
 * credit sits in the collapsed photographs' list; and the account is his
 * copy, its sources table linking each source. Labels come from the
 * registry (read back through /v1/meta), never re-typed here. */

const HEADINGS = [
  "How are the numbers made?",
  "Where does the data come from?",
  "How is count of matches calculated?",
  "How is compatibility calculated?",
  "How does the score work?",
  "Which cities are included?",
  "Every measure, every city",
];

// the sources table as Nathan wrote it: [stat, its link or null, source, source link]
const SOURCES: [string, string | null, string, string][] = [
  ["Rent", null, "HUD 50th percentile rent estimates, FY2027", "https://www.huduser.gov/portal/datasets/50per.html"],
  ["Everyday prices", null, "Bureau of Economic Analysis price levels", "https://www.bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area"],
  ["Places to go out", null, "Census Bureau business data", "https://www.census.gov/programs-surveys/cbp.html"],
  ["Getting around on foot", null, "EPA's national walkability index", "/stats/resident_walkability_index"],
  ["Nice days a year", null, "NOAA daily weather-station records, 1991–2020", "https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily"],
  ["Students", null, "Federal education data (IPEDS)", "https://nces.ed.gov/ipeds/use-the-data"],
  ["Political lean", null, "MIT Election Data and Science Lab data", "https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/VOQCHQ"],
  ["Reported crime", "/about-crime-data", "FBI Crime Data Explorer", "https://cde.ucr.cjis.gov/"],
];

test("the top of About us links only Privacy and the terms of use", async ({ page, request }) => {
  const ps = (await fetchMeta(request)).policy_strings;
  expect(ps).not.toHaveProperty("about_measure_link");
  expect(ps).not.toHaveProperty("about_crime_link");
  await page.goto("/about");
  await expect(page.getByTestId("about-links").getByRole("link")).toHaveText(
    [ps.about_privacy_link, ps.about_terms_link]);
  await expect(page.getByTestId("about-measure-link")).toHaveCount(0);
  // the two pages are still reached from the account itself
  const article = page.locator("article.prose-method");
  await expect(article.getByRole("link", { name: "What we measure", exact: true }))
    .toHaveAttribute("href", "/what-we-measure");
  await expect(article.getByRole("link", { name: "Reported crime", exact: true }))
    .toHaveAttribute("href", "/about-crime-data");
});

test("the account is Nathan's copy: its sections in order, the sources table linked as he wrote it", async ({ page }) => {
  await page.goto("/about");
  const article = page.locator("article.prose-method");
  await expect(article.getByRole("heading", { level: 2 })).toHaveText(HEADINGS);
  const rows = article.locator("table tbody tr");
  await expect(rows).toHaveCount(SOURCES.length);
  for (const [i, [stat, statHref, source, sourceHref]] of SOURCES.entries()) {
    const cells = rows.nth(i).locator("td");
    await expect(cells.nth(0)).toHaveText(stat);
    const statLink = cells.nth(0).getByRole("link");
    if (statHref) await expect(statLink).toHaveAttribute("href", statHref);
    else await expect(statLink).toHaveCount(0);
    await expect(cells.nth(1)).toHaveText(source);
    await expect(cells.nth(1).getByRole("link")).toHaveAttribute("href", sourceHref);
  }
  // no link points at a development server
  const hrefs = await article.locator("a[href]").evaluateAll((as) => as.map((a) => a.getAttribute("href")));
  expect(hrefs.filter((h) => /localhost|127\.0\.0\.1/.test(h ?? ""))).toEqual([]);
});

test("Reported crime in the sources table opens About crime data", async ({ page }) => {
  await page.goto("/about");
  await page.locator("article.prose-method table")
    .getByRole("link", { name: "Reported crime", exact: true }).click();
  await expect(page).toHaveURL(/\/about-crime-data$/);
});

test("the data sources are collapsed, with the Census API notice in view beside them", async ({ page, request }) => {
  const meta = await fetchMeta(request);
  const ps = meta.policy_strings;
  const citations = [...new Set(Object.values(meta.licenses).flatMap((l) => l.citations ?? []))];
  expect(citations.length).toBeGreaterThan(0);
  await page.goto("/about");
  const more = page.getByTestId("credits-data-more");
  await expect(more).not.toHaveAttribute("open", /.*/);
  await expect(more.locator("summary")).toHaveText(
    ps.credits_data_more.replace("{n}", citations.length.toLocaleString("en-US")));
  const list = page.getByTestId("credits-data");
  await expect(list).toBeHidden();
  // ADR 0012: the Census API notice appears with the citations — in view
  await expect(page.getByTestId("credits-notice").first()).toBeVisible();
  await expect(page.getByTestId("credits-notice").first())
    .toHaveText(/This product uses the Census Bureau Data API but is not endorsed or certified by the Census Bureau\./);
  await more.locator("summary").click();
  await expect(list).toBeVisible();
  await expect(list.locator("li")).toHaveText(citations);
});

test("the home page photograph is credited inside the collapsed photographs' list, cropped", async ({ page, request }) => {
  const ps = (await fetchMeta(request)).policy_strings;
  await page.goto("/about");
  const more = page.getByTestId("credits-photos-more");
  await expect(more).not.toHaveAttribute("open", /.*/);
  const hero = more.locator(`[data-credit="${heroImage.file}"]`);
  await expect(hero).toHaveCount(1);
  await expect(hero).toBeHidden();
  const n = await more.locator("li[data-credit]").count();
  await expect(more.locator("summary")).toHaveText(
    ps.credits_photos_more.replace("{n}", n.toLocaleString("en-US")));
  // no credit sits outside the collapsed list
  await expect(page.locator("[data-credit]")).toHaveCount(n);
  await more.locator("summary").click();
  await expect(hero).toBeVisible();
  await expect(hero).toContainText(heroImage.title);
  await expect(hero).toContainText(heroImage.author);
  await expect(hero).toContainText(ps.credits_cropped);
  await expect(hero.getByRole("link", { name: ps.credits_source }))
    .toHaveAttribute("href", heroImage.source_url);
});

test("the home page shows the new photograph with its alt text", async ({ page }) => {
  await page.goto("/");
  const photo = page.getByTestId("hero-photo");
  test.skip(!(await photo.count()), "the hero file is gitignored and absent here");
  await expect(photo.locator("img")).toHaveAttribute("alt", heroImage.alt);
  expect(heroImage.source_url).toBe(
    "https://commons.wikimedia.org/wiki/File:Crew_2016-01-10_(Unsplash_xCmvrpzctaQ).jpg");
  expect(heroImage.license).toBe("CC0");
});
