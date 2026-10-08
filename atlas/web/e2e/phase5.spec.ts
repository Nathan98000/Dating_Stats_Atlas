import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { expandRow, fetchMeta } from "./helpers";

/** Phase 5 (the design audit of 8 October 2026), run at the desk
 * (1440×900), a laptop below the breakpoint (1024×768) and a touch phone
 * (390×844): where the first result lands, that the rail fits, row
 * heights, no sideways scroll, the keyboard paths of the new controls,
 * reduced motion, and axe on every page. */

const DEFAULT_QS = "sex=male&self_age=30&age=28-40&marital=never,previously";
const width = (page: Page) => page.viewportSize()!.width;

async function home(page: Page, qs = "") {
  await page.goto(`/${qs}`);
  await expect(page.locator('li[data-rank="1"]')).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}

test("the #1 result is in the first screen", async ({ page }) => {
  await home(page);
  const box = await page.locator('li[data-rank="1"]').evaluate((el) => {
    const r = el.getBoundingClientRect();
    return { top: r.top + window.scrollY, bottom: r.bottom + window.scrollY };
  });
  const w = width(page);
  if (w === 1440) {
    expect(box.top).toBeLessThan(560);
    expect(box.bottom).toBeLessThanOrEqual(900);
  } else if (w === 1024) {
    expect(box.top).toBeLessThan(768);
  } else {
    expect(box.top).toBeLessThan(844);
  }
});

test("at the desk the rail fits and rows 4-10 stay compact", async ({ page }) => {
  test.skip(width(page) !== 1440, "the desk only");
  await home(page);
  const rail = page.getByTestId("rail");
  expect(await rail.evaluate((el) => el.scrollHeight === el.clientHeight)).toBe(true);
  const heights = await page.locator("li[data-rank]").evaluateAll((els) => els
    .filter((e) => { const r = Number(e.getAttribute("data-rank")); return r >= 4 && r <= 10; })
    .map((e) => e.getBoundingClientRect().height));
  expect(heights.length).toBeGreaterThan(0);
  for (const h of heights) expect(h).toBeLessThanOrEqual(96);
});

for (const path of ["/", "/city/provo-utah", "/compare/provo-utah/austin-texas", "/compare", "/about",
  "/stats/rent_1br", "/privacy", "/terms"]) {
  test(`no sideways scroll: ${path}`, async ({ page }) => {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width(page));
  });
}

test("a row opens on Enter and Space, and says so", async ({ page }) => {
  await home(page);
  const row = page.locator('li[data-rank="4"]');
  const toggle = row.getByTestId("row-toggle").locator("visible=true");
  await toggle.focus();
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await page.keyboard.press("Enter");
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  const detail = page.locator(`#${await toggle.getAttribute("aria-controls")}`);
  await expect(detail).toBeVisible();
  await page.keyboard.press("Space");
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await expect(detail).toHaveCount(0);
});

test("the expanded row: balance, compatibility, and what moved the score, every number served", async ({ page, request }) => {
  const ps = (await fetchMeta(request)).policy_strings;
  await home(page, `?${DEFAULT_QS}`);
  const row = await expandRow(page, 4);
  const detail = row.getByTestId("row-detail");
  await expect(detail.getByTestId("balance-tally")).toContainText(/\d+ men per 100 women/);
  await expect(detail.getByTestId("balance-tally")).toContainText(ps.balance_short_caption);
  await expect(detail.getByTestId("match-figure")).toContainText(ps.match_unit_line);
  await expect(detail).toContainText(ps.moved_heading);
  await expect(detail.getByTestId("moved-bars").locator("li")).toHaveCount(6);
  await expect(detail.getByRole("link", { name: /^Open .+ →$/ })).toBeVisible();
  // the dot sits right of the middle exactly when there are more men
  const per100 = Number((await detail.getByTestId("balance-tally").textContent())!.match(/(\d+) men per 100/)![1]);
  const [dot, track] = await Promise.all([
    detail.getByTestId("balance-dot").boundingBox(), detail.getByTestId("balance-track").boundingBox()]);
  const centre = dot!.x + dot!.width / 2;
  const mid = track!.x + track!.width / 2;
  if (per100 > 100) expect(centre).toBeGreaterThan(mid);
  else if (per100 < 100) expect(centre).toBeLessThan(mid);
});

