/** Phase 2f item 1: tone -> presentation, all five tones in one place.
 * The lit indicator segment takes the same colour as its label. Colour
 * is never the only signal — the band phrase carries the meaning (WCAG
 * 1.4.1) — and no tone class may sit on the tint background, where the
 * light pair measures below AA (the contrast test pins this). */
import type { Tone } from "./types";

export const TONE_TEXT: Record<Tone, string> = {
  good_strong: "text-good-strong",
  good: "text-good",
  neutral: "text-ink-2",
  poor: "text-poor",
  poor_strong: "text-poor-strong",
};

export const TONE_SEG: Record<Tone, string> = {
  good_strong: "var(--good-strong)",
  good: "var(--good)",
  neutral: "var(--ink-3)",
  poor: "var(--poor)",
  poor_strong: "var(--poor-strong)",
};

export function toneText(tone: string | undefined): string {
  return TONE_TEXT[(tone ?? "neutral") as Tone] ?? "text-ink-2";
}

export function toneSeg(tone: string | undefined): string {
  return TONE_SEG[(tone ?? "neutral") as Tone] ?? "var(--ink-3)";
}
