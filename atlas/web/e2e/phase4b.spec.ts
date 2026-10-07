import AxeBuilder from "@axe-core/playwright";
import { expect, test, type APIRequestContext, type Locator, type Page } from "@playwright/test";
import { E2E_API, fetchMeta, seedAboutYou } from "./helpers";
import { parsePrefs, toRankBody } from "../src/lib/prefs";
import { selectVariant } from "../src/lib/variants";
import type { AboutYou } from "../src/lib/about-you";
import type { VariantResponse } from "../src/lib/types";

/** Phase 4b (ADR 0018 amended; Nathan's seven changes): the side panel in
 * two labelled sections, "About you" then "Who you're looking for"; race
 * as one select whose default, "Prefer not to say", means race is not
 * used; no inline notes; the slider's box as the one explanation of the
 * compatibility figure, with the same-sex sentence on a same-sex search
 * only; the figure with no information box and no band words wherever it
 * appears; "Overall score" on every row and in compare; a visitor's
 * m4.0.0 details ({raceOn, race}) migrated. Every string is held to the
 * registry through /v1/meta. */

const DEFAULT_QS = "sex=male&self_age=30&age=28-40&marital=never,previously";

// the m4.0.0 wording of the strings Phase 4b removed from the registry
const REMOVED_STRINGS: [string, string][] = [
  ["about_you_note", "Your sex, education and race or ethnicity stay in this browser"],
  ["self_race_switch_label", "Include my race or ethnicity"],
  ["self_race_switch_note", "Off unless you turn it on"],
  ["self_race_same_sex_note", "Not used in a same-sex search."],
  ["self_race_choose", "Choose one"],
  ["match_info", "This compares the people who match your search against the pattern"],
  ["match_how_link", "How this is measured"],
];
const REMOVED_TESTIDS = ["self-race-switch", "self-race-note", "race-switch-block",
  "about-you-note", "match-info", "match-band", "match-same-sex-note"];
// the switch's wording, which Privacy and About us kept until 2026-09-30
const SWITCH_WORDING = /\bswitch(ed|es|ing)?\b|\bturn(ed|s|ing)? (it|race|them) (on|off)\b|\boff unless\b|\bwith it off\b/i;

const rowsOf = (page: Page) => page.getByTestId("ranked-list").locator("li");

/** What the page shows per row: city, the compatibility figure, the score. */
async function shownRows(page: Page): Promise<string[]> {
  return rowsOf(page).evaluateAll((els) => els.map((e) =>
    `${e.getAttribute("data-cbsa")}:${
      e.querySelector('[data-testid="match-figure"] .font-display')?.textContent ?? ""}:${
      e.querySelector('[data-testid="score"]')?.textContent ?? ""}`));
}

/** The same, for the variant the API computed for these details — the
 * browser's selector over the API's own response to the page's search. */
async function variantRows(request: APIRequestContext, qs: string, about: AboutYou): Promise<string[]> {
  const body = toRankBody(parsePrefs(Object.fromEntries(new URLSearchParams(qs))));
  const r = await request.post(`${E2E_API}/v1/rank`, { data: body });
  expect(r.ok()).toBe(true);
  const resp = (await r.json()) as VariantResponse;
  return selectVariant(resp, about).ranked.map((row) =>
    `${row.cbsa}:${row.match.available && row.match.display != null ? row.match.display : ""}:${
      row.score_display}`);
}

