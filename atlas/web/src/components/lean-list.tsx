"use client";

import Link from "next/link";
import { useState } from "react";

/** Political lean's stat-page list (Phase 4d, ADR 0019). The cities come
 * by NAME — never by either party's share unless the visitor asks — and
 * carry no position numbers, since numbering them by a share would line
 * them up by one party. The visitor can sort by either party's share,
 * highest first; the columns always read Democratic, then Republican. The
 * shares the rows sort on and the figures they show are the build's (the
 * API's code, at build time); this component orders rows and shows
 * strings, and computes nothing. The unit line is said once, under the
 * column names, as on the other stat pages; each row still reads whole to
 * a screen reader ("City — 57% Democratic, 42% Republican"). */

export interface LeanRow {
  slug: string;
  name: string;
  dem: string;
  rep: string;
  dem_share: number;
  rep_share: number;
}

type SortKey = "name" | "dem" | "rep";

export function sortLean(rows: LeanRow[], key: SortKey): LeanRow[] {
  if (key === "name") return rows;
  const share = (r: LeanRow) => (key === "dem" ? r.dem_share : r.rep_share);
  // highest first; a tie keeps the name order the rows arrive in
  return [...rows].sort((a, b) => share(b) - share(a));
}

export function LeanList({
  rows,
  ariaLabel,
  unit,
  colCity,
  columns,
  sort,
}: {
  rows: LeanRow[];
  ariaLabel: string;
  unit: string;
  colCity: string;
  columns: { dem: string; rep: string };
  sort: { label: string; name: string; dem: string; rep: string };
}) {
  const [key, setKey] = useState<SortKey>("name");
  const shown = sortLean(rows, key);
  const options: { key: SortKey; label: string }[] = [
    { key: "name", label: sort.name },
    { key: "dem", label: sort.dem },
    { key: "rep", label: sort.rep },
  ];
  return (
    <>
      <div className="flex flex-wrap items-center justify-end gap-2.5">
        <span className="text-[13px] font-semibold text-ink-2" id="lean-sort-label">
          {sort.label}
        </span>
        <div role="radiogroup" aria-labelledby="lean-sort-label" className="flex flex-wrap gap-[5px]" data-testid="lean-sort">
          {options.map((opt) => {
            const on = key === opt.key;
            return (
              <button
                key={opt.key}
                type="button"
                role="radio"
                aria-checked={on}
                data-sort={opt.key}
                className={`min-h-[36px] rounded-[7px] border px-3.5 text-[12.5px] font-semibold ${on ? "border-accent bg-accent text-white" : "border-rule bg-paper text-ink-3 hover:border-ink-3"}`}
                onClick={() => setKey(opt.key)}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>
      <div>
        {/* the header strip: the column names and, once, the unit line;
            hidden from the tree because every row reads whole */}
        <div
          aria-hidden="true"
          data-testid="lean-list-header"
          className="grid grid-cols-[1fr_auto_auto] items-baseline gap-x-6 border-b-2 border-rule pb-2 text-[12px] font-bold uppercase tracking-wide text-ink-3"
        >
          <span>{colCity}</span>
          <span className="w-[92px] text-right">{columns.dem}</span>
          <span className="w-[92px] text-right">{columns.rep}</span>
          <span
            data-testid="lean-list-unit"
            className="col-span-3 mt-0.5 block text-right text-[12px] font-normal normal-case leading-snug tracking-normal"
          >
            {unit}
          </span>
        </div>
        <ol aria-label={ariaLabel} data-testid="lean-list">
          {shown.map((r) => (
            <li
              key={r.slug}
              className="grid grid-cols-[1fr_auto_auto] items-baseline gap-x-6 border-b border-rule py-3"
              data-slug={r.slug}
            >
              <span className="min-w-0">
                <Link
                  href={`/city/${r.slug}`}
                  className="text-[15.5px] font-semibold hover:text-accent-hover hover:underline"
                >
                  {r.name}
                </Link>
              </span>
              <span className="w-[92px] text-right font-display text-[18px] font-semibold" data-col="dem">
                {r.dem}
                <span className="sr-only"> {columns.dem},</span>
              </span>
              <span className="w-[92px] text-right font-display text-[18px] font-semibold" data-col="rep">
                {r.rep}
                <span className="sr-only"> {columns.rep}</span>
              </span>
            </li>
          ))}
        </ol>
      </div>
    </>
  );
}
