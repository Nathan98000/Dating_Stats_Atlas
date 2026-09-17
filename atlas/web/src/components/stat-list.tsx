"use client";

import Link from "next/link";
import { useState } from "react";

/** The stat page's ranked list with its sort toggle (Phase 2e item 1).
 * Positions are numbered ONCE, at build time, in the direction the
 * registry's direction field calls good; reversing the sort shows the
 * SAME numbers in reverse order — the rule the results list already
 * follows. Toggle labels arrive from the registry via the build JSON. */

export interface StatRow {
  slug: string;
  name: string;
  display: string;
  unit_line: string;
  pos: number;
  band: { label: string; tone: string; key: string } | null;
}

export function StatList({
  rows,
  isDollar,
  ariaLabel,
  defaultIsLowFirst,
  strings,
}: {
  rows: StatRow[];
  isDollar: boolean;
  ariaLabel: string;
  defaultIsLowFirst: boolean;
  strings: { sort_low: string; sort_high: string };
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
              {r.band && (
                <span
                  className={`ml-2.5 text-[12px] font-semibold ${
                    r.band.tone === "good" ? "text-good"
                    : r.band.tone === "poor" ? "text-poor" : "text-ink-3"}`}
                >
                  {r.band.label}
                </span>
              )}
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
    </>
  );
}
