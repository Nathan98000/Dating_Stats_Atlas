import { expect, test, type Page } from "@playwright/test";
import { E2E_API, expandRow, fetchMeta, openRailGroup, photoOnDisk, seedAboutYou } from "./helpers";

/** Phase 6 (the round-3 design review of 8 October 2026, built from
 * atlas/PHASE6_PROMPT.md), run at the desk (1440×900), a laptop below the
 * breakpoint (1024×768) and a touch phone (390×844). */

const width = (page: Page) => page.viewportSize()!.width;
/** The same-sex reference search (a man looking for men 28-38) and the
 * site's default (a woman, by default, looking for men 28-40). */
const SAME_SEX_QS = "?self_age=33&sex=male&age=28-38&marital=never,previously";
/** The real build's production site, for the checks that need its metros
 * (Virginia Beach, Duluth): set P6_REAL_BASE (e.g. http://localhost:3300);
 * skipped otherwise, as CI's fixture build has neither. */
const REAL = process.env.P6_REAL_BASE;
const REAL_API = process.env.P6_REAL_API ?? "http://127.0.0.1:8000";

async function home(page: Page, qs = "") {
  await page.goto(`/${qs}`);
  await expect(page.locator('li[data-rank="1"]')).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}

/** The review's target check (scripts/review/audit_in_page.js, part 1):
 * every visible interactive element smaller than 44×44, except a link set
 * inline inside running text. */
async function smallTargets(page: Page) {
  return page.evaluate(() => {
    const visible = (el: Element) => {
      const r = el.getBoundingClientRect();
      if (r.width < 1 || r.height < 1) return false;
      if (el.closest(".sr-only")) return false;
      let a: Element | null = el;
      while (a) {
        const s = getComputedStyle(a);
        if (s.display === "none" || s.visibility === "hidden" || +s.opacity === 0) return false;
        a = a.parentElement;
      }
      return true;
    };
    const sel = 'a[href], button, input:not([type=hidden]), select, textarea, summary, [role=button], [role=radio], [role=option], [role=tab], [role=checkbox], [role=switch], [tabindex]:not([tabindex="-1"])';
    const out: string[] = [];
    const seen = new Set<Element>();
    for (const el of Array.from(document.querySelectorAll(sel))) {
      if (!visible(el)) continue;
      let t: Element = el;
      const inp = el as HTMLInputElement;
      if ((inp.type === "checkbox" || inp.type === "radio") && el.closest("label")) t = el.closest("label")!;
      if (seen.has(t)) continue;
      seen.add(t);
      const r = t.getBoundingClientRect();
      if (r.width >= 43.5 && r.height >= 43.5) continue;
      const parentText = (t.parentElement?.innerText || "").replace((t as HTMLElement).innerText, "");
      const inline = t.tagName === "A" && getComputedStyle(t).display === "inline" && /\S/.test(parentText);
      if (inline) continue;
      const name = (t.getAttribute("aria-label") || (t as HTMLElement).innerText || "").trim().slice(0, 40);
      out.push(`${t.tagName.toLowerCase()} "${name}" ${Math.round(r.width)}×${Math.round(r.height)}`);
    }
    return out;
  });
}

test.describe("touch targets below 1120px (F02)", () => {
  test.beforeEach(({ page }) => {
    test.skip(width(page) >= 1120, "below the desk only");
  });

  test("home: default, the age popover, the sheet and an open row", async ({ page }) => {
    await home(page);
    expect(await smallTargets(page), "default").toEqual([]);
    await page.getByTestId("age-token").click();
    await expect(page.getByTestId("age-popover")).toBeVisible();
    expect(await smallTargets(page), "age popover").toEqual([]);
    await page.keyboard.press("Escape");
    await expandRow(page, 4);
    expect(await smallTargets(page), "row open").toEqual([]);
    await page.mouse.wheel(0, 1600);
    await page.getByTestId("bottom-bar").getByRole("button", { name: "Adjust your search" }).click();
    await page.locator("dialog[open]").waitFor();
    for (const g of ["Narrow it down", "Sharpen compatibility"]) {
      const b = page.locator("dialog[open]").getByRole("button", { name: g, exact: true });
      if ((await b.getAttribute("aria-expanded")) !== "true") await b.click();
    }
    expect(await smallTargets(page), "sheet open").toEqual([]);
  });

  for (const [name, url] of [
    ["a city page", "/city/austin-texas"],
    ["a compare pair", "/compare/austin-texas/provo-utah"],
    ["a stat page", "/stats/rent_1br"],
    ["the political lean page", "/stats/political_lean"],
    ["What we measure", "/what-we-measure"],
  ] as const) {
    test(`${name}`, async ({ page }) => {
      await page.goto(url);
      await page.evaluate(() => document.fonts.ready);
      expect(await smallTargets(page)).toEqual([]);
    });
  }

  test("How it works, with the credit lists open", async ({ page }) => {
    await page.goto("/about");
    for (const d of await page.locator("details").all()) await d.evaluate((el) => ((el as HTMLDetailsElement).open = true));
    expect(await smallTargets(page)).toEqual([]);
  });
});

