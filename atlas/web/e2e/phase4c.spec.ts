import AxeBuilder from "@axe-core/playwright";
import { expect, test, type APIRequestContext, type Browser, type Page } from "@playwright/test";
import { E2E_API, fetchMeta, seedAboutYou } from "./helpers";
import { parsePrefs, toRankBody } from "../src/lib/prefs";
import { selectVariant } from "../src/lib/variants";
import type { AboutYou } from "../src/lib/about-you";
import type { BalanceBlock, RankResponse, VariantResponse } from "../src/lib/types";

/** Phase 4c (Nathan's two changes for same-sex searches; ADR 0018 and ADR
 * 0004 amended). 1: on a same-sex search own race stays selectable — the
 * select operable, muted within WCAG AA, explained by the registry's tip on
 * hover and keyboard focus (behind an information button where there is no
 * hover), the choice stored and applied once the search is opposite-sex;
 * an opposite-sex search is unchanged. 2: balance on a same-sex search —
 * the sought sex per 100 of the other sex, the figure an opposite-sex
 * search for the same people shows — on the home rows, the city card and
 * compare, with no "doesn't apply" anywhere. Strings are held to the
 * registry through /v1/meta. */

// a man looking for men 27-38, never married, with a degree (the golden
// same-sex search); the same address seen by a woman is opposite-sex
const SAME_SEX_QS = "self_age=31&sex=male&age=27-38&marital=never&edu=bachelors";
const DEFAULT_QS = "sex=male&self_age=30&age=28-40&marital=never,previously";
const DOESNT_APPLY = /doesn[’']t apply/;
// §12.3 / ADR 0003-0004: the banned vocabulary (the registry loader's list)
const BANNED = /\b(odds|rivals?|markets?|supply|inventory|competitors?)\b/i;
const TOUCH = { hasTouch: true, isMobile: true, viewport: { width: 390, height: 844 } };

const rowsOf = (page: Page) => page.getByTestId("ranked-list").locator("li");

type RGB = [number, number, number];
const rgb = (css: string): RGB => {
  const m = css.match(/[\d.]+/g)!;
  return [Number(m[0]), Number(m[1]), Number(m[2])];
};
const luminance = ([r, g, b]: RGB): number => {
  const f = (c: number) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
};
/** WCAG contrast ratio of two computed colours */
const contrast = (a: string, b: string): number => {
  const [hi, lo] = [luminance(rgb(a)), luminance(rgb(b))].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

/** A select's computed colours, its label's, and the panel's background
 * (the first opaque one above it). */
async function looks(page: Page, testid: string) {
  return page.getByTestId(testid).evaluate((el) => {
    const cs = getComputedStyle(el);
    const label = document.querySelector(`label[for="${el.id}"]`) as HTMLElement;
    let p = el.parentElement;
    let panel = "rgb(255, 255, 255)";
    while (p) {
      const bg = getComputedStyle(p).backgroundColor;
      if (bg && bg !== "rgba(0, 0, 0, 0)" && bg !== "transparent") {
        panel = bg;
        break;
      }
      p = p.parentElement;
    }
    return { color: cs.color, background: cs.backgroundColor, border: cs.borderTopColor,
             borderStyle: cs.borderTopStyle, label: getComputedStyle(label).color, panel };
  });
}

/** Every row as the page shows it: city, the whole row's text. */
async function rowTexts(page: Page): Promise<string[]> {
  return rowsOf(page).evaluateAll((els) => els.map((e) =>
    `${e.getAttribute("data-cbsa")}:${(e.textContent ?? "").replace(/\s+/g, " ")}`));
}

/** City, compatibility figure, score — as the page shows them. */
async function shownRows(page: Page): Promise<string[]> {
  return rowsOf(page).evaluateAll((els) => els.map((e) =>
    `${e.getAttribute("data-cbsa")}:${
      e.querySelector('[data-testid="match-figure"] .font-display')?.textContent ?? ""}:${
      e.querySelector('[data-testid="score"]')?.textContent ?? ""}`));
}

async function served(request: APIRequestContext, qs: string): Promise<VariantResponse> {
  const body = toRankBody(parsePrefs(Object.fromEntries(new URLSearchParams(qs))));
  const r = await request.post(`${E2E_API}/v1/rank`, { data: body });
  expect(r.ok()).toBe(true);
  return (await r.json()) as VariantResponse;
}

/** The same, for the variant the API computed for these details. */
async function variantRows(request: APIRequestContext, qs: string, about: AboutYou): Promise<string[]> {
  return selectVariant(await served(request, qs), about).ranked.map((row) =>
    `${row.cbsa}:${row.match.available && row.match.display != null ? row.match.display : ""}:${
      row.score_display}`);
}

const balanceByCity = (sel: RankResponse): Record<string, BalanceBlock> =>
  Object.fromEntries([...sel.ranked, ...sel.suppressed].map((r) => [r.cbsa, r.balance]));

async function openAs(browser: Browser, about: AboutYou, path: string, touch = false) {
  const ctx = await browser.newContext(touch ? TOUCH : {});
  const page = await ctx.newPage();
  await seedAboutYou(page, about);
  await page.goto(path);
  return { ctx, page };
}

async function noSerious(page: Page) {
  await page.waitForLoadState("networkidle");
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const serious = results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? ""));
  expect(serious.map((v) => `${v.id}: ${v.nodes.length} nodes — ${v.help}`)).toEqual([]);
}

