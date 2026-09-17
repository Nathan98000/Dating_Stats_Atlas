/** Item 5's test matrix: the intended city must sit in the TOP THREE for
 * every query, through the ONE shared matcher both the header search and
 * the compare pickers now use. The bug it pins: the compare pickers used
 * to filter with an unranked `.includes()` and truncate in alphabetical
 * index order, so "new york" served seven upstate metros and dropped New
 * York itself — confirmed failing against that logic before the fix (the
 * `legacyComparePickerFilter` case below reproduces it verbatim). */
import { describe, expect, it } from "vitest";
import index from "../src/data/search-index.json";
import { searchCities, type CityEntry } from "../src/lib/search";

const INDEX = index as CityEntry[];

const MATRIX: [string, string][] = [
  ["new york", "new-york-new-york"],
  ["nyc", "new-york-new-york"],
  ["ny", "new-york-new-york"],
  ["new orleans", "new-orleans-louisiana"],
  ["new haven", "new-haven-connecticut"],
  ["san francisco", "san-francisco-california"],
  ["san fran", "san-francisco-california"],
  ["sf", "san-francisco-california"],
  ["dfw", "dallas-texas"],
  ["dallas", "dallas-texas"],
  ["the triangle", "raleigh-north-carolina"],
  ["st louis", "st-louis-missouri"],
  ["st. louis", "st-louis-missouri"],
  ["washington", "washington-district-of-columbia"],
  ["dc", "washington-district-of-columbia"],
  ["provo", "provo-utah"],
  ["winston", "winston-salem-north-carolina"],
  ["twin cities", "minneapolis-minnesota"],
];

/** The compare pickers' pre-fix logic, verbatim: unranked includes(),
 * truncated in index order. Kept as the executable record of the bug. */
function legacyComparePickerFilter(q: string): CityEntry[] {
  const query = q.trim().toLowerCase();
  if (query.length < 2) return [];
  return INDEX
    .filter((e) => [e.f, ...e.k].some((t) => t.toLowerCase().includes(query)))
    .slice(0, 6);
}

describe("the bug, confirmed before the fix", () => {
  it('the legacy compare-picker filter drops New York for "new york"', () => {
    const got = legacyComparePickerFilter("new york").map((e) => e.s);
    // alphabetical: Albany, Binghamton, Buffalo… fill every slot
    expect(got).not.toContain("new-york-new-york");
  });
  // "the triangle" only ever worked in the header because the header
  // scored; the legacy filter happens to match it — the defect was the
  // ordering, which the case above pins
});

describe("one matcher for every city chooser", () => {
  for (const [query, slug] of MATRIX) {
    it(`"${query}" puts ${slug} in the top three`, () => {
      const top = searchCities(INDEX, query, { limit: 3 }).map((e) => e.s);
      expect(top, `top three for "${query}" were ${top.join(", ")}`)
        .toContain(slug);
    });
  }

  it("compare-picker shape: exclude and limit hold", () => {
    const got = searchCities(INDEX, "new york", {
      limit: 7,
      exclude: "new-york-new-york",
    });
    expect(got.map((e) => e.s)).not.toContain("new-york-new-york");
    expect(got.length).toBeLessThanOrEqual(7);
  });

  it("a state name alone never outranks the city that bears it", () => {
    const top = searchCities(INDEX, "washington", { limit: 3 }).map((e) => e.s);
    expect(top[0]).toBe("washington-district-of-columbia");
  });
});