test("the panel has two labelled sections: About you, then Who you're looking for", async ({ page, request }) => {
  const ps = (await fetchMeta(request)).policy_strings;
  await page.goto("/");
  await expect(rowsOf(page).first()).toBeVisible();
  const panel = page.getByTestId("search-panel");
  const about = panel.getByRole("group", { name: ps.panel_about_you_heading, exact: true });
  const seeking = panel.getByRole("group", { name: ps.panel_looking_for_heading, exact: true });
  await expect(about).toHaveCount(1);
  await expect(seeking).toHaveCount(1);
  // visible headings, and real ones: a screen reader meets the same groups
  // and can jump between them by heading
  await expect(about.getByRole("heading", { level: 2 })).toHaveText(ps.panel_about_you_heading);
  await expect(seeking.getByRole("heading", { level: 2 })).toHaveText(ps.panel_looking_for_heading);
  await expect(about.getByRole("heading", { level: 2 })).toBeVisible();
  await expect(seeking.getByRole("heading", { level: 2 })).toBeVisible();

  // About you: I'm a, My age, My education, My race or ethnicity
  for (const label of ["I'm a", "My age", ps.self_edu_label, ps.self_race_label]) {
    await expect(about.getByLabel(label, { exact: true }), label).toHaveCount(1);
    await expect(seeking.getByLabel(label, { exact: true }), label).toHaveCount(0);
  }
  // Who you're looking for: I'm looking for, the age range, Single means
  // and the partner filters for education, income and race
  for (const label of ["I'm looking for", "Youngest age", "Oldest age", "Education", "Earning at least"]) {
    await expect(seeking.getByLabel(label, { exact: true }), label).toHaveCount(1);
    await expect(about.getByLabel(label, { exact: true }), label).toHaveCount(0);
  }
  await expect(seeking.getByRole("group", { name: "Single means" })).toHaveCount(1);
  await expect(seeking.getByTestId("race-panel").getByRole("checkbox")).toHaveCount(8);
  await expect(about.getByRole("group", { name: "Single means" })).toHaveCount(0);
  await expect(about.getByRole("checkbox")).toHaveCount(0);

  // in that order, "What matters more to you?" after them, and a rule
  // dividing the two sections
  const top = async (l: Locator) => (await l.boundingBox())!.y;
  const weighting = panel.getByTestId("weighting");
  expect(await top(about)).toBeLessThan(await top(seeking));
  expect(await top(seeking)).toBeLessThan(await top(weighting));
  await expect(weighting.getByText("What matters more to you?")).toBeVisible();
  const rule = await seeking.evaluate((el) => {
    const cs = getComputedStyle(el.parentElement as HTMLElement);
    return { width: parseFloat(cs.borderTopWidth), style: cs.borderTopStyle };
  });
  expect(rule.width).toBeGreaterThan(0);
  expect(rule.style).toBe("solid");
});

test("race is one select, Prefer not to say by default; a group selects its variant with no request", async ({ page, request }) => {
  const meta = await fetchMeta(request);
  const rankCalls: string[] = [];
  page.on("request", (req) => {
    if (req.url().includes("/api/rank")) rankCalls.push(req.postData() ?? "");
  });
  await page.goto(`/?${DEFAULT_QS}`);
  await expect(rowsOf(page).first()).toBeVisible();
  const race = page.getByTestId("self-race");
  await expect(race).toHaveValue("");
  await expect(race).toBeEnabled();
  await expect(race.locator("option")).toHaveText(
    [meta.policy_strings.prefer_not_to_say, ...meta.race_groups.map((g) => g.label)]);
  // "Prefer not to say" is the race-off variant, the one the server rendered
  const off = await variantRows(request, DEFAULT_QS, {});
  expect(await shownRows(page)).toEqual(off);
  // choosing a group turns race on: the rows become that variant's, at
  // once, with no request
  await race.selectOption("black_nh");
  const on = await variantRows(request, DEFAULT_QS, { race: "black_nh" });
  expect(on).not.toEqual(off);
  await expect.poll(() => shownRows(page)).toEqual(on);
  // and back
  await race.selectOption("");
  await expect.poll(() => shownRows(page)).toEqual(off);
  expect(rankCalls).toEqual([]);
  expect(page.url()).not.toMatch(/black_nh|self_race/);
});

test("none of the removed notes appears anywhere on the home page", async ({ page, request }) => {
  const ps = (await fetchMeta(request)).policy_strings;
  // gone from the registry, so /v1/meta carries none of them
  for (const [key] of REMOVED_STRINGS) expect(ps[key], key).toBeUndefined();
  const check = async (state: string) => {
    // the markup and the page's serialized data, and what renders
    const html = await page.content();
    const text = await page.locator("body").innerText();
    for (const [key, s] of REMOVED_STRINGS) {
      expect(html, `${state}: ${key} in the page`).not.toContain(s);
      expect(text, `${state}: ${key} on screen`).not.toContain(s);
    }
    for (const id of REMOVED_TESTIDS) {
      await expect(page.getByTestId(id), `${state}: ${id}`).toHaveCount(0);
    }
  };
  await page.goto("/");
  await expect(rowsOf(page).first()).toBeVisible();
  await check("the default search");
  await page.getByTestId("self-edu").selectOption("graduate");
  await page.getByTestId("self-race").selectOption("asian_nh");
  await check("details given");
  // a same-sex search (a woman looking for women), race muted but still
  // operable (Phase 4c), the slider's box open
  const answer = page.waitForResponse((r) => r.url().endsWith("/api/rank"));
  await page.getByTestId("seek-sex").selectOption("female");
  await answer;
  await expect(page.getByTestId("self-race")).toBeEnabled();
  await page.getByTestId("slider-info").click();
  await expect(page.getByTestId("slider-same-sex-note")).toBeVisible();
  await check("a same-sex search, the box open");
});