test("on a same-sex search own race stays selectable: operable, muted within AA, the registry's tip on hover and keyboard focus", async ({ page, request }) => {
  const ps = (await fetchMeta(request)).policy_strings;
  // Nathan's wording, verbatim, through /v1/meta
  expect(ps.self_race_same_sex_tip).toBe(
    "This information is not used to calculate compatibility for same-sex couples because not " +
    "enough data is available to make a reliable estimate.");
  await seedAboutYou(page, { sex: "male" });
  await page.goto(`/?${SAME_SEX_QS}`);
  await expect(rowsOf(page).first()).toBeVisible();
  const race = page.getByTestId("self-race");

  // operable: neither disabled nor aria-disabled
  await expect(race).toBeEnabled();
  await expect(race).not.toHaveAttribute("disabled");
  await expect(race).not.toHaveAttribute("aria-disabled");

  // muted — against the education select beside it, which is not — with
  // text and border contrast at WCAG AA
  await expect(page.getByTestId("self-race-field")).toHaveAttribute("data-muted", "");
  await expect(race).toHaveClass(/\bctl-muted\b/);
  const muted = await looks(page, "self-race");
  const plain = await looks(page, "self-edu");
  expect(muted.color).not.toBe(plain.color);
  expect(muted.background).not.toBe(plain.background);
  expect(muted.label).not.toBe(plain.label);
  expect(muted.borderStyle).toBe("dashed");
  expect(contrast(muted.color, muted.background)).toBeGreaterThanOrEqual(4.5);
  expect(contrast(muted.label, muted.panel)).toBeGreaterThanOrEqual(4.5);
  expect(contrast(muted.border, muted.panel)).toBeGreaterThanOrEqual(3);
  expect(contrast(muted.border, muted.background)).toBeGreaterThanOrEqual(3);

  // the tip is always the select's description, and seen only on hover or
  // keyboard focus
  const tip = page.getByTestId("self-race-tip");
  await expect(race).toHaveAttribute("aria-describedby", (await tip.getAttribute("id"))!);
  await expect(race).toHaveAccessibleDescription(ps.self_race_same_sex_tip);
  await expect(tip).toHaveText(ps.self_race_same_sex_tip);
  await expect(tip).toBeHidden();
  await race.hover();
  await expect(tip).toBeVisible();
  // the pointer can move onto the box without it closing (WCAG 1.4.13)
  await tip.hover();
  await expect(tip).toBeVisible();
  await page.getByTestId("list-heading").hover();
  await expect(tip).toBeHidden();

  // keyboard focus: tab in from the field before
  await page.getByTestId("self-edu").focus();
  await page.keyboard.press("Tab");
  await expect(race).toBeFocused();
  await expect(tip).toBeVisible();
  // Escape dismisses it where it stands; it comes back with the next focus
  await page.keyboard.press("Escape");
  await expect(tip).toBeHidden();
  await expect(race).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await page.keyboard.press("Tab");
  await expect(race).toBeFocused();
  await expect(tip).toBeVisible();
  // and tabbing on closes it
  await page.keyboard.press("Tab");
  await expect(race).not.toBeFocused();
  await expect(tip).toBeHidden();

  // a pointer that hovers gets the box, not the touch screen's button
  await expect(page.getByTestId("self-race-tip-button")).toBeHidden();
});

