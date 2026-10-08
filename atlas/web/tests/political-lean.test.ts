import fs from "fs";
import path from "path";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { sortLean, type LeanRow } from "../src/components/lean-list";
import { PoliticalLeanCard, PoliticalLeanCell } from "../src/components/political-lean";
import type { Meta, PoliticalLeanBlock } from "../src/lib/types";

/** Phase 4d (ADR 0019): political lean in the browser. The colours are
 * read from the site's own tokens and held to AA on the backgrounds the
 * bar and its key sit on; the stat list sorts by name unless the visitor
 * asks for a party's share; the card and the compare cell render the
 * API's words — and "Not available" for a metro the returns cannot
 * cover — without computing anything. */

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: unknown }) =>
    createElement("a", { href, ...rest }, children as never),
}));

// WCAG relative luminance and contrast (the tones test's formula)
function channel(v: number): number {
  const s = v / 255;
  return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
}
function luminance(hex: string): number {
  const n = parseInt(hex.slice(1), 16);
  return 0.2126 * channel((n >> 16) & 255) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255);
}
function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

const CSS = fs.readFileSync(path.join(__dirname, "..", "src", "app", "globals.css"), "utf8");
const token = (name: string): string => {
  const m = CSS.match(new RegExp(`--${name}:\\s*(#[0-9A-Fa-f]{6})`));
  if (!m) throw new Error(`no --${name} token`);
  return m[1];
};

describe("the bar's colours hold AA where they sit (white cards, paper page)", () => {
  const BG = { surface: "#FFFFFF", paper: "#FDF7F3" };
  for (const [name, min] of [["dem", 4.5], ["rep", 4.5], ["lean-other", 3]] as const) {
    for (const [bg, hex] of Object.entries(BG)) {
      it(`--${name} on ${bg} is at least ${min}:1`, () => {
        const c = contrast(token(name), hex);
        expect(c, `--${name} ${token(name)} on ${bg} = ${c.toFixed(2)}:1`).toBeGreaterThanOrEqual(min);
      });
    }
  }

  // Phase 5: the sex colours (--male, --female) were retired with the
  // balance tally; the party colours stay apart from the rest
  it("keeps the party colours apart from the tones and the accent", () => {
    const others = ["good", "poor", "good-strong", "poor-strong", "accent"]
      .map((n) => token(n).toUpperCase());
    for (const n of ["dem", "rep", "lean-other"]) {
      expect(others).not.toContain(token(n).toUpperCase());
    }
  });
});

const ROWS: LeanRow[] = [
  { slug: "a", name: "Akron, OH", dem: "50%", rep: "49%", dem_share: 0.5038, rep_share: 0.4865 },
  { slug: "b", name: "Boise, ID", dem: "35%", rep: "62%", dem_share: 0.35, rep_share: 0.62 },
  { slug: "c", name: "Chicago, IL", dem: "58%", rep: "40%", dem_share: 0.58, rep_share: 0.40 },
  { slug: "d", name: "Dayton, OH", dem: "35%", rep: "63%", dem_share: 0.35, rep_share: 0.63 },
];

describe("the stat list's order", () => {
  it("defaults to the names, never either party's top", () => {
    expect(sortLean(ROWS, "name").map((r) => r.slug)).toEqual(["a", "b", "c", "d"]);
  });
  it("sorts by either party's share, highest first, a tie keeping name order", () => {
    expect(sortLean(ROWS, "dem").map((r) => r.slug)).toEqual(["c", "a", "b", "d"]);
    expect(sortLean(ROWS, "rep").map((r) => r.slug)).toEqual(["d", "b", "a", "c"]);
    expect(ROWS.map((r) => r.slug)).toEqual(["a", "b", "c", "d"]);
  });
});

const META = {
  features: {
    political_lean: {
      display_name: "Political lean",
      unit: "2024 presidential vote, whole metro area",
      definition: "How the metro area voted in the 2024 presidential election.",
      stat_page_name: null,
    },
  },
  stat_pages: ["political_lean"],
  policy_strings: { stat_page_link: "See all cities by {name}" },
} as unknown as Meta;

const AVAILABLE: PoliticalLeanBlock = {
  available: true,
  text: "57% Democratic · 42% Republican",
  bar_label: "Democratic 57%, Everyone else 1%, Republican 42%",
  segments: [
    { key: "dem", label: "Democratic", display: "57%", width: 56.65 },
    { key: "other", label: "Everyone else", display: "1%", width: 1.41 },
    { key: "rep", label: "Republican", display: "42%", width: 41.94 },
  ],
  share: { dem: 0.566482, rep: 0.419414 },
};
const MISSING: PoliticalLeanBlock = { available: false, note: "Not available" };

describe("the city card and the compare cell", () => {
  it("show the API's text, the caption, the bar in party order with every segment named", () => {
    const html = renderToStaticMarkup(createElement(PoliticalLeanCard, { block: AVAILABLE, meta: META }));
    expect(html).toContain("57% Democratic · 42% Republican");
    expect(html).toContain("2024 presidential vote, whole metro area");
    expect(html).toContain('aria-label="Democratic 57%, Everyone else 1%, Republican 42%"');
    expect([...html.matchAll(/data-segment="(\w+)"/g)].map((m) => m[1])).toEqual(["dem", "other", "rep"]);
    expect([...html.matchAll(/data-key="(\w+)"/g)].map((m) => m[1])).toEqual(["dem", "other", "rep"]);
    for (const name of ["Democratic", "Everyone else", "Republican"]) expect(html).toContain(`${name}</span>`);
    expect(html).toContain('href="/stats/political_lean"');
    expect(html).toContain("See all cities by political lean");
  });

  it("say Not available, with no bar and no number, where the returns cannot cover the metro", () => {
    const card = renderToStaticMarkup(createElement(PoliticalLeanCard, { block: MISSING, meta: META }));
    expect(card).toContain("Not available");
    expect(card).not.toContain("lean-bar");
    expect(card).not.toMatch(/\d+%/);
    const cell = renderToStaticMarkup(createElement(PoliticalLeanCell, { block: MISSING }));
    expect(cell).toContain("Not available");
    const shown = renderToStaticMarkup(createElement(PoliticalLeanCell, { block: AVAILABLE }));
    expect(shown).toContain("57% Democratic · 42% Republican");
  });
});