test("About us and Privacy name no switch: race or ethnicity is used only if you include it", async ({ page }) => {
  for (const path of ["/about", "/privacy"]) {
    await page.goto(path);
    const text = await page.locator("body").innerText();
    expect(text, `${path}: the removed switch`).not.toMatch(SWITCH_WORDING);
  }
  // Nathan's About us copy (after Phase 4e, 2026-10-06) and his Privacy
  // copy (2026-10-07) no longer carry the sentence; the Privacy page says
  // the details about you stay in your browser
  await page.goto("/privacy");
  expect(await page.locator("body").innerText(), "/privacy: details about you")
    .toMatch(/Your own browser will keep details about you/);
});

test("the slider's box reads the registry string exactly, with the same-sex sentence only on a same-sex search", async ({ page, request }) => {
  const ps = (await fetchMeta(request)).policy_strings;
  // the sentence the API serves a same-sex search (the rows' match.note)
  const r = await request.post(`${E2E_API}/v1/rank`, { data: {
    self: { age: 31 }, seeking: { sex: "male", age: [27, 38], marital: ["never_married"] } } });
  const served = ((await r.json()) as VariantResponse).variants.same_sex_note;
  expect(served).toBe(ps.match_same_sex_note);

  await page.goto(`/?${DEFAULT_QS}`); // a woman (the default) looking for men
  await expect(rowsOf(page).first()).toBeVisible();
  const btn = page.getByTestId("slider-info");
  const note = page.getByTestId("slider-info-note");
  await btn.click();
  await expect(note).toBeVisible();
  expect(await note.textContent()).toBe(ps.slider_info);
  await expect(note.getByTestId("slider-same-sex-note")).toHaveCount(0);
  await page.keyboard.press("Escape");

  // she looks for women: a same-sex search
  let answer = page.waitForResponse((res) => res.url().endsWith("/api/rank"));
  await page.getByTestId("seek-sex").selectOption("female");
  await answer;
  await btn.click();
  await expect(note).toBeVisible();
  await expect(note.getByTestId("slider-same-sex-note")).toHaveText(served);
  expect(await note.textContent()).toBe(`${ps.slider_info} ${served}`);
  await page.keyboard.press("Escape");

  // back to men: the sentence goes
  answer = page.waitForResponse((res) => res.url().endsWith("/api/rank"));
  await page.getByTestId("seek-sex").selectOption("male");
  await answer;
  await btn.click();
  await expect(note).toBeVisible();
  await expect(note.getByTestId("slider-same-sex-note")).toHaveCount(0);
  expect(await note.textContent()).toBe(ps.slider_info);
});

test("the compatibility figure has no information box and no band words: home rows, the city card, compare", async ({ page, request }) => {
  const meta = await fetchMeta(request);
  const bands = meta.features.match_propensity.band_labels as string[];
  expect(bands).toHaveLength(5);
  // the API still sends the band; only the page leaves it out
  const r = await request.post(`${E2E_API}/v1/rank`, {
    data: toRankBody(parsePrefs(Object.fromEntries(new URLSearchParams(DEFAULT_QS)))) });
  expect(((await r.json()) as VariantResponse).variants.match_bands.map((b) => b.label)).toEqual(bands);

  const bare = async (fig: Locator, where: string) => {
    await expect(fig.getByRole("button"), `${where}: a button`).toHaveCount(0);
    const text = (await fig.textContent()) ?? "";
    for (const b of bands) expect(text, `${where}: "${b}"`).not.toContain(b);
  };
  const homeRows = async (state: string) => {
    await expect(rowsOf(page).first()).toBeVisible();
    const figs = page.getByTestId("ranked-list").getByTestId("match-figure");
    const n = await figs.count();
    expect(n).toBeGreaterThan(0);
    for (let i = 0; i < n; i++) await bare(figs.nth(i), `${state}, row ${i + 1}`);
    await expect(page.getByTestId("ranked-list").getByTestId("match-info")).toHaveCount(0);
    await expect(page.getByTestId("ranked-list").getByTestId("match-band")).toHaveCount(0);
  };
  await page.goto(`/?${DEFAULT_QS}`);
  await homeRows("race off");
  // a graduate Asian woman who gives her race: San Jose's figure is capped
  // at 250+ and served "Far above most cities"
  await page.evaluate(() => window.localStorage.setItem("dsa_about_you",
    JSON.stringify({ sex: "female", edu: "graduate", race: "asian_nh" })));
  await page.reload();
  await homeRows("race on");
  await expect(rowsOf(page).filter({ hasText: "San Jose" }).getByTestId("match-figure"))
    .toContainText("250+");

  await page.goto(`/city/san-jose-california?${DEFAULT_QS}`);
  const card = page.getByTestId("ranked-card").getByTestId("match-figure");
  await expect(card).toContainText("250+");
  await bare(card, "the city card");

  await page.goto(`/compare/san-jose-california/austin-texas?${DEFAULT_QS}`);
  const table = page.getByTestId("compare-table");
  const row = table.locator("tr").filter({
    has: page.getByRole("rowheader", { name: meta.features.match_propensity.display_name, exact: true }),
  });
  await expect(row).toHaveCount(1);
  await expect(row).toContainText("250+");
  await bare(row, "compare");
});