test.describe("the age popover's exact ages (F02)", () => {
  test("From and To keep the thumbs' state, clamp to 18-70 and keep From <= To", async ({ page }) => {
    await home(page);
    await page.getByTestId("age-token").click();
    const from = page.getByTestId("age-from");
    const to = page.getByTestId("age-to");
    await expect(from).toHaveValue("28");
    await expect(to).toHaveValue("40");
    await expect(from).toHaveAccessibleName("Youngest age");
    await expect(to).toHaveAccessibleName("Oldest age");
    await from.fill("31");
    await from.press("Enter");
    await expect(page.getByTestId("age-output")).toHaveText("31 – 40");
    await expect(page.getByRole("slider", { name: "Youngest age" })).toHaveAttribute("aria-valuetext", "youngest age 31");
    await to.fill("90");
    await to.press("Enter");
    await expect(to).toHaveValue("70");
    await from.fill("75");
    await from.press("Enter");
    await expect(from).toHaveValue("70");
    await expect(page.getByTestId("age-output")).toHaveText("70 – 70");
    await from.fill("5");
    await from.press("Enter");
    await expect(from).toHaveValue("18");
    // Escape still closes the popover and returns focus to its button
    await from.press("Escape");
    await expect(page.getByTestId("age-popover")).toBeHidden();
    await expect(page.getByTestId("age-token")).toBeFocused();
  });
});

test.describe("home results (D)", () => {
  test("at 390x844 the #1 card's score ends in the first screen (F15)", async ({ page }) => {
    test.skip(width(page) !== 390, "the phone only");
    await home(page);
    const bottom = await page.locator('li[data-rank="1"] [data-testid=score]').evaluate(
      (el) => el.getBoundingClientRect().bottom + window.scrollY);
    expect(bottom).toBeLessThanOrEqual(844);
    // the photo is 16:7 below 640px, and Best/Worst sits under the cards
    const ph = await page.locator('li[data-rank="1"] [data-testid=card-photo-link]').boundingBox();
    expect(ph!.width / ph!.height).toBeCloseTo(16 / 7, 1);
    const sort = page.getByTestId("sort").locator("visible=true");
    await expect(sort).toHaveCount(1);
    const sortTop = (await sort.boundingBox())!.y;
    const cardsBottom = (await page.locator('li[data-rank="3"]').boundingBox())!;
    expect(sortTop).toBeGreaterThan(cardsBottom.y + cardsBottom.height);
  });

  test("the cards' Details chevron opens the three tiles, one card at a time (F06)", async ({ page }) => {
    await home(page);
    const cards = page.getByTestId("featured-card");
    const t1 = cards.nth(0).getByTestId("card-toggle");
    const t2 = cards.nth(1).getByTestId("card-toggle");
    await expect(t1).toHaveAttribute("aria-expanded", "false");
    await expect(t1).toHaveAccessibleName(/^Details for /);
    const box = await t1.boundingBox();
    expect(box!.width).toBeGreaterThanOrEqual(44);
    expect(box!.height).toBeGreaterThanOrEqual(44);
    await t1.click();
    await expect(t1).toHaveAttribute("aria-expanded", "true");
    const id = await t1.getAttribute("aria-controls");
    const detail = page.locator(`#${id}`);
    await expect(detail).toBeVisible();
    await expect(detail.locator("section")).toHaveCount(3);
    await expect(detail.getByRole("link", { name: /^Open .+ →$/ })).toBeVisible();
    await expect(detail.getByRole("button", { name: "Compare" })).toBeVisible();
    if (width(page) >= 768) {
      // one panel under the card row, spanning the three cards
      const panel = (await detail.boundingBox())!;
      const c1 = (await cards.nth(0).boundingBox())!;
      const c3 = (await cards.nth(2).boundingBox())!;
      expect(panel.y).toBeGreaterThan(c1.y + c1.height);
      expect(panel.width).toBeGreaterThanOrEqual(c3.x + c3.width - c1.x - 1);
      // one card open at a time
      await t2.click();
      await expect(t2).toHaveAttribute("aria-expanded", "true");
      await expect(t1).toHaveAttribute("aria-expanded", "false");
      await expect(page.getByTestId("card-detail")).toHaveCount(1);
    } else {
      // inside the card, under its chips
      expect(await cards.nth(0).getByTestId("card-detail").count()).toBe(1);
    }
    await (width(page) >= 768 ? t2 : t1).click();
    await expect(page.getByTestId("card-detail")).toHaveCount(0);
  });

  test("the chips are lifestyle movers: never the pool or compatibility (F12)", async ({ page, request }) => {
    const meta = await fetchMeta(request);
    await home(page);
    const banned = [meta.features.pool_size.chip_label, meta.features.match_propensity.chip_label];
    const chips = await page.getByTestId("why-chips").allInnerTexts();
    for (const set of chips) for (const b of banned) expect(set.split("\n")).not.toContain(b);
    // the fixture's ten tell apart: at least three distinct sets
    expect(new Set(chips.map((c) => c.trim())).size).toBeGreaterThanOrEqual(3);
  });

  test("a metro's served caution opens its detail (F08)", async ({ page, request }) => {
    const meta = await fetchMeta(request);
    await home(page);
    await page.getByTestId("show-all").click();
    const li = page.locator('li[data-slug="huntington-west-virginia"]');
    await li.getByTestId("row-toggle").locator("visible=true").click();
    const caps = li.getByTestId("flag-captions");
    await expect(caps).toHaveText(meta.policy_strings.low_allocation_purity);
    // the detail opens with it: before the tiles
    const capY = (await caps.boundingBox())!.y;
    const tileY = (await li.getByTestId("row-detail").locator("section").first().boundingBox())!.y;
    expect(capY).toBeLessThan(tileY);
    // the glyph is decoration
    await expect(caps.locator("svg")).toHaveAttribute("aria-hidden", "true");
    // a metro with no flag shows none
    await expandRow(page, 4);
    await expect(page.locator('li[data-rank="4"]').getByTestId("flag-captions")).toHaveCount(0);
  });

  test("same-sex: the matches note shows only on a same-sex search, never in the server's HTML (F01)", async ({ page, request, browser }) => {
    const meta = await fetchMeta(request);
    // the server never knows the visitor's sex, so never renders the note
    // (the registry's strings travel with the page as data; the note's
    // element is the browser's choice)
    const html = await (await request.get(`/${SAME_SEX_QS}`)).text();
    expect(html).not.toContain('data-testid="same-sex-note"');
    const noJs = await browser.newContext({ javaScriptEnabled: false });
    const bare = await noJs.newPage();
    await bare.goto(`/${SAME_SEX_QS}`);
    await expect(bare.getByTestId("list-heading")).toBeVisible();
    await expect(bare.getByTestId("same-sex-note")).toHaveCount(0);
    await noJs.close();
    // opposite-sex (the stored sex is a woman): no note
    await seedAboutYou(page, { sex: "female" });
    await home(page, SAME_SEX_QS);
    await expect(page.getByTestId("same-sex-note")).toHaveCount(0);
    await expect(page.getByTestId("balance-footnote")).toHaveText(meta.policy_strings.balance_caption);
  });

  test("same-sex: a man looking for men sees the note and the same-sex balance caption", async ({ page, request }) => {
    const meta = await fetchMeta(request);
    await seedAboutYou(page, { sex: "male" });
    await home(page, SAME_SEX_QS);
    await expect(page.getByTestId("same-sex-note")).toHaveText(
      meta.policy_strings.same_sex_pool_note.replace("{sought_one}", "man").replace("{sought}", "men"));
    await expect(page.getByTestId("same-sex-note")).toContainText("every single man in these ages");
    await expect(page.getByTestId("balance-footnote")).toHaveText(meta.policy_strings.balance_caption_same_sex);
    const row = await expandRow(page, 4);
    await row.getByRole("button", { name: meta.policy_strings.balance_info_label }).click();
    await expect(page.getByTestId("info-tip-note")).toHaveText(meta.policy_strings.balance_caption_same_sex);
  });

  test("the row detail: Even under the tick, the bars' yardstick in view, named info buttons (F25, F22, F26)", async ({ page, request }) => {
    const meta = await fetchMeta(request);
    await home(page);
    const row = await expandRow(page, 4);
    const detail = row.getByTestId("row-detail");
    await expect(detail.getByTestId("balance-tally")).toContainText(meta.policy_strings.balance_even);
    await expect(detail.getByTestId("moved-caption")).toHaveText(meta.policy_strings.moved_caption);
    await expect(detail.getByRole("button", { name: meta.policy_strings.balance_info_label })).toHaveCount(1);
    await expect(detail.getByRole("button", { name: meta.policy_strings.moved_info_label })).toHaveCount(1);
    // the score reads "Overall score {n} out of 100"; the bare number is hidden
    const n = await row.getByTestId("score").innerText();
    await expect(row.getByText(meta.policy_strings.score_label_sr.replace("{n}", n))).toHaveCount(1);
    await expect(row.getByTestId("score")).toHaveAttribute("aria-hidden", "true");
  });

  test("a lifestyle bar names its chip where the words differ (F21)", async ({ page, request }) => {
    const meta = await fetchMeta(request);
    await home(page);
    const row = await expandRow(page, 4);
    const chips = (await row.getByTestId("why-chips").innerText()).split("\n").map((c) => c.trim()).filter(Boolean);
    for (const chip of chips) {
      const key = Object.keys(meta.features).find((k) => meta.features[k].chip_label === chip)!;
      const pillar = meta.features[key].pillar;
      const bar = row.locator(`[data-pillar="${pillar}"]`);
      const pillarName = meta.pillars[pillar].display_name;
      if (chip.toLowerCase() !== pillarName.toLowerCase()) {
        await expect(bar).toContainText(`${pillarName} · `);
        await expect(bar).toContainText(chip.toLowerCase());
      }
    }
  });

  test("phone rows read 'matches' (F21)", async ({ page }) => {
    test.skip(width(page) >= 640, "below 640px");
    await home(page);
    const line = page.locator('li[data-rank="4"] p').filter({ hasText: / matches$/ });
    await expect(line).toHaveCount(1);
  });
});

