import type React from "react";

/** The compare table's row and difference cell, shared by the server page
 * and the part an "about you" variant changes (components/compare-variant,
 * m4.0.0). Phase 2f item 6 (ADR 0007): EVERY row gets a difference,
 * computed as plain subtraction of the two DISPLAYED values — parsed back
 * from the display strings themselves, so the equality with what the
 * visitor sees holds by construction and nothing is recomputed from raw
 * values. */

export function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <tr className="border-b border-rule last:border-b-0">
      <th scope="row" className="px-5 py-3.5 text-left align-top text-[13px] font-semibold text-ink-2">
        {label}
      </th>
      {children}
    </tr>
  );
}

/** A displayed value back to the number it shows: commas stripped,
 * format_pop's "1.3 million" expanded. This is what makes the gate-5
 * equality hold by construction. */
function parseDisplayed(s: string): number {
  const flat = s.replace(/,/g, "");
  const n = parseFloat(flat);
  return /million/.test(flat) ? n * 1_000_000 : n;
}

export function DiffCell({
  id,
  a,
  b,
  decimals,
  direction,
  grey = false,
  dollar = false,
  variant = false,
}: {
  id: string;
  a?: string;
  b?: string;
  decimals: number;
  direction: number;
  grey?: boolean;
  dollar?: boolean;
  /** m4.0.0: a difference an "about you" variant changes (kept unseen
   * while the browser's variant is pending) */
  variant?: boolean;
}) {
  const v = variant ? { "data-variant": "" } : {};
  if (a === undefined || b === undefined) {
    return (
      <td className="px-5 py-3.5 text-ink-3" data-diff-for={id} {...v}>
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
  const tone = grey || !direction || d === 0
    ? "text-ink-3"
    : d * direction > 0 ? "text-good" : "text-poor";
  return (
    <td className={`px-5 py-3.5 text-[14px] font-semibold ${tone}`} data-diff-for={id} {...v}>
      {body}
    </td>
  );
}
