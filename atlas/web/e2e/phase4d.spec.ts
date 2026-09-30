import AxeBuilder from "@axe-core/playwright";
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { E2E_API, fetchMeta } from "./helpers";
import statPages from "../src/data/stat-pages.json";
import type { PoliticalLeanBlock, PoliticalLeanResponse } from "../src/lib/types";

/** Phase 4d (ADR 0019, Nathan's decision): each metro's 2024 presidential
 * vote as context — never scored, never a filter or a weight, never asked.
 * The city card beside who lives here, one compare row, the What-we-measure
 * entry and a stat page that lists the cities by name; nowhere on the home
 * rows or in the side panel. Every figure is the API's (/v1/political_lean
 * on the test API; the stat page's build JSON from the same engine code),
 * the parties always read Democratic before Republican, and no evaluative
 * word appears beside them. "Not available" has its unit tests
 * (tests/political-lean.test.ts, model/tests/test_context.py): no metro of
 * the pinned fixture lacks a figure. */

const QS = "?sex=male&self_age=30&age=28-40&marital=never,previously";
// ADR 0019's neutrality rule: the parties' names and the numbers only
const EVALUATIVE = /\b(red|blue|liberal|conservative|progressive|left|right|friendly|haven|woke|maga)\b/i;

async function lean(request: APIRequestContext): Promise<Record<string, PoliticalLeanBlock>> {
  const r = await request.get(`${E2E_API}/v1/political_lean`);
  expect(r.ok()).toBe(true);
  return ((await r.json()) as PoliticalLeanResponse).metros;
}

const cbsaOf = async (request: APIRequestContext, slug: string) =>
  (await fetchMeta(request)).metros.find((m) => m.slug === slug)!.cbsa;

test("the city card shows the API's shares, caption, bar and key in party order, beside who lives here", async ({ page, request }) => {
  const meta = await fetchMeta(request);
  const blocks = await lean(request);
  const block = blocks[await cbsaOf(request, "pittsburgh-pennsylvania")];
  if (!block.available) throw new Error("fixture metro without a figure");
  await page.goto(`/city/pittsburgh-pennsylvania${QS}`);
  const card = page.locator('[data-card="political_lean"]');
  await expect(card).toBeVisible();
  await expect(card).toContainText(meta.features.political_lean.display_name);
  await expect(card.getByTestId("lean-text")).toHaveText(block.text);
  expect(block.text).toMatch(/^\d{1,3}% Democratic\u00a0· \d{1,3}% Republican$/);
  await expect(card.getByTestId("lean-caption")).toHaveText("2024 presidential vote, whole metro area");
  const bar = card.getByTestId("lean-bar");
  await expect(bar).toHaveAttribute("role", "img");
  await expect(bar).toHaveAttribute("aria-label", block.bar_label);
  expect(await bar.locator("[data-segment]").evaluateAll((els) => els.map((e) => e.getAttribute("data-segment"))))
    .toEqual(["dem", "other", "rep"]);
  // every segment is named in text: colour is never the only cue
  expect(await card.getByTestId("lean-key").locator("[data-key]").allInnerTexts())
    .toEqual(["Democratic", "Everyone else", "Republican"]);
  await expect(card.getByRole("link", { name: "See all cities by political lean" }))
    .toHaveAttribute("href", "/stats/political_lean");
  // near who lives here: the next card after it, before the crime cards
  const order = await page.locator("[data-card]").evaluateAll((els) => els.map((e) => e.getAttribute("data-card")));
  expect(order.indexOf("political_lean")).toBe(order.indexOf("who_lives_here") + 1);
  expect(order.indexOf("political_lean")).toBeLessThan(order.indexOf("violent_crime_rate"));
  expect(await card.innerText()).not.toMatch(EVALUATIVE);
});

test("a metro across state lines shows its summed shares; the card goes wherever the other stat cards go", async ({ page, request }) => {
  const blocks = await lean(request);
  const hunt = blocks[await cbsaOf(request, "huntington-west-virginia")];
  if (!hunt.available) throw new Error("fixture metro without a figure");
  await page.goto(`/city/huntington-west-virginia${QS}`);
  await expect(page.locator('[data-card="political_lean"]').getByTestId("lean-text")).toHaveText(hunt.text);
  // a metro below the ranking floor has no stat cards on its page, and so
  // no political lean card either
  await page.goto(`/city/eagle-pass-texas${QS}`);
  await expect(page.locator('[data-card="political_lean"]'))
    .toHaveCount(await page.locator('[data-card="who_lives_here"]').count());
});

test("compare adds one row with both cities' shares and no difference", async ({ page, request }) => {
  const blocks = await lean(request);
  const [a, b] = [blocks[await cbsaOf(request, "provo-utah")], blocks[await cbsaOf(request, "austin-texas")]];
  if (!a.available || !b.available) throw new Error("fixture metro without a figure");
  await page.goto(`/compare/provo-utah/austin-texas${QS}`);
  const table = page.getByTestId("compare-table");
  const row = table.locator("tr", { has: page.getByRole("rowheader", { name: "Political lean" }) });
  await expect(row).toHaveCount(1);
  const cells = row.locator("[data-lean-cell]");
  await expect(cells.nth(0)).toHaveText(a.text);
  await expect(cells.nth(1)).toHaveText(b.text);
  await expect(row.locator('[data-no-diff="political_lean"]')).toHaveText("");
  await expect(row.locator("[data-diff-for]")).toHaveCount(0);
  expect(await row.innerText()).not.toMatch(EVALUATIVE);
});