test.describe("on the real build (P6_REAL_BASE)", () => {
  test.skip(!REAL, "needs the real build's site");
  test("after 'Show all' and #50, the back link and Back restore 193 rows with #50 in view (F18)", async ({ page }) => {
    await page.goto(`${REAL}/`);
    await page.getByTestId("show-all").click();
    const rows = page.locator("li[data-rank]");
    await expect(rows).toHaveCount(193);
    const r50 = page.locator('li[data-rank="50"]');
    await r50.locator("h3 a").click();
    await expect(page).toHaveURL(/\/city\//);
    expect(await page.evaluate(() => Object.keys(sessionStorage))).toEqual(["dsa_place"]);
    await page.getByTestId("back-to-results").click();
    await expect(rows).toHaveCount(193);
    await expect(r50).toBeInViewport();
    await r50.locator("h3 a").click();
    await expect(page).toHaveURL(/\/city\//);
    await page.goBack();
    await expect(rows).toHaveCount(193);
    await expect(r50).toBeInViewport();
  });
  test("Virginia Beach's detail shows the group-housing caution; Duluth both (F08)", async ({ page, request }) => {
    const meta = await (await request.get(`${REAL_API}/v1/meta`)).json();
    for (const [slug, flags] of [["virginia-beach-virginia", ["gq_flag"]],
                                 ["duluth-minnesota", ["low_allocation_purity", "gq_flag"]]] as const) {
      await page.goto(`${REAL}/`);
      await page.getByTestId("show-all").click();
      const li = page.locator(`li[data-slug="${slug}"]`);
      await li.getByTestId("row-toggle").locator("visible=true").click();
      const caps = li.getByTestId("flag-captions").locator("li");
      await expect(caps).toHaveCount(flags.length);
      for (const f of flags) await expect(li.locator(`[data-flag="${f}"]`)).toHaveText(meta.policy_strings[f]);
    }
  });
});

test.describe("changing the search (E)", () => {
  async function openSheet(page: Page) {
    await page.mouse.wheel(0, 1600);
    await page.getByTestId("bottom-bar").getByRole("button", { name: "Adjust your search" }).click();
    await page.locator("dialog[open]").waitFor();
  }

  test("'Show results' closes onto the focused results heading; the bar shows the search in flight; the change is said and shown (F05)", async ({ page, request }) => {
    test.skip(width(page) >= 1120, "the sheet is below the desk");
    const ps = (await fetchMeta(request)).policy_strings;
    await home(page);
    let release: () => void = () => {};
    const held = new Promise<void>((r) => { release = r; });
    await page.route("**/api/rank", async (route) => { await held; await route.continue(); });
    const before = await page.locator("li[data-rank]").evaluateAll((els) => els.map((e) => e.getAttribute("data-cbsa")));
    await openSheet(page);
    // the sheet knows the whole search (F19)
    await expect(page.getByTestId("sheet-summary")).toHaveText(
      ps.sheet_search_summary.replace("{you}", "Woman").replace("{age}", "30").replace("{sought}", "Men").replace("{ages}", "28–40"));
    const dialog = page.locator("dialog[open]");
    await dialog.getByRole("radiogroup", { name: "Cost of living importance" }).getByRole("radio", { name: "A lot" }).click();
    await dialog.getByRole("radiogroup", { name: "Weather importance" }).getByRole("radio", { name: "A lot" }).click();
    await dialog.getByRole("radiogroup", { name: "Social life importance" }).getByRole("radio", { name: "Not much" }).click();
    await page.getByTestId("show-results").click();
    await expect(page.locator("dialog[open]")).toHaveCount(0);
    await expect(page.getByTestId("list-heading")).toBeFocused();
    await expect(page.getByTestId("list-heading")).toBeInViewport();
    // pending: the bar's own progress line
    await expect(page.getByTestId("bar-pending-line")).toHaveClass(/progress-line/);
    release();
    await expect(page.getByTestId("bar-pending-line")).not.toHaveClass(/progress-line/);
    const after = await page.locator("li[data-rank]").evaluateAll((els) => els.map((e) => e.getAttribute("data-cbsa")));
    const notice = page.getByTestId("results-notice");
    await expect(notice).toHaveText(new RegExp(`^${ps.results_updated.replace("{change}", ".+")}`));
    if (after.slice(0, 3).join() !== before.slice(0, 3).join()) {
      await expect(notice).toContainText(ps.results_new_top.split("{a}")[0]);
    }
    await expect(page.getByTestId("results-live")).toHaveText((await notice.innerText()).trim());
    // the visible line goes after six seconds; the live region keeps its words
    await expect(notice).toHaveText("", { timeout: 8000 });
  });

  test("the sheet's summary row closes it onto 'I'm a' (F19); close and Escape only close (F05)", async ({ page }) => {
    test.skip(width(page) >= 1120, "the sheet is below the desk");
    await home(page);
    await openSheet(page);
    await page.keyboard.press("Escape");
    await expect(page.locator("dialog[open]")).toHaveCount(0);
    await expect(page.getByTestId("bottom-bar").getByRole("button", { name: "Adjust your search" })).toBeFocused();
    await openSheet(page);
    const summary = page.getByTestId("sheet-summary");
    expect((await summary.boundingBox())!.height).toBeGreaterThanOrEqual(44);
    await summary.click();
    await expect(page.locator("dialog[open]")).toHaveCount(0);
    await expect(page.getByTestId("self-sex")).toBeFocused();
    await expect(page.getByTestId("self-sex")).toBeInViewport();
  });

  test("choosing your race re-orders the list with no request, and says so (F13)", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    const calls: string[] = [];
    page.on("request", (r) => { if (r.url().includes("/api/rank")) calls.push(r.url()); });
    await home(page);
    await openRailGroup(page, "Sharpen compatibility");
    await page.getByTestId("self-race").selectOption("black_nh");
    const said = ps.results_updated.replace("{change}", ps.results_change_race);
    await expect(page.getByTestId("results-live")).toHaveText(new RegExp(`^${said}`));
    await expect(page.getByTestId("results-notice")).toHaveText(new RegExp(`^${said}`));
    await page.getByTestId("self-edu").selectOption("graduate");
    await expect(page.getByTestId("results-live")).toHaveText(
      new RegExp(`^${ps.results_updated.replace("{change}", ps.results_change_education)}`));
    expect(calls).toEqual([]);
    // nothing about you is kept in sessionStorage
    const keys = await page.evaluate(() => Object.keys(sessionStorage));
    expect(keys.filter((k) => k !== "dsa_place")).toEqual([]);
  });

  test("'I'm a' flips 'Looking for' only while it is untouched, and says so (F20)", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await home(page);
    // untouched: a woman looking for men who becomes a man now looks for women
    await page.getByTestId("self-sex").selectOption("male");
    await expect(page.getByTestId("seek-sex")).toHaveValue("female");
    await expect(page.getByTestId("results-live")).toHaveText(
      new RegExp(`^(${ps.sought_flipped.replace("{sought}", "Women")}|${ps.results_updated.split("{")[0]})`));
    // touched: set it back to men by hand, then change "I'm a" — no flip
    await page.getByTestId("seek-sex").selectOption("male");
    await page.getByTestId("self-sex").selectOption("female");
    await page.getByTestId("self-sex").selectOption("male");
    await expect(page.getByTestId("seek-sex")).toHaveValue("male");
  });

  test("an info box opens on click or Enter, not on focus; Escape closes it and keeps focus (F17)", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await home(page);
    const row = await expandRow(page, 4);
    const btn = row.getByRole("button", { name: ps.balance_info_label });
    await btn.focus();
    await page.waitForTimeout(200);
    await expect(page.getByTestId("info-tip-note")).toHaveCount(0);
    await page.keyboard.press("Enter");
    const note = page.getByTestId("info-tip-note");
    await expect(note).toBeVisible();
    // the note never covers its own tile
    const tile = (await row.getByTestId("balance-tally").locator("xpath=ancestor::section[1]").boundingBox())!;
    const box = (await note.boundingBox())!;
    const overlaps = box.y < tile.y + tile.height && box.y + box.height > tile.y
      && box.x < tile.x + tile.width && box.x + box.width > tile.x;
    expect(overlaps).toBe(false);
    await page.keyboard.press("Escape");
    await expect(note).toHaveCount(0);
    await expect(btn).toBeFocused();
  });

  test("the phone menu closes on Escape and on a click outside, focus back on its button (F28)", async ({ page }) => {
    test.skip(width(page) >= 640, "the menu is the phone's");
    await page.goto("/");
    const btn = page.getByTestId("menu-button");
    await btn.click();
    await expect(btn).toHaveAttribute("aria-expanded", "true");
    await page.keyboard.press("Escape");
    await expect(btn).toHaveAttribute("aria-expanded", "false");
    await expect(btn).toBeFocused();
    await btn.click();
    await expect(btn).toHaveAttribute("aria-expanded", "true");
    await page.mouse.click(200, 700);
    await expect(btn).toHaveAttribute("aria-expanded", "false");
    await expect(btn).toBeFocused();
  });

  test("the way back keeps the visitor's place: back link and browser Back (F18)", async ({ page }) => {
    await home(page);
    await page.getByTestId("show-all").click();
    const rows = page.locator("li[data-rank]");
    const n = await rows.count();
    const last = page.locator(`li[data-rank="${n}"]`);
    const slug = await last.getAttribute("data-slug");
    await last.locator("h3 a").click();
    await expect(page).toHaveURL(new RegExp(`/city/${slug}`));
    // nothing about you in sessionStorage: only the place
    const stored = await page.evaluate(() => Object.fromEntries(Object.entries(sessionStorage)));
    expect(Object.keys(stored)).toEqual(["dsa_place"]);
    expect(Object.keys(JSON.parse(stored.dsa_place)).sort()).toEqual(["cbsa", "from", "to", "visible"]);
    await page.getByTestId("back-to-results").click();
    await expect(page).toHaveURL(/\/(\?.*)?$/);
    await expect(rows).toHaveCount(n);
    await expect(last).toBeInViewport();
    // and the browser's own Back
    await last.locator("h3 a").click();
    await expect(page).toHaveURL(new RegExp(`/city/${slug}`));
    await page.goBack();
    await expect(rows).toHaveCount(n);
    await expect(last).toBeInViewport();
  });

  test("focus never hides under the bar; the bar comes before the list (F27)", async ({ page }) => {
    test.skip(width(page) >= 1120, "the bar is below the desk");
    await home(page);
    await page.mouse.wheel(0, 1600);
    await expect(page.getByTestId("bottom-bar")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.style.scrollPaddingBottom)).toBe("88px");
    const order = await page.evaluate(() => {
      const bar = document.querySelector('[data-testid="bottom-bar"]')!;
      const list = document.querySelector('[data-testid="ranked-list"]')!;
      return bar.compareDocumentPosition(list) & Node.DOCUMENT_POSITION_FOLLOWING;
    });
    expect(order).toBeTruthy();
  });

  test("search fields carry the site's own Clear; the age token names its text (F35, F37)", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await home(page);
    await expect(page.getByTestId("age-token")).toHaveAccessibleName("Their age 28 – 40");
    const find = page.getByTestId("find-in-results");
    await find.fill("Aus");
    const clear = find.locator("xpath=..").getByRole("button", { name: ps.clear });
    await expect(clear).toBeVisible();
    const b = (await clear.boundingBox())!;
    expect(b.width).toBeGreaterThanOrEqual(44);
    expect(b.height).toBeGreaterThanOrEqual(44);
    await clear.click();
    await expect(find).toHaveValue("");
    await expect(find).toBeFocused();
  });
});

