import type React from "react";
import { edgeOf, parseDisplayed } from "@/lib/compare";

/** The compare table's row, value cell and edge cell, shared by the server
 * page and the part an "about you" variant changes (components/compare-
 * variant, m4.0.0). Phase 2f item 6 (ADR 0007): every row's difference is
 * plain subtraction of the two DISPLAYED values — parsed back from the
 * display strings themselves, so the equality with what the visitor sees
 * holds by construction and nothing is recomputed from raw values.
 *
 * Phase 5: the Difference column became Edge — "▲ Boston" where that city
 * does better for this search (the decision unchanged: d × direction > 0
 * favours the left-hand city), a dash where the site doesn't judge or the
 * two are equal — with the difference itself kept as quiet text beneath.
 * Below 640px the table reflows: each measure is a block, its label across
 * the top and the two cities' values side by side, the winner's value
 * marked ▲ (the edge column is hidden there). Explicit roles keep the
 * table a table for screen readers when its display changes. */

export type { Edge } from "@/lib/compare";
export { edgeOf } from "@/lib/compare";

export function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <tr role="row" className="grid grid-cols-2 border-b border-rule last:border-b-0 sm:table-row">
      <th role="rowheader" scope="row"
        className="col-span-2 px-4 pb-1 pt-3.5 text-left align-top text-caption font-semibold text-ink-2 sm:px-5 sm:py-3.5">
        {label}
      </th>
      {children}
    </tr>
  );
}

/** One city's value: on a phone the winning side carries a ▲. */
export function ValueCell({ win = false, edgeLabel = "", variant = false, children }: {
  win?: boolean; edgeLabel?: string; variant?: boolean; children: React.ReactNode;
}) {
  return (
    <td role="cell" className="px-4 pb-3.5 pt-1 align-top sm:px-5 sm:py-3.5" {...(variant ? { "data-variant": "" } : {})}>
      <span className="flex items-start gap-1.5">
        {win && (
          <span className="pt-0.5 text-good-strong sm:hidden" role="img" aria-label={edgeLabel}>
            <EdgeMark />
          </span>
        )}
        <span className="min-w-0">{children}</span>
      </span>
    </td>
  );
}

function EdgeMark() {
  return (
    <svg width="9" height="8" viewBox="0 0 8 7" aria-hidden="true" fill="currentColor" className="inline">
      <path d="M4 0L8 7H0z" />
    </svg>
  );
}

export function DiffCell({
  id,
  a,
  b,
  decimals,
  direction,
  names,
  grey = false,
  dollar = false,
  variant = false,
}: {
  id: string;
  a?: string;
  b?: string;
  decimals: number;
  direction: number;
  /** the two cities' short names, left and right */
  names: [string, string];
  grey?: boolean;
  dollar?: boolean;
  /** m4.0.0: a difference an "about you" variant changes (kept unseen
   * while the browser's variant is pending) */
  variant?: boolean;
}) {
  const v = variant ? { "data-variant": "" } : {};
  const cls = "px-5 py-3.5 align-top max-sm:hidden";
  if (a === undefined || b === undefined) {
    return (
      <td role="cell" className={`${cls} text-ink-3`} data-diff-for={id} {...v}>
        —
      </td>
    );
  }
  const d = parseDisplayed(a) - parseDisplayed(b);
  const sign = d > 0 ? "+" : d < 0 ? "−" : "";
  const body = `${sign}${dollar ? "$" : ""}${Math.abs(d).toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
  const edge = edgeOf(a, b, direction, grey);
  return (
    <td role="cell" className={cls} data-diff-for={id} data-edge={edge} {...v}>
      {edge === 0 ? (
        <span className="text-body-sm text-ink-3">—</span>
      ) : (
        <span className="flex items-center gap-1.5 text-body-sm font-semibold text-good-strong">
          <EdgeMark />
          {names[edge === 1 ? 0 : 1]}
        </span>
      )}
      <span className="block text-caption text-ink-3" data-diff-value>{body}</span>
    </td>
  );
}
