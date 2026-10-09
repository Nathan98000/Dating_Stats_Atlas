"use client";

import Link from "next/link";
import { Segmented } from "./segmented";
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
 * build JSON.
 *
 * A unit line that is the same on every row (all but population's) is
 * said once, under the column name, and each row shows its number alone
 * (Nathan, 2026-09-30: nice days' line beside every figure read as a
 * long string of text next to a number). Each row still carries it for
 * screen readers, so a row reads "position: city — value unit" as
 * before. A line that changes from row to row (population's adults)
 * stays on the row. */

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
  const sharedUnit =
    rows.length > 0 && rows[0].unit_line && rows.every((r) => r.unit_line === rows[0].unit_line)
      ? rows[0].unit_line
      : null;

  return (
    <>
      <div className="flex items-center justify-end gap-2.5">
        <span className="text-caption font-semibold text-ink-2" id="stat-sort-label">
          Show
        </span>
        {/* Phase 6 (F33): the home page's segmented control — a radio
            group, the selected segment white with the 1.5px --ink-2 border
            (the filled berry segments' unselected boundary read 1.23:1) */}
        <Segmented
          labelledBy="stat-sort-label"
          testid="stat-sort"
          inline
          options={[
            { value: "low", label: strings.sort_low },
            { value: "high", label: strings.sort_high },
          ]}
          value={lowFirstShown ? "low" : "high"}
          onChange={(v) => setReversed((v === "low") !== defaultIsLowFirst)}
        />
      </div>
      <div>
        {/* item 9.5: the header strip — visual column labels on the same
            grid as the rows; hidden from the tree because each row
            already reads "position: city — value unit" on its own */}
        <div
          aria-hidden="true"
          data-testid="stat-list-header"
          className="grid grid-cols-[44px_1fr_auto] items-baseline gap-x-4 border-b-2 border-rule pb-2 text-caption font-bold uppercase tracking-wide text-ink-3"
        >
          <span />
          <span>{strings.col_city}</span>
          <span className="text-right">
            <span className="block">{colName}</span>
            {sharedUnit && (
              <span
                data-testid="stat-list-unit"
                className="ml-auto mt-0.5 block max-w-[24ch] text-caption font-normal normal-case leading-snug tracking-normal sm:max-w-none"
              >
                {sharedUnit}
              </span>
            )}
          </span>
        </div>
        <ol aria-label={ariaLabel} data-testid="stat-list">
        {shown.map((r) => (
          <li
            key={r.slug}
            className="grid grid-cols-[44px_1fr_auto] items-baseline gap-x-4 border-b border-rule py-3 max-desk:py-0"
            data-slug={r.slug}
            data-pos={r.pos}
          >
            <span aria-hidden="true" className="font-display text-h3 font-semibold text-ink-3">
              {r.pos}
            </span>
            <span className="min-w-0">
              <Link
                href={`/city/${r.slug}`}
                className="inline-flex items-center max-desk:min-h-11 text-body font-semibold hover:text-accent-hover hover:underline"
              >
                <span className="sr-only">{r.pos}: </span>
                {r.name}
              </Link>
            </span>
            <span className="text-right">
              <span className="text-data-m">
                {isDollar ? "$" : ""}
                {r.display}
              </span>
              {sharedUnit ? (
                <span className="sr-only"> {r.unit_line}</span>
              ) : (
                <span className="ml-1.5 hidden text-caption text-ink-3 sm:inline">
                  {r.unit_line}
                </span>
              )}
            </span>
          </li>
        ))}
        </ol>
      </div>
    </>
  );
}
