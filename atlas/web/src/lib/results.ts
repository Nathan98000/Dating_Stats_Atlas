/** Phase 5: how many result rows the home page shows. The list opens at
 * INITIAL_VISIBLE (the three featured cards count among them), "Show 10
 * more" adds STEP, "Show all" shows every ranked row, and a new search
 * starts again at INITIAL_VISIBLE. Presentation only: rows are sliced,
 * never re-ranked. */
export const INITIAL_VISIBLE = 10;
export const STEP = 10;
export const FEATURED = 3;

export function visibleSlice<T>(rows: T[], visible: number): { featured: T[]; rest: T[] } {
  const shown = rows.slice(0, Math.max(0, visible));
  return { featured: shown.slice(0, FEATURED), rest: shown.slice(FEATURED) };
}

export function showMore(visible: number, total: number): number {
  return Math.min(total, visible + STEP);
}

/** The visible count that includes the row at `index` (0-based), for
 * "Find a city in your results": never fewer than now. */
export function visibleToInclude(visible: number, index: number): number {
  return Math.max(visible, index + 1);
}

/** Phase 5: where a balance figure sits on the BalanceTrack, as a share of
 * its width (0-1). The track spans 40 to 160 per 100, clamped; 100 (even)
 * is the middle, and above 100 — more of the sought sex — is to the right.
 * Presentation scaling of the served per_100, never a new number. */
export const BALANCE_MIN = 40;
export const BALANCE_MAX = 160;

export function balancePosition(per100: number): number {
  const x = (per100 - BALANCE_MIN) / (BALANCE_MAX - BALANCE_MIN);
  return Math.min(1, Math.max(0, x));
}

/** The diverging bars of "What moved the score": ±DIVERGE_SPAN points
 * span half the width, clamped. Returns the bar's left edge and width as
 * shares of the full width (0-1). */
export const DIVERGE_SPAN = 25;

export function divergingBar(points: number): { left: number; width: number } {
  const w = Math.min(1, Math.abs(points) / DIVERGE_SPAN) / 2;
  return points >= 0 ? { left: 0.5, width: w } : { left: 0.5 - w, width: w };
}

/** Fills a registry template's {slot}s from served values. */
export function fill(template: string, slots: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (m, k: string) =>
    k in slots ? String(slots[k]) : m);
}
