import type { Meta, Mover } from "@/lib/types";

/** Phase 5: why a city ranks where it does, as chips — the served movers
 * (m4.2.1: at most two pluses, then the biggest minus), never re-derived
 * here, each named by its registry chip_label. A plus is teal on its soft
 * fill with a drawn ▲, a minus clay with ▼: the glyph and the word carry the
 * meaning, never the colour alone. The chips are aria-hidden; the row
 * carries the served summary_line for screen readers. */
export function WhyChips({ movers, meta }: { movers: Mover[]; meta: Meta }) {
  if (!movers.length) return null;
  return (
    <span aria-hidden="true" className="flex flex-wrap gap-1.5" data-testid="why-chips">
      {movers.map((m) => {
        const plus = m.sign > 0;
        return (
          <span
            key={m.key}
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
      })}
    </span>
  );
}
