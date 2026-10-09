/** The compare table's arithmetic on displayed values (Phase 2f item 6,
 * ADR 0007): a difference is plain subtraction of the two DISPLAYED values,
 * parsed back from the display strings themselves, so it equals what the
 * visitor sees by construction and nothing is recomputed from raw values.
 * Phase 5's Edge column names the city a difference favours; since Phase 6
 * (F07, ADR 0007 amended) it also says by how much — the absolute value of
 * the same subtraction — where the plain signed difference read against
 * its arrow ("▲ Abilene +$526" for the cheaper city). */

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

function formatted(d: number, decimals: number, dollar: boolean): string {
  return `${dollar ? "$" : ""}${d.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
}

/** The plain difference of two displayed values, signed: "+31,802",
 * "−$526" (rows the site doesn't judge show it). */
export function signedDiff(a: string, b: string, decimals: number, dollar = false): string {
  const d = parseDisplayed(a) - parseDisplayed(b);
  const sign = d > 0 ? "+" : d < 0 ? "−" : "";
  return sign + formatted(Math.abs(d), decimals, dollar);
}

/** The size of a lead (Phase 6, F07): the absolute value of the same plain
 * subtraction, formatted as the values are ("31,802", "$339", "2.6") —
 * filled into the registry's compare_edge_by ("by {diff}"). */
export function leadOf(a: string, b: string, decimals: number, dollar = false): string {
  return formatted(Math.abs(parseDisplayed(a) - parseDisplayed(b)), decimals, dollar);
}
