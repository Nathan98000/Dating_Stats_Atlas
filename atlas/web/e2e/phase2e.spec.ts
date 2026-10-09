import { readdirSync, readFileSync } from "fs";
import { openRailGroup } from "./helpers";
import path from "path";
import { expect, test } from "@playwright/test";

/** Phase 2e's surfaces: both-ways stat sorting without renumbering plus
 * the distribution strip (gate 1), the real map with state borders and
 * no mapping library in the bundle (gate 3), photographs with rendered
 * attribution (gate 4), the shared search fix on the real UI (gate 5),
 * eight equal race groups end to end (gate 7), the typed age field, and
 * the What we measure page. */

const CITY_URL =
  "/city/provo-utah?sex=male&self_age=30&age=28-40&marital=never,previously";

test("stat pages sort both ways without renumbering, strip renders", async ({ page }) => {
  await page.goto("/stats/rent_1br");
  await expect(page.getByTestId("stat-strip")).toBeVisible();
  const rows = page.getByTestId("stat-list").locator("li");
  const first = await rows.first().getAttribute("data-pos");
  const last = await rows.last().getAttribute("data-pos");
  expect(first).toBe("1"); // cheapest first: the registry's good end
  await page.getByTestId("stat-sort")
    .getByRole("radio", { name: "Highest first" }).click();
  // the SAME numbers in reverse — the priciest city keeps its earned
  // position number, it does not become #1
  await expect(rows.first()).toHaveAttribute("data-pos", last!);
  await expect(rows.last()).toHaveAttribute("data-pos", "1");
  // reversal is keyboard operable
  await page.getByTestId("stat-sort")
    .getByRole("radio", { name: "Lowest first" }).focus();
  await page.keyboard.press("Enter");
  await expect(rows.first()).toHaveAttribute("data-pos", "1");
  // the rent-stabilisation caution was DELETED in Phase 2g item 1.5:
  // HUD's measure trims subsidised units and adjusts to recent movers
  await expect(page.getByTestId("stat-note")).toHaveCount(0);
});

test("the locator is a real map: state borders, home state filled, dot placed", async ({ page, request }) => {
  await page.goto(CITY_URL);
  const map = page.getByTestId("locator-map");
  await expect(map).toBeVisible();
  // Phase 6 (F32): an image of the static /map/<cbsa>.svg, over simplified
  // outlines (50 states; the District is a speck at this scale)
  const src = await map.getAttribute("src");
  expect(src).toMatch(/^\/map\/\d+\.svg$/);
  const svg = await (await request.get(src!)).text();
  expect((svg.match(/<path /g) ?? []).length).toBeGreaterThanOrEqual(50);
  expect((svg.match(/fill="#F7E9EE"/g) ?? []).length).toBe(1);
  expect((svg.match(/<circle /g) ?? []).length).toBe(1);
  expect(svg.length).toBeLessThan(14_000);
});

test("no mapping library reaches the browser bundle", async () => {
  // the projection ran at build time; the client chunks must not carry
  // d3-geo (gate 3)
  const dist = process.env.NEXT_DIST_DIR ?? ".next-e2e";
  const chunkDir = path.resolve(dist, "static", "chunks");
  const offenders: string[] = [];
  const walk = (dir: string) => {
    for (const f of readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, f.name);
      if (f.isDirectory()) walk(p);
      else if (f.name.endsWith(".js")) {
        const src = readFileSync(p, "utf-8");
        if (/geoAlbersUsa|d3-geo/.test(src)) offenders.push(f.name);
      }
    }
  };
  walk(chunkDir);
  expect(offenders).toEqual([]);
});

