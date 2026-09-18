import { describe, expect, it } from "vitest";
import { TONE_SEG, TONE_TEXT } from "../src/lib/tones";

/** Phase 2f gate 2: the four coloured tones measured against every
 * background they actually sit on. The measured table also PINS the
 * exclusion: the light pair is below AA on the tint background, which
 * is why no tone label may ever sit on tint (nothing does today; if a
 * surface ever needs one there, it takes the strong tone and says so). */

const TONES = {
  good_strong: "#1B5E4B",
  good: "#2E7D6B",
  poor: "#B0543E",
  poor_strong: "#8A2B18",
} as const;

const BACKGROUNDS = {
  paper: "#FDF7F3", // page background (compare legend, stat pages)
  surface: "#FFFFFF", // cards and tables, where every band label sits
} as const;

const TINT = "#F7E9EE"; // banners/chips — tone labels NEVER sit here

function channel(v: number): number {
  const s = v / 255;
  return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
}

function luminance(hex: string): number {
  const n = parseInt(hex.slice(1), 16);
  return (
    0.2126 * channel((n >> 16) & 255) +
    0.7152 * channel((n >> 8) & 255) +
    0.0722 * channel(n & 255)
  );
}

export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

describe("the four tones hold AA on every background they sit on", () => {
  for (const [tone, hex] of Object.entries(TONES)) {
    for (const [bg, bgHex] of Object.entries(BACKGROUNDS)) {
      it(`${tone} on ${bg} is at least 4.5:1`, () => {
        const c = contrast(hex, bgHex);
        expect(c, `${tone} ${hex} on ${bg} ${bgHex} = ${c.toFixed(2)}:1`)
          .toBeGreaterThanOrEqual(4.5);
      });
    }
  }

  it("prints the measured table for the report", () => {
    const lines = ["tone        paper   white   tint"];
    for (const [tone, hex] of Object.entries(TONES)) {
      lines.push(
        `${tone.padEnd(12)}${contrast(hex, BACKGROUNDS.paper).toFixed(2)}:1  ` +
        `${contrast(hex, BACKGROUNDS.surface).toFixed(2)}:1  ` +
        `${contrast(hex, TINT).toFixed(2)}:1`,
      );
    }
    console.log(lines.join("\n"));
    expect(lines.length).toBe(5);
  });

  it("pins WHY tone labels never sit on tint: the light pair is below AA there", () => {
    expect(contrast(TONES.good, TINT)).toBeLessThan(4.5);
    expect(contrast(TONES.poor, TINT)).toBeLessThan(4.5);
    // and the strong pair would clear it, which is the documented escape
    // hatch if a tone ever must render on tint
    expect(contrast(TONES.good_strong, TINT)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(TONES.poor_strong, TINT)).toBeGreaterThanOrEqual(4.5);
  });

  it("the class and segment maps cover exactly the five tones", () => {
    const five = ["good_strong", "good", "neutral", "poor", "poor_strong"];
    expect(Object.keys(TONE_TEXT).sort()).toEqual([...five].sort());
    expect(Object.keys(TONE_SEG).sort()).toEqual([...five].sort());
    // neutral carries no judgement colour
    expect(TONE_TEXT.neutral).toBe("text-ink-2");
    expect(TONE_SEG.neutral).toBe("var(--ink-3)");
  });
});