test("where there is no hover, an information button beside the label opens the same text", async ({ browser, request }) => {
  const ps = (await fetchMeta(request)).policy_strings;
  const { ctx, page } = await openAs(browser, { sex: "male" }, `/?${SAME_SEX_QS}`, true);
  await expect(rowsOf(page).first()).toBeVisible();
  expect(await page.evaluate(() => window.matchMedia("(hover: none)").matches)).toBe(true);

  const btn = page.getByTestId("self-race-tip-button");
  await expect(btn).toBeVisible();
  await expect(btn).toHaveAccessibleName(ps.self_race_same_sex_tip_label);
  // beside the field's label, on its line
  const label = await page.getByTestId("self-race-field").locator("label").boundingBox();
  const box = await btn.boundingBox();
  expect(box!.x).toBeGreaterThanOrEqual(label!.x + label!.width - 1);
  expect(Math.abs((box!.y + box!.height / 2) - (label!.y + label!.height / 2))).toBeLessThan(12);

  await btn.tap();
  const note = page.getByTestId("self-race-tip-button-note");
  await expect(note).toBeVisible();
  await expect(note).toHaveText(ps.self_race_same_sex_tip);
  // the select stays operable and described there too
  const race = page.getByTestId("self-race");
  await expect(race).toBeEnabled();
  await expect(race).toHaveAccessibleDescription(ps.self_race_same_sex_tip);
  await ctx.close();
});

test("a race chosen on a same-sex search changes no number, is stored, and applies once the search is opposite-sex", async ({ page, request }) => {
  const rankCalls: string[] = [];
  page.on("request", (req) => {
    if (req.url().includes("/api/rank")) rankCalls.push(req.postData() ?? "");
  });
  await seedAboutYou(page, { sex: "male" });
  await page.goto(`/?${SAME_SEX_QS}`);
  await expect(rowsOf(page).first()).toBeVisible();
  const before = await rowTexts(page);
  // the rows are the race-off variant the API computed, and on a same-sex
  // search a race selects that same variant
  const off = await variantRows(request, SAME_SEX_QS, { sex: "male" });
  expect(await shownRows(page)).toEqual(off);
  expect(await variantRows(request, SAME_SEX_QS, { sex: "male", race: "asian_nh" })).toEqual(off);

  const race = page.getByTestId("self-race");
  await race.selectOption("asian_nh");
  await expect(race).toHaveValue("asian_nh");
  // stored as usual, in this browser only
  await expect.poll(() => page.evaluate(() => window.localStorage.getItem("dsa_about_you")))
    .toBe(JSON.stringify({ sex: "male", race: "asian_nh" }));
  // no number on the page moved, and nothing was asked of the server
  expect(await rowTexts(page)).toEqual(before);
  expect(await shownRows(page)).toEqual(off);
  expect(rankCalls).toEqual([]);

  // he now looks for women: an opposite-sex search, where his race applies
  const answer = page.waitForResponse((r) => r.url().endsWith("/api/rank"));
  await page.getByTestId("seek-sex").selectOption("female");
  await answer;
  const qs = new URL(page.url()).search.slice(1);
  const on = await variantRows(request, qs, { sex: "male", race: "asian_nh" });
  expect(on).not.toEqual(await variantRows(request, qs, { sex: "male" }));
  await expect.poll(() => shownRows(page)).toEqual(on);
  await expect(race).toHaveValue("asian_nh");
  await expect(race).not.toHaveClass(/ctl-muted/);
  await expect(page.getByTestId("self-race-tip")).toHaveCount(0);
  // the one request (the search changed) carried no detail
  expect(rankCalls.length).toBeGreaterThan(0);
  for (const b of rankCalls) expect(Object.keys(JSON.parse(b).self)).toEqual(["age"]);
  expect(page.url()).not.toMatch(/asian_nh|self_race/);
});