test.describe("trust (F)", () => {
  test("an ⓘ beside 'Optional' explains where the details go, on demand, and links to Privacy (F10b)", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await home(page);
    if (width(page) < 1120) {
      await page.mouse.wheel(0, 1600);
      await page.getByTestId("bottom-bar").getByRole("button", { name: "Adjust your search" }).click();
    }
    const scope = width(page) < 1120 ? page.locator("dialog[open]") : page.getByTestId("rail");
    const btn = scope.getByRole("button", { name: ps.sharpen_info_label });
    await expect(btn).toHaveCount(1);
    // on demand only: nothing shows until it is asked for
    await expect(page.getByTestId("sharpen-info-note")).toHaveCount(0);
    await btn.click();
    const note = page.getByTestId("sharpen-info-note");
    await expect(note).toContainText(ps.sharpen_info);
    await expect(note.getByRole("link", { name: ps.sharpen_info_link })).toHaveAttribute("href", "/privacy");
  });

  test("Privacy says the details never leave the browser; How it works uses the registry's account (F10a, F11)", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await page.goto("/privacy");
    const priv = (await page.locator("main").innerText()).replace(/\s+/g, " ");
    expect(priv).toContain("Your own sex, education and race or ethnicity never leave your browser. "
      + "Our server sends the figures for every combination of them, and your browser shows the one "
      + "that fits you, so we never learn which one that is.");
    await page.goto("/about");
    const about = (await page.locator("main").innerText()).replace(/\s+/g, " ");
    expect(about).toContain(ps.match_how.replace(/\s+/g, " "));
    expect(about).not.toContain("racial/ethnic pairing actually occurs");
  });
});

