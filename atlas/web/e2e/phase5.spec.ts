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

test("at the desk the rail fits the window (scrolling inside itself) and rows 4-10 stay compact", async ({ page }) => {
  test.skip(width(page) !== 1440, "the desk only");
  await home(page);
  const rail = page.getByTestId("rail");
  expect(await rail.evaluate((el) => el.getBoundingClientRect().height)).toBeLessThanOrEqual(900 - 32);
  expect(await rail.evaluate((el) => getComputedStyle(el).overflowY)).toBe("auto");
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
  // after the Phase 5 report: the longer words sit behind balance's
  // information box, the compatibility figure keeps none (Phase 4b), and
  // since 2026-10-10 (Nathan) neither do the points: their yardstick shows
  // under their heading (F22) and nowhere else
  // Phase 6: the button is named on its own (F26)
  await expect(detail.getByRole("button", { name: ps.balance_info_label })).toHaveCount(1);
  await expect(detail.getByRole("button", { name: /^About/ })).toHaveCount(1);
  await expect(detail.getByTestId("match-figure").getByRole("button")).toHaveCount(0);
  await expect(detail.getByTestId("moved-caption")).toHaveText(ps.moved_caption);
  await expect(detail.getByRole("link", { name: /^Open .+ →$/ })).toBeVisible();
  await expect(detail.getByTestId("match-figure")).toContainText(ps.match_unit_line);
  await expect(detail).toContainText(ps.moved_heading);
  await expect(detail.getByTestId("moved-bars").locator("li")).toHaveCount(6);
  await expect(detail.getByRole("link", { name: /^Open .+ →$/ })).toBeVisible();
  // the dots (Nathan, 2026-10-10, replacing the track): ten for the other
  // sex, one for every ten of the sought sex, the last filled to the
  // fraction — the served per_100 drawn, never a new number
  const per100 = Number((await detail.getByTestId("balance-tally").textContent())!.match(/(\d+) men per 100/)![1]);
  const dots = detail.getByTestId("balance-dots");
  await expect(dots.locator('[data-row="seeker"]')).toHaveAttribute("data-full", "10");
  const tens = Math.min(160, Math.max(40, per100)) / 10;
  const sought = dots.locator('[data-row="sought"]');
  await expect(sought).toHaveAttribute("data-full", String(Math.floor(tens)));
  if (tens % 1) await expect(sought).toHaveAttribute("data-part", (tens % 1).toFixed(1));
  else await expect(sought).not.toHaveAttribute("data-part", /.*/);
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
    // hidden from screen readers (the row carries the line): the group, or
    // since Phase 6 on a card, where the Details chevron follows the chips,
    // each chip
    const hidden = await chips.nth(i).evaluate((g) => g.getAttribute("aria-hidden") === "true"
      || [...g.querySelectorAll("[data-sign]")].every((c) => c.getAttribute("aria-hidden") === "true"));
    expect(hidden).toBe(true);
  }
});