test("an opposite-sex search: the race field looks as it always has, with no box", async ({ page }) => {
  await page.goto(`/?${DEFAULT_QS}`); // a woman (the default) looking for men
  await expect(rowsOf(page).first()).toBeVisible();
  const race = page.getByTestId("self-race");
  await expect(race).toBeEnabled();
  await expect(race).not.toHaveClass(/ctl-muted/);
  await expect(page.getByTestId("self-race-field")).not.toHaveAttribute("data-muted");
  await expect(race).not.toHaveAttribute("aria-describedby");
  // the same look as the education select beside it
  const a = await looks(page, "self-race");
  const b = await looks(page, "self-edu");
  expect({ ...a, panel: undefined }).toEqual({ ...b, panel: undefined });
  await race.hover();
  await page.getByTestId("self-edu").focus();
  await page.keyboard.press("Tab");
  await expect(race).toBeFocused();
  await expect(page.getByTestId("self-race-tip")).toHaveCount(0);
  await expect(page.getByTestId("self-race-tip-button")).toHaveCount(0);
  await expect(page.getByRole("tooltip")).toHaveCount(0);
});

test("a same-sex search shows balance, the opposite-sex figure for the same people: home rows, the city card, a left-out city and compare", async ({ browser, request }) => {
  const meta = await fetchMeta(request);
  // what the API computed for this search, whoever is searching
  const resp = await served(request, SAME_SEX_QS);
  const man = selectVariant(resp, { sex: "male" });
  const woman = selectVariant(resp, { sex: "female" });
  expect(balanceByCity(man)).toEqual(balanceByCity(woman));
  const shown = balanceByCity(man);
  const ranked = man.ranked.filter((r) => r.balance.available);
  expect(ranked.length).toBe(man.ranked.length);
  for (const r of ranked) expect(r.balance.display).toMatch(/^\d+ men per 100 women$/);

  // the home rows, for the man (same-sex) and the woman (opposite-sex)
  const rowsFor = async (about: AboutYou) => {
    const { ctx, page } = await openAs(browser, about, `/?${SAME_SEX_QS}`);
    await expect(rowsOf(page).first()).toBeVisible();
    const out: Record<string, string> = {};
    for (const li of await rowsOf(page).all()) {
      const cbsa = (await li.getAttribute("data-cbsa"))!;
      const tally = li.getByTestId("balance-tally");
      await expect(tally).toContainText(shown[cbsa].display!);
      out[cbsa] = (await tally.textContent()) ?? "";
    }
    // the footnote is the caption on this search too
    await expect(page.getByTestId("balance-footnote")).toContainText(meta.policy_strings.balance_caption);
    await ctx.close();
    return out;
  };
  const his = await rowsFor({ sex: "male" });
  expect(Object.keys(his).length).toBe(man.ranked.length);
  expect(await rowsFor({ sex: "female" })).toEqual(his);

  // the city card of a ranked city, and a left-out city's surviving balance
  const { ctx, page } = await openAs(browser, { sex: "male" }, `/city/new-york-new-york?${SAME_SEX_QS}`);
  await expect(page.getByTestId("ranked-card")).toBeVisible();
  await expect(page.getByTestId("ranked-card")).toContainText(shown["35620"].display!);
  const left = man.suppressed.find((r) => r.cbsa === "26580")!;
  expect(left.balance.available).toBe(true);
  await page.goto(`/city/huntington-west-virginia?${SAME_SEX_QS}`);
  await expect(page.getByTestId("balance-survives")).toBeVisible();
  await expect(page.getByTestId("balance-survives")).toContainText(left.balance.display!);

  // compare: both tallies and their difference
  await page.goto(`/compare/new-york-new-york/austin-texas?${SAME_SEX_QS}`);
  const table = page.getByTestId("compare-table");
  await expect(table).toBeVisible();
  const row = table.locator("tr").filter({
    has: page.getByRole("rowheader", { name: meta.features.pool_balance.display_name, exact: true }),
  });
  await expect(row).toHaveCount(1);
  await expect(row).toContainText(shown["35620"].display!);
  await expect(row).toContainText(shown["12420"].display!);
  await expect(table.locator('[data-diff-for="balance"]')).toBeVisible();
  await ctx.close();
});