test("the chips are the served movers: two pluses at most, then one minus", async ({ page }) => {
  await home(page);
  const chips = page.getByTestId("why-chips");
  const n = await chips.count();
  expect(n).toBeGreaterThan(0);
  for (let i = 0; i < n; i++) {
    const signs = await chips.nth(i).locator("[data-sign]").evaluateAll((els) => els.map((e) => e.getAttribute("data-sign")));
    expect(signs.filter((x) => x === "plus").length).toBeLessThanOrEqual(2);
    expect(signs.filter((x) => x === "minus").length).toBeLessThanOrEqual(1);
    expect(signs).toEqual([...signs].sort((a, b) => (a === "plus" ? -1 : 1) - (b === "plus" ? -1 : 1)));
    await expect(chips.nth(i)).toHaveAttribute("aria-hidden", "true");
  }
});

test("segmented controls move with the arrow keys", async ({ page }) => {
  await home(page);
  const sort = page.getByTestId("sort");
  await sort.getByRole("radio", { name: "Best first" }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(sort.getByRole("radio", { name: "Worst first" })).toHaveAttribute("aria-checked", "true");
  await expect(sort.getByRole("radio", { name: "Worst first" })).toBeFocused();
  await expect(page).toHaveURL(/sort=worst_first/);
  // one tab stop per group
  await expect(sort.getByRole("radio", { name: "Best first" })).toHaveAttribute("tabindex", "-1");
});

test("show 10 more, show all, and a new search starts again at ten", async ({ page }) => {
  await home(page);
  const rows = page.locator("li[data-rank]");
  const total = Number((await page.getByTestId("results-count").textContent())!.match(/^\d+/)![0]);
  expect(total).toBeGreaterThan(10);
  await expect(rows).toHaveCount(10);
  await page.getByTestId("show-more").click();
  await expect(rows).toHaveCount(total);
  await expect(page.getByTestId("show-more")).toHaveCount(0);
  await page.getByTestId("sort").getByRole("radio", { name: "Worst first" }).click();
  await expect(rows).toHaveCount(10);
});

test("find a city in your results widens the list, scrolls to it and focuses its link", async ({ page }) => {
  await home(page);
  const rows = page.locator("li[data-rank]");
  const last = (await rows.evaluateAll((els) => els.length));
  expect(last).toBe(10);
  // the 11th city, not yet shown
  await page.getByTestId("show-all").click();
  const eleventh = (await page.locator('li[data-rank="11"] a').first().textContent())!;
  await page.goto("/");
  await expect(rows).toHaveCount(10);
  const box = page.getByTestId("find-in-results");
  const city = eleventh.split(",")[0];
  await box.fill(city);
  // the index names a city in full ("Huntington, West Virginia")
  await page.getByRole("option", { name: new RegExp(`^${city},`) }).first().click();
  await expect(rows).toHaveCount(11);
  await expect(page.locator('li[data-rank="11"] a').first()).toBeFocused();
  await expect(page.locator('li[data-rank="11"] a').first()).toBeInViewport();
});

test("while a search is pending a progress line shows, and the result is announced", async ({ page }) => {
  await home(page);
  await page.route("**/api/rank", async (route) => {
    await new Promise((r) => setTimeout(r, 600));
    await route.continue();
  });
  const imp = page.getByRole("radiogroup", { name: "Cost of living importance" });
  if (width(page) < 1120) {
    await page.mouse.wheel(0, 1600);
    await page.getByTestId("bottom-bar").getByRole("button", { name: "Adjust your search" }).click();
  }
  await imp.getByRole("radio", { name: "A lot" }).click();
  await expect(page.getByTestId("pending-line")).toHaveClass(/progress-line/);
  await expect(page.locator("section[aria-busy=true]")).toHaveCount(1);
  await expect(page.getByTestId("results-live")).toHaveText(/^Results updated for /);
  await expect(page.getByTestId("pending-line")).not.toHaveClass(/progress-line/);
  // no dimming: the list stays at full strength
  expect(await page.getByTestId("ranked-list").evaluate((el) => getComputedStyle(el).opacity)).toBe("1");
});

test("under reduced motion no row slides (no FLIP transform)", async ({ browser }) => {
  const ctx = await browser.newContext({ reducedMotion: "reduce", viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await home(page);
  await page.evaluate(() => {
    (window as unknown as { __t: string[] }).__t = [];
    new MutationObserver((ms) => ms.forEach((m) => {
      const el = m.target as HTMLElement;
      if (el.style?.transform) (window as unknown as { __t: string[] }).__t.push(el.style.transform);
    })).observe(document.body, { subtree: true, attributes: true, attributeFilter: ["style"] });
  });
  await page.getByTestId("sort").getByRole("radio", { name: "Worst first" }).click();
  await expect(page.locator('li[data-rank]').first()).not.toHaveAttribute("data-rank", "1");
  expect(await page.evaluate(() => (window as unknown as { __t: string[] }).__t)).toEqual([]);
  await ctx.close();
});

test("with motion allowed, moved rows slide into place", async ({ page }) => {
  test.skip(width(page) !== 1440, "once is enough");
  await home(page);
  await page.evaluate(() => {
    (window as unknown as { __t: string[] }).__t = [];
    new MutationObserver((ms) => ms.forEach((m) => {
      const el = m.target as HTMLElement;
      if (el.style?.transform) (window as unknown as { __t: string[] }).__t.push(el.style.transform);
    })).observe(document.body, { subtree: true, attributes: true, attributeFilter: ["style"] });
  });
  await page.getByRole("radiogroup", { name: "Cost of living importance" }).getByRole("radio", { name: "A lot" }).click();
  await expect.poll(() => page.evaluate(() => (window as unknown as { __t: string[] }).__t.length)).toBeGreaterThan(0);
});

const PAGES = ["/", "/city/provo-utah", "/compare/provo-utah/austin-texas", "/compare", "/about",
  "/stats/rent_1br", "/privacy", "/terms", "/what-we-measure", "/about-crime-data", "/no-such-page"];
for (const path of PAGES) {
  test(`axe: ${path}`, async ({ page }) => {
    test.skip(width(page) === 1024, "1440 and 390");
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"])
      .analyze();
    const serious = results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? ""));
    expect(serious.map((v) => `${v.id}: ${v.nodes.length} — ${v.help}`)).toEqual([]);
  });
}

test("compare: the Edge column names the city that does better, and below 640px each measure is a block", async ({ page }) => {
  await page.goto(`/compare/provo-utah/austin-texas?${DEFAULT_QS}`);
  const table = page.getByTestId("compare-table");
  await expect(table).toBeVisible();
  await expect(page.locator("main#main")).toHaveCount(1);
  if (width(page) >= 640) {
    await expect(table.getByRole("columnheader", { name: "Edge" })).toBeVisible();
    const edges = await table.locator("[data-diff-for][data-edge]").evaluateAll((tds) =>
      tds.map((td) => ({ edge: td.getAttribute("data-edge"), text: td.textContent ?? "" })));
    expect(edges.length).toBeGreaterThan(5);
    for (const e of edges) {
      if (e.edge === "1") expect(e.text).toMatch(/^Provo/);
      else if (e.edge === "-1") expect(e.text).toMatch(/^Austin/);
      else expect(e.text).toMatch(/^—/);
    }
    // population is a fact: never an edge
    await expect(table.locator('[data-diff-for="who_lives_here"]')).toHaveAttribute("data-edge", "0");
  } else {
    await expect(table.locator("[data-diff-for]").first()).toBeHidden();
    // the two values sit side by side under the measure's label
    const row = table.getByRole("row").filter({ has: page.getByRole("rowheader", { name: "Rent", exact: true }) });
    const [label, a, b] = await Promise.all([
      row.getByRole("rowheader").boundingBox(), row.getByRole("cell").nth(0).boundingBox(),
      row.getByRole("cell").nth(1).boundingBox()]);
    expect(a!.y).toBeGreaterThan(label!.y);
    expect(Math.abs(a!.y - b!.y)).toBeLessThan(2);
    expect(b!.x).toBeGreaterThan(a!.x + a!.width - 2);
  }
});

test("compare landing: a link to the visitor's top two", async ({ page, request }) => {
  await page.goto(`/compare?${DEFAULT_QS}`);
  const link = page.getByTestId("compare-top-two");
  await expect(link).toHaveText(/^Your top two: .+ vs .+$/);
  const r = await request.post("http://127.0.0.1:8600/v1/rank", { data: {
    self: { age: 30 }, seeking: { sex: "male", age: [28, 40], marital: ["never_married", "previously_married"] } } });
  const ranked = (await r.json()).ranked as { slug: string }[];
  await expect(link).toHaveAttribute("href", new RegExp(`^/compare/${ranked[0].slug}/${ranked[1].slug}\\?`));
});