test("What we measure lists it in the context group, after who lives here, with its definition and page", async ({ page, request }) => {
  const meta = await fetchMeta(request);
  const le = meta.features.political_lean;
  await page.goto("/what-we-measure");
  const group = page.locator('[data-group="context"]');
  await expect(group).toContainText(le.display_name);
  await expect(group).toContainText(le.definition);
  expect(le.definition).toBe(
    "How the metro area voted in the 2024 presidential election. It describes everyone who voted there, not the people who match your search.");
  await expect(group.getByRole("link", { name: "See all cities by political lean" })).toHaveAttribute("href", "/stats/political_lean");
  const text = await group.innerText();
  expect(text.indexOf(meta.features.who_lives_here.display_name)).toBeLessThan(text.indexOf(le.display_name));
});

const page_ = (statPages as unknown as { pages: Record<string, { rows: { name: string; slug: string; dem_share: number; rep_share: number }[]; missing_in_ranked_set: number }> }).pages.political_lean;

const listed = (page: Page) => page.getByTestId("lean-list").locator("li");

test("the stat page lists the cities by name, sorts by either party's share on request, and says its unit once", async ({ page }) => {
  await page.goto("/stats/political_lean");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Cities by political lean");
  await expect(page.getByTestId("stat-source")).toContainText("MIT Election Data and Science Lab");
  await expect(page.getByTestId("stat-strip")).toHaveCount(0);
  await expect(page.getByTestId("lean-list-unit")).toHaveText("2024 presidential vote, whole metro area");
  await expect(page.getByTestId("lean-list-unit")).toHaveCount(1);
  // by name by default — never by either party's top
  await expect(page.getByTestId("lean-sort").getByRole("radio", { name: "Name" })).toHaveAttribute("aria-checked", "true");
  const rows = listed(page);
  await expect(rows).toHaveCount(page_.rows.length);
  const names = await rows.locator("a").allInnerTexts();
  expect(names).toEqual(page_.rows.map((r) => r.name));
  const folded = (x: string) => x.toLowerCase();
  expect(names).toEqual([...names].sort((x, y) => (folded(x) < folded(y) ? -1 : folded(x) > folded(y) ? 1 : 0)));
  // no position numbers: nothing lines the cities up by a party
  await expect(rows.first().locator("[data-pos]")).toHaveCount(0);
  expect(await rows.first().getAttribute("data-pos")).toBeNull();
  const byShare = (key: "dem_share" | "rep_share") =>
    [...page_.rows].sort((x, y) => y[key] - x[key]).map((r) => r.slug);
  for (const [label, key] of [["Democratic share", "dem_share"], ["Republican share", "rep_share"]] as const) {
    await page.getByTestId("lean-sort").getByRole("radio", { name: label }).click();
    await expect(page.getByTestId("lean-sort").getByRole("radio", { name: label })).toHaveAttribute("aria-checked", "true");
    expect(await rows.evaluateAll((els) => els.map((e) => e.getAttribute("data-slug")))).toEqual(byShare(key));
  }
  await page.getByTestId("lean-sort").getByRole("radio", { name: "Name" }).click();
  expect(await rows.locator("a").allInnerTexts()).toEqual(names);
  // the columns read Democratic, then Republican, on every row
  const first = page_.rows[0];
  await expect(rows.first().locator('[data-col="dem"]')).toContainText("Democratic");
  await expect(rows.first()).toHaveAttribute("data-slug", first.slug);
  expect(await page.getByTestId("lean-list-header").innerText()).toMatch(/DEMOCRATIC[\s\S]*REPUBLICAN/i);
  // the metros the returns cannot cover are left off and counted
  expect(page_.missing_in_ranked_set).toBe(6);
  await expect(page.getByTestId("stat-missing")).toContainText("6 of the ranked cities");
  // the sweep reads political lean's own words — the heading, the
  // definition, the sort control, the column names and the list — not the
  // note every stat page shares ("left off this list", in its plain sense)
  for (const part of [page.getByRole("heading", { level: 1 }), page.locator("main p").first(),
                      page.getByTestId("lean-sort"), page.getByTestId("lean-list-header"),
                      page.getByTestId("lean-list")]) {
    expect(await part.innerText()).not.toMatch(EVALUATIVE);
  }
});

test("not on the home rows, not in the side panel, and no page asks for it from the browser", async ({ page, baseURL }) => {
  const own = new URL(baseURL ?? "http://127.0.0.1:3100").origin;
  const seen: string[] = [];
  page.on("request", (req) => {
    const url = req.url();
    if (!url.startsWith("data:") && !url.startsWith("blob:")) seen.push(url);
  });
  await page.goto(`/${QS}`);
  await page.waitForLoadState("networkidle");
  await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
  expect(await page.locator("body").innerText()).not.toMatch(/Political lean|Democratic|Republican/);
  await page.goto(`/city/pittsburgh-pennsylvania${QS}`);
  await page.waitForLoadState("networkidle");
  await page.goto(`/compare/provo-utah/austin-texas${QS}`);
  await page.waitForLoadState("networkidle");
  expect(seen.filter((u) => /politic/i.test(u) || new URL(u).origin !== own)).toEqual([]);
});

for (const p of [
  { name: "the political lean stat page", url: "/stats/political_lean" },
  { name: "a city page with its card", url: `/city/pittsburgh-pennsylvania${QS}` },
  { name: "compare with its row", url: `/compare/provo-utah/austin-texas${QS}` },
]) {
  test(`axe: ${p.name}`, async ({ page }) => {
    await page.goto(p.url);
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const serious = results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? ""));
    expect(serious.map((v) => `${v.id}: ${v.nodes.length} nodes — ${v.help}`)).toEqual([]);
  });
}