test("no \"doesn't apply\" (and no banned word) is served or shown: /v1/meta, the rank response, home, city, compare and About us", async ({ page, request }) => {
  const ps = (await fetchMeta(request)).policy_strings;
  expect(ps.balance_same_sex).toBeUndefined();
  for (const [k, text] of Object.entries(ps)) expect(text, k).not.toMatch(DOESNT_APPLY);
  const body = toRankBody(parsePrefs(Object.fromEntries(new URLSearchParams(SAME_SEX_QS))));
  const raw = await (await request.post(`${E2E_API}/v1/rank`, { data: body })).text();
  expect(raw).not.toMatch(DOESNT_APPLY);
  expect(raw).not.toContain("balance_applies");
  // the pages, markup (and the data serialised into it) and screen, for a
  // same-sex visitor — on the home page with the race field's tip open —
  // and About us, whose "balance doesn't apply" sentence Nathan removed
  // after the report (PHASE4C.md §6)
  await seedAboutYou(page, { sex: "male" });
  for (const path of [`/?${SAME_SEX_QS}`, `/city/new-york-new-york?${SAME_SEX_QS}`,
    `/city/huntington-west-virginia?${SAME_SEX_QS}`,
    `/compare/new-york-new-york/austin-texas?${SAME_SEX_QS}`, `/?${DEFAULT_QS}`, "/about"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    if (path === `/?${SAME_SEX_QS}`) {
      await page.getByTestId("self-race").hover();
      await expect(page.getByTestId("self-race-tip")).toBeVisible();
    }
    expect(await page.content(), `${path}: markup`).not.toMatch(DOESNT_APPLY);
    const screen = await page.locator("body").innerText();
    expect(screen, `${path}: screen`).not.toMatch(DOESNT_APPLY);
    expect(screen, `${path}: banned vocabulary`).not.toMatch(BANNED);
  }
});

test("axe: a same-sex search with the race tip open from the keyboard", async ({ page }) => {
  await seedAboutYou(page, { sex: "male", race: "hispanic" });
  await page.goto(`/?${SAME_SEX_QS}`);
  await expect(rowsOf(page).first()).toBeVisible();
  await page.getByTestId("self-edu").focus();
  await page.keyboard.press("Tab");
  await expect(page.getByTestId("self-race-tip")).toBeVisible();
  await noSerious(page);
});

test("axe: a same-sex search on a touch screen with the information button's box open", async ({ browser }) => {
  const { ctx, page } = await openAs(browser, { sex: "male" }, `/?${SAME_SEX_QS}`, true);
  await expect(rowsOf(page).first()).toBeVisible();
  await page.getByTestId("self-race-tip-button").tap();
  await expect(page.getByTestId("self-race-tip-button-note")).toBeVisible();
  await noSerious(page);
  await ctx.close();
});
