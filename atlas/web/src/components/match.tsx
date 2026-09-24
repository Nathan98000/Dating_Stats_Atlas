import Link from "next/link";
import type { MatchBlock, Meta } from "@/lib/types";
import { toneText } from "@/lib/tones";
import { InfoTip } from "./info-tip";

/** Chances of matching (m3.0.0, ADR 0009): the index the API computed
 * (100 = the US average for this search), its unit line, its band label
 * and the information box — Nathan's text from the registry, with the
 * link to the plain-words account of how it is measured. Never renders
 * a number the API didn't send; the margin is returned and not shown
 * (ADR 0004 still). */
export function MatchFigure({
  match,
  meta,
  id,
  compact = false,
}: {
  match: MatchBlock | undefined;
  meta: Meta;
  id: string;
  compact?: boolean;
}) {
  const le = meta.features.match_propensity;
  const policy = meta.policy_strings;
  if (!match || !match.available || match.display == null) return null;
  return (
    <div className="flex flex-col gap-1" data-testid="match-figure">
      <div className="flex items-center gap-1.5">
        <span className="text-[13px] font-semibold text-ink-2">{le.display_name}</span>
        <InfoTip id={id} label={le.display_name} testid="match-info">
          {policy.match_info}{" "}
          {match.note ? <span data-testid="match-same-sex-note">{match.note}{" "}</span> : null}
          <Link
            href="/how-it-works#chances-of-matching"
            className="font-semibold text-accent underline underline-offset-2 hover:text-accent-hover"
          >
            {policy.match_how_link}
          </Link>
        </InfoTip>
      </div>
      <p className="flex flex-wrap items-baseline gap-x-2">
        <span className={`font-display font-semibold leading-none ${compact ? "text-[22px]" : "text-[30px]"}`}>
          {match.display}
        </span>
        <span className={`text-ink-3 ${compact ? "text-[12.5px]" : "text-sm"}`}>
          {match.unit_line ?? le.unit}
        </span>
      </p>
      {match.band && (
        <span className={`text-[12.5px] font-semibold ${toneText(match.band.tone)}`} data-testid="match-band">
          {match.band.label}
        </span>
      )}
    </div>
  );
}
