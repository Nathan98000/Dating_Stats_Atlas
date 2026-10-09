import { readFileSync } from "fs";
import path from "path";
import { describe, expect, it } from "vitest";

/** Phase 5: the new tokens' contrast, read from globals.css itself (so a
 * changed token is measured, not a copy of it). Control boundaries and
 * selected states need 3:1 (WCAG 1.4.11); text needs 4.5:1. */

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

const css = readFileSync(path.resolve(__dirname, "..", "src", "app", "globals.css"), "utf8");
const root = css.slice(css.indexOf(":root {"), css.indexOf("@theme inline"));

function token(name: string): string {
  const m = root.match(new RegExp(`--${name}:\\s*(#[0-9A-Fa-f]{6})`));
  if (!m) throw new Error(`--${name} is not a hex colour in :root`);
  return m[1];
}

const PAIRS: [string, string, string, number][] = [
  // [what, foreground token, background token, minimum]
  ["control boundary on white", "line-strong", "surface", 3],
  ["control boundary on paper", "line-strong", "paper", 3],
  ["selected segment's border against its track", "ink-2", "sunken", 3],
  ["plus chip text on its fill", "good-strong", "good-soft", 4.5],
  ["minus chip text on its fill", "poor-strong", "poor-soft", 4.5],
  ["warning text on its fill", "warning", "warning-soft", 4.5],
  ["warning text on white", "warning", "surface", 4.5],
  ["error text on its fill", "error", "error-soft", 4.5],
  ["error text on white", "error", "surface", 4.5],
  ["medallion rank on highlight", "ink", "highlight", 4.5],
  ["unselected segment text on its track", "ink-2", "sunken", 4.5],
  ["hint text on the open row", "ink-3", "hover", 4.5],
  ["selected chip text on tint", "accent-hover", "tint", 4.5],
  ["selected chip border on white", "accent", "surface", 3],
  // Phase 6: the line under the count after a change ("New top three: …")
  // and the same-sex note, on the page; the cautions and the bars' words on
  // an open row's or card's detail
  ["the 'New top three' line on paper", "ink-2", "paper", 4.5],
  ["a caution caption on the open row", "ink-2", "hover", 4.5],
];

describe("Phase 5 tokens hold their contrast", () => {
  for (const [what, fg, bg, min] of PAIRS) {
    it(`${what} (--${fg} on --${bg}) is at least ${min}:1`, () => {
      const c = contrast(token(fg), token(bg));
      expect(c, `${token(fg)} on ${token(bg)} = ${c.toFixed(2)}:1`).toBeGreaterThanOrEqual(min);
    });
  }

  it("--line-strong would not do as the selected segment's border (why it is --ink-2)", () => {
    expect(contrast(token("line-strong"), token("sunken"))).toBeLessThan(3);
  });

  it("prints the measured table for the report", () => {
    const lines = PAIRS.map(([what, fg, bg]) =>
      `${what.padEnd(46)} ${contrast(token(fg), token(bg)).toFixed(2)}:1`);
    console.log(lines.join("\n"));
    expect(lines.length).toBe(PAIRS.length);
  });
});
