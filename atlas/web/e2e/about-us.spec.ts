import { expect, test } from "@playwright/test";
import { fetchMeta, photoOnDisk } from "./helpers";
import heroImage from "../src/data/hero.json";
import statImages from "../src/data/stat-images.json";
import cityImages from "../src/data/city-images.json";

/** Nathan's About us changes (after Phase 4e, 2026-10-06): no What we
 * measure or About crime data button at the top — the account links both
 * in its own words; the data citations collapse; the home page photograph's
 * credit sits in the collapsed photographs' list; and the account is his
 * copy, its sources table linking each source. Labels come from the
 * registry (read back through /v1/meta), never re-typed here. */

const HEADINGS = [
  "How are the numbers made?",
  "Where does the data come from?",
  "How is the count of matches calculated?",
  "How is compatibility calculated?",
  "How is the overall score calculated?",
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
  ["Political lean", null, "MIT Election Data and Science Lab", "https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/VOQCHQ"],
  ["Reported crime", "/about-crime-data", "FBI Crime Data Explorer", "https://cde.ucr.cjis.gov/"],
];

test("the top of About carries no buttons; the footer's Data sources opens Sources and credits", async ({ page, request }) => {
  const ps = (await fetchMeta(request)).policy_strings;
  expect(ps).not.toHaveProperty("about_measure_link");
  expect(ps).not.toHaveProperty("about_crime_link");
  await page.goto("/about");
  // Phase 5: Privacy and Terms moved to the footer every page carries
  await expect(page.getByTestId("about-links")).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "Footer" })
    .getByRole("link", { name: ps.footer_sources })).toHaveAttribute("href", "/about#sources-and-credits");
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
  // renamed by Nathan on 2026-10-07 (was "About us")
  await expect(page.locator("h1")).toHaveText("How it works");
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

test("the data sources are collapsed, the Census API notice folded in with them", async ({ page, request }) => {
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
  // Nathan (2026-10-06): the Census API notice folds into the collapsed
  // list — ADR 0012: it appears with the citations
  const notice = page.getByTestId("credits-notice");
  await expect(notice).toHaveCount(1);
  expect(await more.locator('[data-testid="credits-notice"]').count()).toBe(1);
  await expect(notice).toBeHidden();
  await more.locator("summary").click();
  await expect(list).toBeVisible();
  await expect(list.locator("li")).toHaveText(citations);
  await expect(notice).toBeVisible();
  await expect(notice).toHaveText(
    "This product uses the Census Bureau Data API but is not endorsed or certified by the Census Bureau.");
});

test("the photographs' list credits what the site shows, the cropped ones marked; the home photograph has left", async ({ page, request }) => {
  const ps = (await fetchMeta(request)).policy_strings;
  // Phase 5 (Nathan's decision 1): the home page has no photograph band,
  // so its credit left; the credits the page owes are every stat and city
  // photograph on disk (gitignored: a fresh checkout — CI's — owes none),
  // every city photograph marked cropped (after the Phase 5 report the
  // home page's cards and the city page's band crop them all)
  type Img = { file: string; license: string };
  const cities = Object.values(cityImages as unknown as Record<string, Img>)
    .filter((i) => photoOnDisk(`cities/${i.file}`));
  const files = [
    ...Object.values(statImages as unknown as Record<string, Img>)
      .filter((i) => photoOnDisk(`stats/${i.file}`)).map((i) => i.file),
    ...cities.map((i) => i.file),
  ];
  await page.goto("/about");
  await expect(page.getByTestId("sources-and-credits")).toBeVisible();
  await expect(page.locator(`[data-credit="${heroImage.file}"]`)).toHaveCount(0);
  const more = page.getByTestId("credits-photos-more");
  if (files.length === 0) {
    await expect(more).toHaveCount(0);
    await expect(page.locator("[data-credit]")).toHaveCount(0);
    return;
  }
  await expect(more).not.toHaveAttribute("open", /.*/);
  await expect(more.locator("summary")).toHaveText(
    ps.credits_photos_more.replace("{n}", files.length.toLocaleString("en-US")));
  expect(await more.locator("li[data-credit]").evaluateAll(
    (lis) => lis.map((li) => li.getAttribute("data-credit")))).toEqual(files);
  await more.locator("summary").click();
  for (const img of cities) {
    const li = more.locator(`[data-credit="${img.file}"]`);
    await expect(li).toContainText(`· ${ps.credits_cropped}`);
  }
});
