"use client";

import Link from "next/link";
import { useState } from "react";

/** The stat page's ranked list with its sort toggle (Phase 2e item 1).
 * Positions are numbered ONCE, at build time, in the direction the
 * registry's direction field calls good; reversing the sort shows the
 * SAME numbers in reverse order — the rule the results list already
 * follows. Since Phase 2f item 9.4 rows carry no band label (the
 * ordering already says it and the distribution strip carries the
 * spread), and item 9.5 adds a header row: the list STAYS an <ol> with
 * an aria-hidden header strip on the same grid, because each row's link
 * already carries its position as an sr-only prefix and its value line
 * carries the unit in words — converting to a <table> would announce
 * the position twice and re-plumb the sort toggle's semantics for no
 * gain. Toggle labels and headers arrive from the registry via the
 * build JSON. */

export interface StatRow {
  slug: string;
  name: string;
  display: string;
  unit_line: string;
  pos: number;
}

export function StatList({
  rows,
  isDollar,
  ariaLabel,
  colName,
  defaultIsLowFirst,
  strings,
}: {
  rows: StatRow[];
  isDollar: boolean;
  ariaLabel: string;
  colName: string;
  defaultIsLowFirst: boolean;
  strings: { sort_low: string; sort_high: string; col_city: string };
}) {
  const [reversed, setReversed] = useState(false);
  const shown = reversed ? [...rows].reverse() : rows;
  const lowFirstShown = defaultIsLowFirst !== reversed;

  return (
    <>
      <div className="flex items-center justify-end gap-2.5">
        <span className="text-[13px] font-semibold text-ink-2" id="stat-sort-label">
          Show
        </span>
        <div role="radiogroup" aria-labelledby="stat-sort-label" className="flex gap-[5px]" data-testid="stat-sort">
          {[
            { low: true, label: strings.sort_low },
            { low: false, label: strings.sort_high },
          ].map((opt) => {
            const on = lowFirstShown === opt.low;
            return (
              <button
                key={opt.label}
                type="button"
                role="radio"
                aria-checked={on}
                className={`min-h-[36px] rounded-[7px] border px-3.5 text-[12.5px] font-semibold ${on ? "border-accent bg-accent text-white" : "border-rule bg-paper text-ink-3 hover:border-ink-3"}`}
                onClick={() => setReversed(opt.low !== defaultIsLowFirst)}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>
      <div>
        {/* item 9.5: the header strip — visual column labels on the same
            grid as the rows; hidden from the tree because each row
            already reads "position: city — value unit" on its own */}
        <div
          aria-hidden="true"
          data-testid="stat-list-header"
          className="grid grid-cols-[44px_1fr_auto] items-baseline gap-x-4 border-b-2 border-rule pb-2 text-[12px] font-bold uppercase tracking-wide text-ink-3"
        >
          <span />
          <span>{strings.col_city}</span>
          <span className="text-right">{colName}</span>
        </div>
        <ol aria-label={ariaLabel} data-testid="stat-list">
        {shown.map((r) => (
          <li
            key={r.slug}
            className="grid grid-cols-[44px_1fr_auto] items-baseline gap-x-4 border-b border-rule py-3"
            data-slug={r.slug}
            data-pos={r.pos}
          >
            <span aria-hidden="true" className="font-display text-[19px] font-semibold text-ink-3">
              {r.pos}
            </span>
            <span className="min-w-0">
              <Link
                href={`/city/${r.slug}`}
                className="text-[15.5px] font-semibold hover:text-accent-hover hover:underline"
              >
                <span className="sr-only">{r.pos}: </span>
                {r.name}
              </Link>
            </span>
            <span className="text-right">
              <span className="font-display text-[19px] font-semibold">
                {isDollar ? "$" : ""}
                {r.display}
              </span>
              <span className="ml-1.5 hidden text-[12px] text-ink-3 sm:inline">
                {r.unit_line}
              </span>
            </span>
          </li>
        ))}
        </ol>
      </div>
    </>
  );
}
