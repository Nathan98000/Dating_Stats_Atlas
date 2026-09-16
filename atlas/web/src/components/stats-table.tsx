import Link from "next/link";
import type { Meta, Stat } from "@/lib/types";
import { signedPoints, ordinal } from "@/lib/format";
import { StandingMark } from "./figures";

/** Every stat the site holds, on demand (ADR 0003c): display name, value in
 * real units, standing across the query's ranked set, weight under the
 * current preferences, contribution. Labels, units and definitions come
 * from the legend — none live here. Every row links to its provenance
 * record (acceptance gate 2). */
export function StatsTable({
  stats,
  meta,
  withContributions,
  caption,
}: {
  stats: Stat[];
  meta: Meta;
  withContributions: boolean;
  caption: string;
}) {
  const policy = meta.policy_strings;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[540px] text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="text-left text-xs text-ink-3">
            <th scope="col" className="py-1.5 pr-3 font-semibold">Stat</th>
            <th scope="col" className="py-1.5 pr-3 font-semibold">Value</th>
            <th scope="col" className="py-1.5 pr-3 font-semibold">Standing</th>
            {withContributions && (
              <>
                <th scope="col" className="py-1.5 pr-3 font-semibold">Weight</th>
                <th scope="col" className="py-1.5 pr-3 font-semibold">Effect on score</th>
              </>
            )}
            <th scope="col" className="py-1.5 font-semibold">
              <span className="sr-only">Provenance</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {stats.map((s) => {
            const legend = meta.features[s.id];
            if (!legend) return null;
            const pillar = meta.pillars[legend.pillar];
            return (
              <tr key={s.id} className="border-t border-rule-2 align-baseline">
                <th scope="row" className="py-2 pr-3 text-left font-normal">
                  <span className="text-ink">{legend.display_name}</span>
                  {pillar && (
                    <span className="ml-2 text-xs text-ink-3">{pillar.display_name}</span>
                  )}
                  <span className="sr-only">. {legend.definition}</span>
                </th>
                <td className="num py-2 pr-3 whitespace-nowrap">
                  {s.value === null || s.missing ? (
                    <span className="text-ink-3">
                      not available here
                      <span className="sr-only"> — {policy.missing_features}</span>
                    </span>
                  ) : s.suppressed ? (
                    <span className="text-ink-3">{policy[s.suppressed] ?? s.suppressed}</span>
                  ) : (
                    <>
                      <span className="text-ink">{s.display}</span>{" "}
                      <span className="text-ink-3">{legend.unit}</span>
                      {s.moe_display !== undefined && (
                        <span className="text-ink-2">
                          {" "}
                          ±{s.moe_display}
                          <span className="sr-only">
                            {" "}
                            margin, measured directly from replicate weights
                          </span>
                        </span>
                      )}
                    </>
                  )}
                </td>
                <td className="py-2 pr-3 whitespace-nowrap">
                  {s.standing !== undefined ? (
                    <>
                      <StandingMark pct={s.standing} />
                      <span className="num ml-2 text-xs text-ink-2">
                        {ordinal(s.standing)}
                      </span>
                    </>
                  ) : (
                    <span className="text-ink-3">—</span>
                  )}
                </td>
                {withContributions && (
                  <>
                    <td className="num py-2 pr-3 text-ink-2">
                      {s.weight !== undefined ? `${(s.weight * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="num py-2 pr-3">
                      {s.contribution !== undefined && s.contribution !== null ? (
                        <span className={s.contribution >= 0 ? "text-pass" : "text-crit"}>
                          {signedPoints(s.contribution)} pts
                        </span>
                      ) : (
                        <span className="text-ink-3">—</span>
                      )}
                    </td>
                  </>
                )}
                <td className="py-2 text-right">
                  <Link
                    href={`/methodology#f-${s.id}`}
                    className="text-xs text-accent underline underline-offset-2"
                  >
                    source
                    <span className="sr-only"> and provenance for {legend.display_name}</span>
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
