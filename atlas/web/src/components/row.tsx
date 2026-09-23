import Link from "next/link";
import type { Meta, RankedRow } from "@/lib/types";
import { BalanceTally } from "./tally";
import { MatchFigure } from "./match";

/** A v3 result row: rank numeral, city, the pool figure large with its
 * plain caption, the movers line, the balance tally, and the score out of
 * 100 with its meter (filled to score/100 — the number is the signal, the
 * meter is the texture). No margin, no CV, no code, no permalink. */
export function ResultRow({
  row,
  meta,
  queryString,
}: {
  row: RankedRow;
  meta: Meta;
  queryString: string;
}) {
  const poolLegend = meta.features.pool_size;
  return (
    <li
      className="grid grid-cols-[52px_1fr_auto] gap-x-5 gap-y-2 border-b border-rule py-6 max-sm:grid-cols-[40px_1fr]"
      data-cbsa={row.cbsa}
      data-rank={row.rank}
      data-slug={row.slug}
    >
      <div
        aria-hidden="true"
        className="pt-1 font-display text-[34px] font-semibold leading-none text-ink"
      >
        {row.rank}
      </div>

      <div className="flex min-w-0 flex-col gap-2.5">
        <h3 className="font-display text-[21px] font-semibold leading-snug">
          <span className="sr-only">Ranked {row.rank}: </span>
          <Link
            href={`/city/${row.slug}${queryString ? `?${queryString}` : ""}`}
            className="hover:text-accent-hover hover:underline"
          >
            {row.display_name}
          </Link>
        </h3>
        <p className="flex flex-wrap items-baseline gap-x-2">
          <span className="font-display text-[26px] font-semibold leading-none">
            {row.pool.toLocaleString("en-US")}
          </span>
          <span className="text-sm text-ink-2">{poolLegend.unit}</span>
        </p>
        <p className="max-w-[64ch] text-sm leading-relaxed text-ink-2">
          {row.summary_line}
        </p>
        <div className="mt-1 flex flex-wrap gap-x-10 gap-y-3">
          <div className="flex flex-col gap-1.5" data-testid="balance-tally">
            <span className="text-[13px] font-semibold text-ink-2">
              {meta.features.pool_balance.display_name}
            </span>
            <BalanceTally balance={row.balance} compact />
          </div>
          {/* m3.0.0 (ADR 0009): chances of matching — the scored figure,
              the API's display string, the registry information box */}
          <MatchFigure match={row.match} meta={meta} id={`match-${row.cbsa}`} compact />
        </div>
      </div>

      <div className="flex flex-col items-end gap-1.5 max-sm:col-start-2 max-sm:items-start">
        <div className="flex items-baseline gap-1.5">
          <span
            className="font-display text-[40px] font-semibold leading-none"
            data-testid="score"
          >
            {row.score_display}
          </span>
          <span className="text-xs text-ink-3">out of 100</span>
        </div>
        <div
          aria-hidden="true"
          className="h-[5px] w-[96px] overflow-hidden rounded-full bg-rule"
        >
          <div
            className="h-full rounded-full bg-accent"
            style={{ width: `${Math.min(100, Math.max(0, row.score))}%` }}
          />
        </div>
      </div>
    </li>
  );
}