test("segmented controls move with the arrow keys", async ({ page }) => {
  await home(page);
  const sort = page.getByTestId("sort").locator("visible=true");
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
  await page.getByTestId("sort").locator("visible=true").getByRole("radio", { name: "Worst first" }).click();
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
  await page.getByTestId("sort").locator("visible=true").getByRole("radio", { name: "Worst first" }).click();
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

test("compare: the Comparison column names the city that does better, and below 640px each measure is a block", async ({ page }) => {
  await page.goto(`/compare/provo-utah/austin-texas?${DEFAULT_QS}`);
  const table = page.getByTestId("compare-table");
  await expect(table).toBeVisible();
  await expect(page.locator("main#main")).toHaveCount(1);
  if (width(page) >= 640) {
    // Nathan, 2026-10-10: "Comparison", and the page never says "edge"
    await expect(table.getByRole("columnheader", { name: "Comparison" })).toBeVisible();
    await expect(page.locator("main")).not.toContainText(/\bedge\b/i);
    const edges = await table.locator("[data-diff-for][data-edge]").evaluateAll((tds) =>
      tds.map((td) => ({ edge: td.getAttribute("data-edge"), text: td.textContent ?? "" })));
    expect(edges.length).toBeGreaterThan(5);
    for (const e of edges) {
      if (e.edge === "1") expect(e.text).toMatch(/^Provo/);
      else if (e.edge === "-1") expect(e.text).toMatch(/^Austin/);
      // no dash (2026-10-10): a row the site doesn't judge, or a tie,
      // shows its plain difference alone
      else expect(e.text).toMatch(/^[+−]?\$?\d/);
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

for (const path of ["/city/provo-utah", "/compare/provo-utah/austin-texas"]) {
  test(`landmark-one-main and skip-link pass: ${path}`, async ({ page }) => {
    test.skip(width(page) === 1024, "1440 and 390");
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page }).withRules(["landmark-one-main", "skip-link", "region"]).analyze();
    expect(results.violations.map((v) => v.id)).toEqual([]);
    await expect(page.locator("main#main")).toHaveCount(1);
  });
}

test("every page has its own title and Open Graph tags", async ({ page }) => {
  test.skip(width(page) !== 1440, "once is enough");
  const want: [string, RegExp][] = [
    ["/", /^Dating Stats Atlas$/],
    ["/city/provo-utah", /^Provo, UT · Dating Stats Atlas$/],
    ["/compare/provo-utah/austin-texas", /^Provo, UT vs Austin, TX · Dating Stats Atlas$/],
    ["/compare", /^Compare · Dating Stats Atlas$/],
    ["/stats/rent_1br", /^Rent by city · Dating Stats Atlas$/],
    ["/about", /^How it works · Dating Stats Atlas$/],
    ["/privacy", /^Privacy · Dating Stats Atlas$/],
    ["/terms", /^Terms · Dating Stats Atlas$/],
  ];
  for (const [path, title] of want) {
    await page.goto(path);
    await expect(page, path).toHaveTitle(title);
    await expect(page.locator('meta[property="og:title"]'), path).toHaveAttribute("content", title);
    await expect(page.locator('meta[property="og:description"]'), path).toHaveAttribute("content", /.+/);
    await expect(page.locator('meta[property="og:url"]'), path).toHaveAttribute("content", /^https?:\/\/.+/);
  }
});

test("the 404 has the header, the footer and a main landmark", async ({ page }) => {
  const r = await page.goto("/no-such-page");
  expect(r!.status()).toBe(404);
  await expect(page.locator("header").first()).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Footer" })).toBeVisible();
  await expect(page.locator("main#main")).toHaveCount(1);
});

test("the city page leads with the score; on a phone the map is a thumbnail beside the name", async ({ page }) => {
  await page.goto(`/city/provo-utah?${DEFAULT_QS}`);
  const card = page.getByTestId("ranked-card");
  await expect(card.getByTestId("score")).toHaveText(/^\d+$/);
  await expect(card.getByTestId("score-label")).toHaveText("Overall score");
  await expect(card.getByTestId("balance-tally")).toBeVisible();
  if (width(page) < 640) {
    const thumb = page.getByTestId("locator-thumb");
    await expect(thumb).toBeVisible();
    expect((await thumb.boundingBox())!.width).toBeLessThanOrEqual(97);
    await expect(page.getByTestId("locator-map")).toBeHidden();
    // stat cards two to a row
    const cards = page.locator("[data-card]");
    const [a, b] = await Promise.all([cards.nth(0).boundingBox(), cards.nth(1).boundingBox()]);
    expect(Math.abs(a!.y - b!.y)).toBeLessThan(2);
  } else {
    await expect(page.getByTestId("locator-map")).toBeVisible();
  }
});

test("the score tracks mark the served median of the ranked cities", async ({ page, request }) => {
  const r = await request.post("http://127.0.0.1:8600/v1/rank", { data: {
    self: { age: 30 }, seeking: { sex: "male", age: [28, 40], marital: ["never_married", "previously_married"] } } });
  const resp = await r.json();
  const median = resp.variants.list[resp.variants.default].score_median;
  expect(median.display).toMatch(/^\d+$/);
  await page.goto(`/?${DEFAULT_QS}`);
  const card = page.getByTestId("featured-card").first();
  await expect(card.getByTestId("median-tick")).toHaveCount(1);
  await expect(card).toContainText(`median ${median.display}`);
  await page.goto(`/city/provo-utah?${DEFAULT_QS}`);
  await expect(page.getByTestId("ranked-card").getByTestId("median-tick")).toHaveCount(1);
  await expect(page.getByTestId("ranked-card")).toContainText(`median ${median.display}`);
});

test("after the Phase 5 report: the cards' photo links to the city, no card shows the map, and the search bar carries no trust line", async ({ page, request }) => {
  const ps = (await fetchMeta(request)).policy_strings;
  await home(page, `?${DEFAULT_QS}`);
  const cards = page.getByTestId("featured-card");
  await expect(cards).toHaveCount(3);
  for (let i = 0; i < 3; i++) {
    const card = cards.nth(i);
    const name = card.getByRole("heading").getByRole("link");
    const photoLink = card.getByTestId("card-photo-link");
    await expect(photoLink).toHaveAttribute("href", (await name.getAttribute("href"))!);
    // a mouse route only: out of the tab order, hidden from screen readers
    await expect(photoLink).toHaveAttribute("tabindex", "-1");
    await expect(photoLink).toHaveAttribute("aria-hidden", "true");
    await expect(card.locator('img[src^="/map/"]')).toHaveCount(0);
    await expect(card).toContainText(ps.card_matches);
    await expect(card).not.toContainText("single men match");
  }
  await cards.first().getByTestId("card-photo-link").click();
  await expect(page).toHaveURL(/\/city\//);
  await page.goBack();
  const quick = page.getByTestId("quick-search");
  await expect(quick).not.toContainText("We don't save your searches");
  await expect(quick).not.toContainText("Census Bureau data");
});