test("a photographed city shows its photo, credited in About us; others fall back to artwork", async ({ page }) => {
  await page.goto(CITY_URL);
  const photo = page.getByTestId("city-photo");
  const art = page.getByTestId("city-art");
  if (await photo.count()) {
    // m4.0.0 (Nathan's decision 8): no credit line under the photo — its
    // credit, with a licence-deed link and a source link, is in About us,
    // Sources and credits; real alt text (never "photo of X")
    await expect(photo.locator("figcaption")).toHaveCount(0);
    const file = ((await photo.locator("img").getAttribute("src")) ?? "").split("/").pop()!;
    const alt = await photo.locator("img").getAttribute("alt");
    expect(alt ?? "").not.toMatch(/^photo of/i);
    await page.goto("/about");
    const credit = page.locator(`[data-credit="${file}"]`);
    await expect(credit).toHaveCount(1);
    // the city and stat photographs sit in the collapsible list
    await page.getByTestId("credits-photos-more").locator("summary").click();
    await expect(credit.getByRole("link", { name: "source" })).toHaveAttribute("href", /^https:\/\//);
  } else {
    await expect(art).toBeVisible();
    await expect(art).toHaveAttribute("aria-hidden", "true");
  }
});

test('the compare picker finds New York for "new york" (the item-5 bug)', async ({ page }) => {
  await page.goto("/compare");
  await page.getByLabel("First city").fill("new york");
  const options = page.getByRole("option");
  await expect(options.first()).toBeVisible();
  const texts = await options.allTextContents();
  expect(texts.slice(0, 3).join(" | ")).toMatch(/New York, New York/);
  // and the header search agrees, from the same implementation
  await page.getByLabel("Find a city").locator("visible=true").fill("new york");
  const headerOpts = page.locator("#city-search-results").getByRole("option");
  await expect(headerOpts.first()).toContainText("New York, New York");
});

test("eight equal race groups in the panel, the pair selectable alone", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
  await openRailGroup(page, "Narrow it down");
  const panel = page.getByTestId("race-panel");
  const boxes = panel.locator("input.check");
  await expect(boxes).toHaveCount(8);
  await expect(panel).toContainText("Two or more races");
  await expect(panel).toContainText("Another race");
  // untick the six other groups, leaving ONLY the formerly
  // always-counted pair: an ordinary filter now
  const others = ["Hispanic", "White", "Black", "Asian", "Native American",
                  "Pacific Islander"];
  for (const label of others) {
    await panel.getByText(label, { exact: true }).click();
  }
  await expect.poll(() => page.url()).toMatch(/race=/);
  const url = new URL(page.url());
  const sel = (url.searchParams.get("race") ?? "").split(",").sort();
  expect(sel).toEqual(["other_nh", "two_or_more_nh"]);
});

test("My age accepts typed input, validates on blur", async ({ page }) => {
  await page.goto("/");
  const field = page.getByTestId("my-age");
  await field.click();
  await field.fill("");
  await field.pressSequentially("34");
  await expect(field).toHaveValue("34"); // no per-keystroke clamping
  await page.keyboard.press("Tab");
  await expect.poll(() => page.url()).toMatch(/self_age=34/);
  // out of range: message appears, last good value holds
  await field.fill("");
  await field.pressSequentially("9");
  await page.keyboard.press("Tab");
  await expect(page.getByTestId("my-age-error")).toContainText(/18 to 70/);
  await expect(field).toHaveValue("34");
  expect(page.url()).toMatch(/self_age=34/);
});

test("What we measure lists every statistic, grouped, with crime's own line", async ({ page }) => {
  // m4.0.0 (Nathan's decision 7): out of the nav, linked from About us —
  // since Nathan's About us changes after Phase 4e, from the account's own
  // last section rather than a button at the top
  await page.goto("/");
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "How it works", exact: true }).click();
  await page.locator("article.prose-method")
    .getByRole("link", { name: "What we measure", exact: true }).click();
  await expect(page).toHaveURL(/what-we-measure/);
  for (const group of ["The people", "Cost of living", "Social life",
                       "Student life", "Weather"]) {
    await expect(
      page.getByRole("heading", { name: group, exact: true })).toBeVisible();
  }
  await expect(page.getByRole("link", { name: /See all cities by rent/ }))
    .toBeVisible();
  // Phase 2f item 8.5: the cost group shows Rent AND Everyday prices;
  // the two RPP component cards left this page (they stay scored)
  const cost = page.locator('[data-group="cost"]');
  await expect(cost).toContainText("Everyday prices");
  await expect(page.locator("main")).not.toContainText("Prices for goods");
  // item 8.4: walkability's own link name, from the registry
  await expect(page.getByRole("link", { name: "See all cities by walkability" }))
    .toBeVisible();
  const crimeRow = page.getByTestId("measure-crime");
  await expect(crimeRow).toContainText(
    /not used to calculate city rankings/);
  await crimeRow.getByRole("link", { name: /About the crime figures/ }).click();
  await expect(page).toHaveURL(/about-crime-data/);
});
