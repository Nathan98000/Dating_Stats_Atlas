import { expect, test, type Page } from "@playwright/test";
import { expandRow } from "./helpers";

/** Phase 6 (the round-3 design review of 8 October 2026, built from
 * atlas/PHASE6_PROMPT.md), run at the desk (1440×900), a laptop below the
 * breakpoint (1024×768) and a touch phone (390×844). */

const width = (page: Page) => page.viewportSize()!.width;

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
