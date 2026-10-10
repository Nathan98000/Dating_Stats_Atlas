import type React from "react";
import { edgeOf, leadOf, signedDiff } from "@/lib/compare";
import { fill } from "@/lib/results";

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
 * table a table for screen readers when its display changes.
 *
 * Phase 6 (F07): a judged row's Edge reads "▲ Denver" over "by 31,802" —
 * the registry's compare_edge_by with the absolute value of the same
 * subtraction ("by 2 places" for the spot in the results,
 * compare_edge_places) — and a screen reader hears "Denver, by 31,802".
 * Rows the site doesn't judge keep the dash over the plain signed
 * difference. */

export type { Edge } from "@/lib/compare";
export { edgeOf } from "@/lib/compare";

export function Row({ label, note, children }: {
  label: string;
  /** Phase 6 (F01): a line under the label (the same-sex note on the
   * Matches row), chosen in the browser, so kept inside the variant veil */
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <tr role="row" className="grid grid-cols-2 border-b border-rule last:border-b-0 sm:table-row">
      <th role="rowheader" scope="row"
        className="col-span-2 px-4 pb-1 pt-3.5 text-left align-top text-caption font-semibold text-ink-2 sm:px-5 sm:py-3.5">
        {label}
        {note && (
          <span data-variant="" className="mt-1 block max-w-[40ch] text-overline font-normal tracking-normal text-ink-3"
            data-testid="same-sex-note">
            {note}
          </span>
        )}
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
        {/* fills the cell, so a figure drawn to its width (balance's dots) has one */}
        <span className="min-w-0 flex-1">{children}</span>
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
  by,
  places,
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
  /** Phase 6: the registry's compare_edge_by ("by {diff}") */
  by: string;
  /** Phase 6: the spot row's compare_edge_places ("by {n} places") */
  places?: string;
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
  const edge = edgeOf(a, b, direction, grey);
  const lead = leadOf(a, b, decimals, dollar);
  const body = edge === 0 ? signedDiff(a, b, decimals, dollar)
    : places ? fill(places, { n: lead }) : fill(by, { diff: lead });
  return (
    <td role="cell" className={cls} data-diff-for={id} data-edge={edge} {...v}>
      {edge === 0 ? (
        <span className="text-body-sm text-ink-3">—</span>
      ) : (
        <span className="flex items-center gap-1.5 text-body-sm font-semibold text-good-strong">
          <EdgeMark />
          <span>{names[edge === 1 ? 0 : 1]}<span className="sr-only">,</span></span>
        </span>
      )}
      <span className="block text-caption text-ink-3" data-diff-value>{body}</span>
    </td>
  );
}
