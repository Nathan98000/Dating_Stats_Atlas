"use client";

import { useState } from "react";
import Link from "next/link";
import type { Meta, RankedRow } from "@/lib/types";
import { fmtInt, signedPoints } from "@/lib/format";
import { FlagChips, PoolFigure } from "./figures";
import { StatsTable } from "./stats-table";

/** One ranked metro (item 3): rank, name from the build's metros.json (the
 * API's `name`, never hand-typed), pool with its margin in the required
 * words, odds, score, the stats that moved it for these weights, flags —
 * and, expanded, every stat the site holds. No comparator sentence; no
 * score_moe in the row (it lives in the detail, labelled the approximation
 * it is). */
export function RankRow({
  row,
  meta,
  raceActive,
  queryString,
}: {
  row: RankedRow;
  meta: Meta;
  raceActive: boolean;
  queryString: string;
}) {
  const [open, setOpen] = useState(false);
  const policy = meta.policy_strings;
  const odds = row.stats.find((s) => s.id === "partners_per_rival");
  const oddsLegend = meta.features.partners_per_rival;
  const movers = (row.top_stats ?? [])
    .map((id) => row.stats.find((s) => s.id === id))
    .filter((s): s is NonNullable<typeof s> => Boolean(s));

  return (
    <li className="border-b border-rule-2 py-4" data-cbsa={row.cbsa} data-rank={row.rank}>
      <div className="grid grid-cols-[3rem_1fr] gap-x-4 sm:grid-cols-[3.5rem_1fr_auto]">
        <div className="row-span-2 pt-0.5 font-serif text-3xl leading-none text-ink" aria-hidden="true">
          {row.rank}
        </div>
        <h3 className="font-serif text-lg font-semibold leading-snug">
          <span className="sr-only">Ranked {row.rank}: </span>
          <Link
            href={`/metro/${row.cbsa}${queryString ? `?${queryString}` : ""}`}
            className="hover:underline"
          >
            {row.name}
          </Link>
        </h3>
        <div className="col-start-2 sm:col-start-3 sm:row-start-1 sm:text-right">
          <span className="num text-lg font-semibold" aria-label={`score ${row.score} of 100`}>
            {row.score.toFixed(1)}
          </span>
          <span className="ml-1 text-xs text-ink-3">score</span>
        </div>

        <div className="col-start-2 mt-1 flex flex-col gap-1.5 text-sm sm:col-span-2">
          <p className="flex flex-wrap items-baseline gap-x-2">
            <PoolFigure
              pool={row.pool}
              moe={row.pool_moe}
              marginWords={policy.margin_row}
              label={meta.features.pool_size.display_name}
            />
            {raceActive && <Counterweight row={row} meta={meta} />}
          </p>
          <p className="text-ink-2">
            {odds?.display !== undefined ? (
              <>
                <span className="num font-semibold text-ink">{odds.display}</span>{" "}
                {oddsLegend.display_name.toLowerCase()}
              </>
            ) : null}
            {movers.length > 0 && (
              <>
                <span className="text-ink-3"> · moved most by </span>
                {movers.map((s, i) => {
                  const le = meta.features[s.id];
                  // pool and odds already lead the row with their values —
                  // repeat only their effect, not the number
                  const onRow = s.id === "pool_size" || s.id === "partners_per_rival";
                  return (
                    <span key={s.id}>
                      {i > 0 && <span className="text-ink-3">, </span>}
                      {onRow
                        ? (s.id === "pool_size" ? "the pool" : "the odds")
                        : le.display_name.toLowerCase()}
                      {!onRow && (
                        <>
                          {" "}
                          <span className="num">{s.display}</span>
                          {le.unit_short ? ` ${le.unit_short}` : ""}
                        </>
                      )}{" "}
                      <span className={`num ${s.contribution! >= 0 ? "text-pass" : "text-crit"}`}>
                        ({signedPoints(s.contribution!)})
                      </span>
                    </span>
                  );
                })}
              </>
            )}
          </p>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <FlagChips flags={row.flags} policy={policy} />
            <button
              type="button"
              className="text-sm text-accent underline underline-offset-2"
              aria-expanded={open}
              onClick={() => setOpen((o) => !o)}
            >
              {open ? "Hide detail" : "Every stat"}
            </button>
          </div>
        </div>
      </div>

      {open && (
        <div className="mt-3 border-l-2 border-rule pl-4 sm:ml-[3.5rem]">
          <p className="mb-2 max-w-[68ch] text-sm text-ink-2">{row.explanation}</p>
          <StatsTable
            stats={row.stats}
            meta={meta}
            withContributions
            caption={`Every stat for ${row.name} under the current preferences`}
          />
          <dl className="mt-3 grid max-w-[68ch] grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs text-ink-2">
            <dt className="font-semibold text-ink-3">Sample</dt>
            <dd>
              <span className="num">{fmtInt(row.n_unweighted)}</span> effective respondents
              (the smaller of allocated count and Kish effective n)
            </dd>
            <dt className="font-semibold text-ink-3">Served CV</dt>
            <dd>
              <span className="num">{(row.cv * 100).toFixed(1)}%</span> — {policy.cv_detail}
            </dd>
            <dt className="font-semibold text-ink-3">Score margin</dt>
            <dd>
              <span className="num">±{row.score_moe.toFixed(1)}</span> points — {policy.score_moe_detail}
            </dd>
            <dt className="font-semibold text-ink-3">Allocation</dt>
            <dd>
              purity <span className="num">{row.allocation_purity.toFixed(2)}</span>
              {row.flags.includes("low_allocation_purity") ? ` — ${policy.low_allocation_purity}` : ""}
            </dd>
          </dl>
          <p className="mt-2 text-xs">
            <Link
              className="text-accent underline underline-offset-2"
              href={`/metro/${row.cbsa}${queryString ? `?${queryString}` : ""}`}
            >
              Full metro page
            </Link>
          </p>
        </div>
      )}
    </li>
  );
}

/** §10.4: whenever a race filter is active, the cross-group pairing rate
 * renders beside the pool at the same visual weight — not a footnote. A
 * null rate never renders as 0%. */
function Counterweight({ row, meta }: { row: RankedRow; meta: Meta }) {
  const policy = meta.policy_strings;
  const le = meta.features.cross_group_pairing_rate;
  if (row.cross_group_pairing_rate === null || row.cross_group_pairing_rate === undefined) {
    return (
      <span className="text-ink-2">
        <span className="text-ink-3">·</span> pairing rate:{" "}
        {policy[row.cross_group_pairing_suppressed ?? "n_below_100"]}
      </span>
    );
  }
  return (
    <span data-figure="pairing">
      <span className="text-ink-3" aria-hidden="true">·</span>{" "}
      <span className="num font-semibold text-ink">
        {row.cross_group_pairing_display}%
      </span>{" "}
      <span className="text-ink-2">{le.display_name.toLowerCase()}</span>
      <span className="num text-ink-2"> ±{row.cross_group_pairing_moe_display}pp</span>
      <span className="sr-only">
        , a margin of plus or minus {row.cross_group_pairing_moe_display}{" "}
        percentage points measured directly from the survey&apos;s replicate
        weights.
      </span>
    </span>
  );
}
