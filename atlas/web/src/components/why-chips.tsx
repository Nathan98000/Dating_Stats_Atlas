import type { Meta, Mover } from "@/lib/types";

/** Phase 5: why a city ranks where it does, as chips — the served movers
 * (m4.2.1: at most two pluses, then the biggest minus), never re-derived
 * here, each named by its registry chip_label. Since Phase 6 (m4.3.0,
 * F12) the chips show the served `lifestyle_movers` — the same rule over
 * the four things a visitor weights — so cities tell apart; the pool and
 * the compatibility figure keep their own column and tile. A plus is teal on its soft
 * fill with a drawn ▲, a minus clay with ▼: the glyph and the word carry the
 * meaning, never the colour alone. The chips are aria-hidden; the row
 * carries the served summary_line for screen readers. A row with no
 * lifestyle mover shows none. */
export function WhyChips({ movers, meta, trailing }: {
  movers: Mover[];
  meta: Meta;
  /** Phase 6 (F06): a control that follows the chips on their last line,
   * pushed to its right end (the card's Details chevron), so it never
   * narrows the lines above it. With one, each chip is hidden from screen
   * readers on its own and the group is not. */
  trailing?: React.ReactNode;
}) {
  if (!movers.length && !trailing) return null;
  const chips = movers.map((m) => {
    const plus = m.sign > 0;
    return (
      <span
        key={m.key}
        aria-hidden={trailing ? "true" : undefined}
        data-sign={plus ? "plus" : "minus"}
        className={`inline-flex h-6 items-center gap-1 whitespace-nowrap rounded-sm px-[7px] text-overline tracking-normal ${plus ? "bg-good-soft text-good-strong" : "bg-poor-soft text-poor-strong"}`}
      >
        {/* the ▲/▼ glyph, drawn (12px is the smallest type size) */}
        <svg width="8" height="7" viewBox="0 0 8 7" className="shrink-0" fill="currentColor">
          <path d={plus ? "M4 0L8 7H0z" : "M0 0h8L4 7z"} />
        </svg>
        {meta.features[m.key]?.chip_label ?? meta.features[m.key]?.display_name ?? m.key}
      </span>
    );
  });
  if (trailing) {
    return (
      <span className="flex flex-wrap items-center gap-1.5" data-testid="why-chips">
        {chips}
        <span className="ml-auto">{trailing}</span>
      </span>
    );
  }
  return (
    <span aria-hidden="true" className="flex flex-wrap gap-1.5" data-testid="why-chips">
      {chips}
    </span>
  );
}
