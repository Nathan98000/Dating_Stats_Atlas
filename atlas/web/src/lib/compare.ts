/** The compare table's arithmetic on displayed values (Phase 2f item 6,
 * ADR 0007): a difference is plain subtraction of the two DISPLAYED values,
 * parsed back from the display strings themselves, so it equals what the
 * visitor sees by construction and nothing is recomputed from raw values.
 * Phase 5's Edge column names the city a difference favours. */

export type Edge = -1 | 0 | 1;

/** A displayed value back to the number it shows: commas and dollar signs
 * stripped, format_pop's "1.3 million" expanded. */
export function parseDisplayed(s: string): number {
  const flat = s.replace(/,/g, "").replace(/\$/g, "");
  const n = parseFloat(flat);
  return /million/.test(flat) ? n * 1_000_000 : n;
}

/** Which city a displayed difference favours: 1 the left, -1 the right,
 * 0 none — no judgement (grey: population, a pillar set to Not much, no
 * direction), a value missing, or no difference. The decision is the one
 * the colours made before Phase 5: d × direction > 0 favours the left. */
export function edgeOf(a: string | undefined, b: string | undefined, direction: number,
                       grey = false): Edge {
  if (a === undefined || b === undefined || grey || !direction) return 0;
  const d = parseDisplayed(a) - parseDisplayed(b);
  if (!Number.isFinite(d) || d === 0) return 0;
  return d * direction > 0 ? 1 : -1;
}
