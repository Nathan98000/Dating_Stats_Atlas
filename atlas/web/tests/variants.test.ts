/** The browser selects, it never computes (m4.0.0, ADR 0018): for every
 * case the Python model emitted (scripts/gen_variant_cases.py) the
 * browser's selector returns exactly the rows atlas.model.variants
 * .select_variant returns — the same cities in the same order with the
 * same numbers — and a page's slice (the city and compare pages) selects
 * the same rows as the whole response. */
import { describe, expect, it } from "vitest";
import cases from "./variant_cases.json";
import { selectVariant, sliceVariants } from "../src/lib/variants";
import type { AboutYou } from "../src/lib/about-you";
import type { VariantResponse } from "../src/lib/types";

describe("variant selection against the Python model", () => {
  for (const c of cases.cases) {
    const resp = c.response as unknown as VariantResponse;
    for (const sel of c.selections) {
      const about = sel.about as AboutYou;
      it(`${c.name}: ${JSON.stringify(about)}`, () => {
        const got = selectVariant(resp, about);
        expect(got).toEqual(sel.expected);
        // a slice of any two ranked cities and a left-out one selects the
        // same rows, with their ranks in the whole list
        const pick = [
          ...resp.ranked.slice(-2).map((r) => r.cbsa),
          ...resp.suppressed.slice(0, 1).map((r) => r.cbsa),
        ];
        const sliced = selectVariant(sliceVariants(resp, pick), about);
        expect(sliced.ranked).toEqual(got.ranked.filter((r) => pick.includes(r.cbsa)));
        expect(sliced.suppressed).toEqual(got.suppressed.filter((r) => pick.includes(r.cbsa)));
        expect(sliced.counts).toEqual(got.counts);
      });
    }
  }

  it("covers a same-sex search, a left-out city and worst-first", () => {
    const names = cases.cases.map((c) => c.name);
    expect(names).toContain("same_sex");
    const narrow = cases.cases.find((c) => c.name === "narrow_worst_first")!;
    expect(narrow.response.suppressed.length).toBeGreaterThan(0);
    expect(narrow.response.sort).toBe("worst_first");
  });

  it("balance is the search's: every own sex selects the same blocks, sent once (m4.1.0)", () => {
    for (const c of cases.cases) {
      const resp = c.response as unknown as VariantResponse;
      expect(resp.variants).not.toHaveProperty("by_sex");
      expect(resp.variants.balance.ranked).toHaveLength(resp.ranked.length);
      expect(resp.variants.balance.suppressed).toHaveLength(resp.suppressed.length);
      const shown = (about: AboutYou) => {
        const sel = selectVariant(resp, about);
        expect(sel).not.toHaveProperty("balance_applies");
        return { words: sel.balance_words, rows: Object.fromEntries(
          [...sel.ranked, ...sel.suppressed].map((r) => [r.cbsa, r.balance])) };
      };
      // a same-sex visitor sees exactly what an opposite-sex visitor sees
      expect(shown({ sex: "male" })).toEqual(shown({ sex: "female" }));
    }
    // a man seeking men sees "N men per 100 women"
    const ss = cases.cases.find((c) => c.name === "same_sex")!;
    const sel = selectVariant(ss.response as unknown as VariantResponse, { sex: "male" });
    const shownBlocks = sel.ranked.map((r) => r.balance).filter((b) => b.available);
    expect(shownBlocks.length).toBeGreaterThan(0);
    for (const b of shownBlocks) expect(b.display).toBe(`${b.per_100} men per 100 women`);
  });

  it("on a same-sex search the visitor's race selects the race-off variant", () => {
    const ss = cases.cases.find((c) => c.name === "same_sex")!;
    const resp = ss.response as unknown as VariantResponse;
    const off = selectVariant(resp, { sex: "male" });
    for (const race of ["asian_nh", "hispanic", "black_nh"]) {
      expect(selectVariant(resp, { sex: "male", race })).toEqual(off);
    }
  });
});