test.describe("compare (G)", () => {
  test("a judged Edge names the city and the size of its lead; others keep the dash and the sign (F07)", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await page.goto("/compare/austin-texas/provo-utah");
    const table = page.getByTestId("compare-table");
    await expect(table).toBeVisible();
    test.skip(width(page) < 640, "the Edge column is the table's, from 640px");
    const cells = await table.locator("[data-diff-for]").evaluateAll((tds) => tds.map((td) => ({
      id: td.getAttribute("data-diff-for"), edge: td.getAttribute("data-edge"),
      text: (td as HTMLElement).innerText.replace(/\s+/g, " ").trim(),
      value: td.querySelector("[data-diff-value]")?.textContent?.trim() ?? "" })));
    let judged = 0;
    for (const c of cells) {
      if (c.edge === "1" || c.edge === "-1") {
        judged++;
        const by = c.id === "rank" ? ps.compare_edge_places.split("{n}")[0] : ps.compare_edge_by.split("{diff}")[0];
        expect(c.value, `${c.id}`).toMatch(new RegExp(`^${by}[$\\d]`));
        expect(c.value).not.toMatch(/[+−]/);
        // a screen reader hears "Austin, by …"
        await expect(table.locator(`[data-diff-for="${c.id}"]`)).toHaveAccessibleName(
          c.edge === "1" ? /^Austin ?, by / : /^Provo ?, by /);
      } else if (c.edge === "0") {
        expect(c.text.startsWith("—")).toBe(true);
      }
    }
    expect(judged).toBeGreaterThan(3);
    await expect(page.getByTestId("diff-legend")).toHaveText(ps.compare_edge_note);
  });

  test("a city below the floor reads 'Not ranked' on the five ranked rows (F24); Matches is the row's name (F21)", async ({ page, request }) => {
    const meta = await fetchMeta(request);
    const ps = meta.policy_strings;
    await page.goto("/compare/austin-texas/eagle-pass-texas");
    const table = page.getByTestId("compare-table");
    await expect(table).toBeVisible();
    for (const label of ["Spot in your results", ps.overall_score_label, meta.features.pool_size.display_name,
                         meta.features.match_propensity.display_name, meta.features.pool_balance.display_name]) {
      const row = table.getByRole("row").filter({ has: page.getByRole("rowheader", { name: label }) });
      await expect(row.getByRole("cell").nth(1), label).toHaveText(ps.compare_not_ranked);
    }
    expect(meta.features.pool_size.display_name).toBe("Matches");
    await expect(table).not.toContainText("Not covered");
    await expect(table).not.toContainText("People who match");
  });

  test("the starting-search note is neutral, not a warning (F23)", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await page.goto("/compare/austin-texas/provo-utah");
    const note = page.getByTestId("default-profile-note");
    await expect(note).toContainText(ps.compare_default_note.split("{search}")[0]);
    const st = await note.evaluate((el) => {
      const cs = getComputedStyle(el);
      const v = (n: string) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
      const hex = (c: string) => "#" + (c.match(/\d+/g) ?? []).slice(0, 3).map((x) => Number(x).toString(16).padStart(2, "0")).join("").toUpperCase();
      return { bg: hex(cs.backgroundColor), fg: hex(cs.color), border: cs.borderTopWidth, sunken: v("--sunken").toUpperCase(), ink2: v("--ink-2").toUpperCase() };
    });
    expect(st.bg).toBe(st.sunken);
    expect(st.fg).toBe(st.ink2);
    expect(st.border).toBe("0px");
  });

  test("same-sex: the Matches row carries the note, chosen in the browser (F01)", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await seedAboutYou(page, { sex: "male" });
    await page.goto(`/compare/austin-texas/provo-utah${SAME_SEX_QS}`);
    await expect(page.getByTestId("compare-table").getByTestId("same-sex-note"))
      .toHaveText(ps.same_sex_pool_note.replace("{sought_one}", "man").replace("{sought}", "men"));
    const html = await (await request.get(`/compare/austin-texas/provo-utah${SAME_SEX_QS}`)).text();
    expect(html).not.toContain('data-testid="same-sex-note"');
  });

  test("opposite-sex: no note on Compare", async ({ page }) => {
    await seedAboutYou(page, { sex: "female" });
    await page.goto(`/compare/austin-texas/provo-utah${SAME_SEX_QS}`);
    await expect(page.getByTestId("compare-table")).toBeVisible();
    await expect(page.getByTestId("same-sex-note")).toHaveCount(0);
  });
});

