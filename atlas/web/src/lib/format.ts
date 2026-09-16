/** Presentation-only helpers. These format numbers the API computed — they
 * never derive one. Anything requiring arithmetic (scaling, margins,
 * percentiles, contributions) arrives from the API pre-computed, usually
 * as a `display` string. */

export function fmtInt(n: number): string {
  return n.toLocaleString("en-US");
}

export function ordinal(n: number): string {
  const v = Math.round(n);
  const rem10 = v % 10;
  const rem100 = v % 100;
  const suffix =
    rem100 >= 11 && rem100 <= 13 ? "th"
    : rem10 === 1 ? "st"
    : rem10 === 2 ? "nd"
    : rem10 === 3 ? "rd"
    : "th";
  return `${v}${suffix}`;
}

export function signedPoints(v: number): string {
  return `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(1)}`;
}

export const REASON_ORDER = ["n_below_100", "empty_pool", "no_rivals"];