test("every home row and the compare table label the overall score", async ({ page, request }) => {
  const ps = (await fetchMeta(request)).policy_strings;
  expect(ps.overall_score_label).toBeTruthy();
  for (const qs of [DEFAULT_QS, `${DEFAULT_QS}&sort=worst_first`]) {
    await page.goto(`/?${qs}`);
    await expect(rowsOf(page).first()).toBeVisible();
    const got = await rowsOf(page).evaluateAll((els) => els.map((e) => {
      const label = e.querySelector('[data-testid="score-label"]');
      return {
        label: label?.textContent ?? null,
        score: e.querySelector('[data-testid="score"]')?.textContent ?? null,
        // the label, the number and its "out of 100", together
        block: (label?.parentElement?.textContent ?? "").replace(/\s+/g, " ").trim(),
      };
    }));
    expect(got.length).toBeGreaterThan(0);
    for (const r of got) {
      expect(r.label).toBe(ps.overall_score_label);
      expect(r.score).toMatch(/^\d+$/);
      expect(r.block).toBe(`${ps.overall_score_label}${r.score}out of 100`);
    }
  }
  await page.goto(`/compare/provo-utah/austin-texas?${DEFAULT_QS}`);
  const table = page.getByTestId("compare-table");
  await expect(table.getByRole("rowheader", { name: ps.overall_score_label, exact: true })).toHaveCount(1);
  await expect(table).not.toContainText("Score out of 100");
  const row = table.locator("tr").filter({
    has: page.getByRole("rowheader", { name: ps.overall_score_label, exact: true }),
  });
  await expect(row.locator("td").nth(0)).toHaveText(/^\d+$/);
  await expect(row.locator("td").nth(1)).toHaveText(/^\d+$/);
});

test("a visitor's m4.0.0 details ({raceOn, race}) migrate: the same choice, stored without the switch", async ({ page, browser, request }) => {
  // the switch on with a group chosen: race on, that group
  await seedAboutYou(page, { sex: "female", edu: "graduate", raceOn: true, race: "asian_nh" });
  await page.goto(`/?${DEFAULT_QS}`);
  await expect(rowsOf(page).first()).toBeVisible();
  await expect(page.getByTestId("self-sex")).toHaveValue("female");
  await expect(page.getByTestId("self-edu")).toHaveValue("graduate");
  await expect(page.getByTestId("self-race")).toHaveValue("asian_nh");
  await expect.poll(() => page.evaluate(() => window.localStorage.getItem("dsa_about_you")))
    .toBe(JSON.stringify({ sex: "female", edu: "graduate", race: "asian_nh" }));
  const want = await variantRows(request, DEFAULT_QS, { sex: "female", edu: "graduate", race: "asian_nh" });
  await expect.poll(() => shownRows(page)).toEqual(want);
  // m4.0.0 showed exactly these (raceOn && race), and not the race-off rows
  expect(want).not.toEqual(await variantRows(request, DEFAULT_QS, { sex: "female", edu: "graduate" }));

  // the switch on with no group chosen: race was never used, and is not now
  const other = await browser.newContext();
  const p2 = await other.newPage();
  await seedAboutYou(p2, { sex: "female", raceOn: true });
  await p2.goto(`/?${DEFAULT_QS}`);
  await expect(rowsOf(p2).first()).toBeVisible();
  await expect(p2.getByTestId("self-race")).toHaveValue("");
  await expect(p2.getByTestId("self-race")).toBeEnabled();
  await expect.poll(() => p2.evaluate(() => window.localStorage.getItem("dsa_about_you")))
    .toBe(JSON.stringify({ sex: "female" }));
  await expect.poll(() => shownRows(p2)).toEqual(await variantRows(request, DEFAULT_QS, { sex: "female" }));
  await other.close();
});

test("axe: a same-sex search with the race select muted and the slider's box open", async ({ page }) => {
  await seedAboutYou(page, { sex: "male", race: "hispanic" });
  await page.goto("/?self_age=31&sex=male&age=27-38&marital=never");
  await expect(rowsOf(page).first()).toBeVisible();
  // Phase 4c: muted but operable (it was disabled in Phase 4b)
  await expect(page.getByTestId("self-race")).toBeEnabled();
  await page.getByTestId("slider-info").focus();
  await expect(page.getByTestId("slider-same-sex-note")).toBeVisible();
  await page.waitForLoadState("networkidle");
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const serious = results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? ""));
  expect(serious.map((v) => `${v.id}: ${v.nodes.length} nodes — ${v.help}`)).toEqual([]);
});