test.describe("compare on the real build (P6_REAL_BASE)", () => {
  test.skip(!REAL, "needs the real build's site");
  const edgeCell = (page: Page, id: string) => page.locator(`[data-diff-for="${id}"]`);
  test("Austin–Denver: matches '▲ Denver' by 31,802; the spot by 2 places", async ({ page }) => {
    test.skip(width(page) < 640, "the Edge column");
    await page.goto(`${REAL}/compare/austin-texas/denver-colorado`);
    await expect(edgeCell(page, "pool")).toHaveAttribute("data-edge", "-1");
    await expect(edgeCell(page, "pool")).toContainText("Denver");
    await expect(edgeCell(page, "pool").locator("[data-diff-value]")).toHaveText("by 31,802");
    // (the accessible-name algorithm sets a space before the visually
    // hidden comma; speech is the same)
    await expect(edgeCell(page, "pool")).toHaveAccessibleName(/^Denver ?, by 31,802$/);
    await expect(edgeCell(page, "rank").locator("[data-diff-value]")).toHaveText("by 2 places");
  });
  test("Austin–Abilene: rent '▲ Abilene' by $526", async ({ page }) => {
    test.skip(width(page) < 640, "the Edge column");
    await page.goto(`${REAL}/compare/austin-texas/abilene-texas`);
    await expect(edgeCell(page, "rent_1br")).toHaveAttribute("data-edge", "-1");
    await expect(edgeCell(page, "rent_1br")).toContainText("Abilene");
    await expect(edgeCell(page, "rent_1br").locator("[data-diff-value]")).toHaveText("by $526");
  });
});

