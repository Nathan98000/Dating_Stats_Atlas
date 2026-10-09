import { expect, test, type Page } from "@playwright/test";
import { expandRow, fetchMeta, seedAboutYou } from "./helpers";

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
