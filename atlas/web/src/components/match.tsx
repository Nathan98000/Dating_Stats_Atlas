import type { MatchBlock, Meta } from "@/lib/types";

/** The compatibility figure (m3.0.0, ADR 0009; "chances of matching"
 * until m4.0.0, ADR 0018): the index the API computed (100 = the US
 * average for this search) and its unit line. Phase 4b (ADR 0018
 * amended, Nathan's changes 5 and 6): no information box and no band
 * words beside it — the number against 100 says where a city stands, and
 * the side panel's slider box is the one explanation. The API still
 * sends the band. Never renders a number the API didn't send; the margin
 * is returned and not shown (ADR 0004 still). */
export function MatchFigure({
  match,
  meta,
  compact = false,
}: {
  match: MatchBlock | undefined;
  meta: Meta;
  compact?: boolean;
}) {
  const le = meta.features.match_propensity;
  if (!match || !match.available || match.display == null) return null;
  return (
    <div className="flex flex-col gap-1" data-testid="match-figure">
      <span className="text-[13px] font-semibold text-ink-2">{le.display_name}</span>
      <p className="flex flex-wrap items-baseline gap-x-2">
        <span className={`font-display font-semibold leading-none ${compact ? "text-[22px]" : "text-[30px]"}`}>
          {match.display}
        </span>
        <span className={`text-ink-3 ${compact ? "text-[12.5px]" : "text-sm"}`}>
          {match.unit_line ?? le.unit}
        </span>
      </p>
    </div>
  );
}