test.describe("city and stat pages, sharing, the footer (H)", () => {
  test("the city page leads with the score: its heading in the first screen at 1440x900 (F16)", async ({ page }) => {
    test.skip(width(page) !== 1440, "the desk");
    await page.goto("/city/austin-texas");
    const h = page.getByTestId("ranked-card").getByRole("heading", { level: 2 });
    await expect(h).toBeVisible();
    expect((await h.boundingBox())!.y).toBeLessThan(900);
    // the photo band (or the artwork) comes after the score card
    const card = (await page.getByTestId("ranked-card").boundingBox())!;
    const face = page.locator('[data-testid="city-photo"], [data-testid="city-art"]').first();
    expect((await face.boundingBox())!.y).toBeGreaterThan(card.y + card.height);
  });

  test("the score card carries the metro's cautions under its matches line (F08)", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await page.goto("/city/huntington-west-virginia");
    await expect(page.getByTestId("ranked-card").getByTestId("flag-captions")).toHaveText(ps.low_allocation_purity);
    await page.goto("/city/austin-texas");
    await expect(page.getByTestId("ranked-card")).toBeVisible();
    await expect(page.getByTestId("flag-captions")).toHaveCount(0);
  });

  test("same-sex on the city page: the note and the balance caption, chosen in the browser (F01)", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    const html = await (await request.get(`/city/austin-texas${SAME_SEX_QS}`)).text();
    expect(html).not.toContain('data-testid="same-sex-note"');
    await seedAboutYou(page, { sex: "male" });
    await page.goto(`/city/austin-texas${SAME_SEX_QS}`);
    const card = page.getByTestId("ranked-card");
    await expect(card.getByTestId("same-sex-note")).toHaveText(
      ps.same_sex_pool_note.replace("{sought_one}", "man").replace("{sought}", "men"));
    await card.getByRole("button", { name: ps.balance_info_label }).click();
    await expect(page.getByTestId("info-tip-note")).toHaveText(ps.balance_caption_same_sex);
  });

  test("a city below the floor says so, with the floor (F24); the crime boxes are named (F26)", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    await page.goto("/city/eagle-pass-texas");
    await expect(page.getByTestId("below-floor")).toHaveText(ps.city_below_floor.replace("{city}", "Eagle Pass"));
    await page.goto("/city/austin-texas");
    await expect(page.getByRole("button", { name: "About the violent crime figure" })).toHaveCount(1);
    await expect(page.getByRole("button", { name: "About the property crime figure" })).toHaveCount(1);
  });

  test("a band showing a place elsewhere in the metro names it (F29)", async ({ page, request }) => {
    test.skip(!photoOnDisk("cities/killeen-texas.jpg"), "no photographs on this checkout");
    const ps = (await fetchMeta(request)).policy_strings;
    await page.goto("/city/killeen-texas");
    await expect(page.getByTestId("photo-place")).toHaveText(
      ps.photo_place_caption.replace("{place}", "Belton").replace("{city}", "Killeen"));
    await page.goto("/city/austin-texas");
    await expect(page.getByTestId("photo-place")).toHaveCount(0);
  });

  test("the city page's HTML carries no map geometry and only its own metro (F32)", async ({ request, page }) => {
    const html = await (await request.get("/city/austin-texas")).text();
    // icons are short paths; a state outline is hundreds of characters
    expect(html.match(/<path d="[^"]{300,}"/g) ?? []).toEqual([]);
    expect((html.match(/"description\\?":/g) ?? []).length).toBeLessThanOrEqual(2);
    await page.goto("/city/austin-texas");
    const map = page.getByTestId(width(page) < 640 ? "locator-map-thumb" : "locator-map");
    await expect(map).toHaveAttribute("src", /^\/map\/12420\.svg$/);
  });

  test("the stat pages' sort controls are the segmented control (F33)", async ({ page }) => {
    await page.goto("/stats/rent_1br");
    const sort = page.getByTestId("stat-sort");
    await expect(sort).toHaveAttribute("role", "radiogroup");
    const on = sort.getByRole("radio", { checked: true });
    await expect(on).toHaveCount(1);
    // white with the --ink-2 border (1.5px, which a 1x screen draws as 1px)
    const style = await on.evaluate((el) => ({ border: parseFloat(getComputedStyle(el).borderTopWidth),
      color: getComputedStyle(el).borderTopColor, bg: getComputedStyle(el).backgroundColor }));
    expect(style.border).toBeGreaterThanOrEqual(1);
    expect(style.color).toBe("rgb(90, 82, 87)");
    expect(style.bg).toBe("rgb(255, 255, 255)");
    await page.goto("/stats/political_lean");
    await expect(page.getByTestId("lean-sort").getByRole("radio")).toHaveText(["Name", "Democratic share", "Republican share"]);
    await expect(page.getByTestId("lean-sort").getByRole("radio", { name: "Name" })).toHaveAttribute("aria-checked", "true");
  });

  test("the stat photo keeps its own shape, no band beside it (F33)", async ({ page }) => {
    test.skip(!photoOnDisk("stats/rent_1br.webp") && !photoOnDisk("stats/rent_1br.jpg"), "no photographs on this checkout");
    await page.goto("/stats/rent_1br");
    const img = page.getByTestId("stat-photo");
    const r = await img.evaluate((el) => {
      const i = el as HTMLImageElement;
      const b = i.getBoundingClientRect();
      return { shown: b.width / b.height, natural: i.naturalWidth / i.naturalHeight, h: b.height };
    });
    expect(Math.abs(r.shown - r.natural)).toBeLessThan(0.02);
    expect(r.h).toBeLessThanOrEqual(380.5);
  });

  test("a shared results link has its own title, URL and preview (F31)", async ({ page, request }) => {
    const ps = (await fetchMeta(request)).policy_strings;
    const r = await request.post(`${E2E_API}/v1/rank`, { data: {
      self: { age: 30 }, seeking: { sex: "male", age: [28, 40], marital: ["never_married", "previously_married"] } } });
    const link = (await r.json()).permalink as string;
    await page.goto(link);
    await expect(page).toHaveTitle("Top cities for single men, 28–40 · Dating Stats Atlas");
    expect(await page.locator('meta[property="og:url"]').getAttribute("content")).toMatch(new RegExp(`${link.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`));
    await expect(page.locator('meta[property="og:description"]')).toHaveAttribute("content", ps.home_subtitle);
    await expect(page.locator('meta[property="og:image"]')).toHaveAttribute("content", /\/og\/home\.png$/);
    await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute("content", "summary_large_image");
    // a home URL with a search too; the bare home keeps the site's title
    await page.goto("/?self_age=30&sex=female&age=25-35&marital=never");
    await expect(page).toHaveTitle("Top cities for single women, 25–35 · Dating Stats Atlas");
    await page.goto("/");
    await expect(page).toHaveTitle(ps.title_site);
    await expect(page.locator('meta[property="og:image"]')).toHaveAttribute("content", /\/og\/home\.png$/);
  });

  test("city pages preview with their 1200x630 crop (F31)", async ({ page, request }) => {
    test.skip(!photoOnDisk("cities/og/austin-texas.jpg"), "no photographs on this checkout");
    await page.goto("/city/austin-texas");
    const og = await page.locator('meta[property="og:image"]').getAttribute("content");
    expect(og).toMatch(/\/cities\/og\/austin-texas\.jpg$/);
    await expect(page.locator('meta[property="og:image:width"]')).toHaveAttribute("content", "1200");
    await expect(page.locator('meta[property="og:image:height"]')).toHaveAttribute("content", "630");
    const img = await request.get(new URL(og!).pathname);
    expect(img.ok()).toBe(true);
  });

  test("a short page ends on its footer (F36)", async ({ page }) => {
    await page.goto("/no-such-page");
    const footer = (await page.locator("footer").boundingBox())!;
    const docH = await page.evaluate(() => document.documentElement.scrollHeight);
    expect(Math.round(footer.y + footer.height)).toBe(docH);
    expect(docH).toBeGreaterThanOrEqual(page.viewportSize()!.height);
  });
});

test.describe("photographs (A, I)", () => {
  test("card #1 is fetched first, #2-#3 lazily; every card and band carries its sized copies (F03)", async ({ page }) => {
    test.skip(!photoOnDisk("cities/new-york-new-york.jpg") && !photoOnDisk("cities/new-york-new-york.png"),
      "no photographs on this checkout");
    await home(page);
    const imgs = page.getByTestId("card-photo");
    await expect(imgs).toHaveCount(3);
    await expect(imgs.nth(0)).toHaveAttribute("fetchpriority", "high");
    await expect(imgs.nth(1)).toHaveAttribute("loading", "lazy");
    await expect(imgs.nth(2)).toHaveAttribute("loading", "lazy");
    for (let i = 0; i < 3; i++) {
      await expect(imgs.nth(i)).toHaveAttribute("srcset", /\/cities\/w\/[a-z-]+-\d+\.webp \d+w/);
      await expect(imgs.nth(i)).toHaveAttribute("width", /^\d+$/);
    }
    await page.goto("/city/austin-texas");
    const band = page.getByTestId("city-photo").locator("img");
    await expect(band).toHaveAttribute("srcset", /\/cities\/w\/austin-texas-\d+\.webp/);
    await expect(band).toHaveAttribute("fetchpriority", "high");
  });
});
