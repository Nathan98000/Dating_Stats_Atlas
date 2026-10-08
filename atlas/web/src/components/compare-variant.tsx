"use client";

import { useMemo } from "react";
import type { Meta, RankedRow, SuppressedRow, VariantResponse } from "@/lib/types";
import { selectVariant } from "@/lib/variants";
import { useAboutYou } from "@/lib/use-about-you";
import { BalanceTrack } from "./balance-track";
import { DiffCell, Row } from "./compare-cells";

/** The compare table's rows an "about you" variant changes (m4.0.0, ADR
 * 0018): the spot in the visitor's results, the score, the compatibility
 * figure and the balance. The server cut the response down to the two
 * cities (lib/variants sliceVariants); this selects the visitor's variant
 * and renders the API's numbers — the differences are the table's usual
 * subtraction of two displayed values. */
export function CompareVariantRows({
  slice,
  cbsaA,
  cbsaB,
  meta,
}: {
  slice: VariantResponse;
  cbsaA: string;
  cbsaB: string;
  meta: Meta;
}) {
  const about = useAboutYou();
  const sel = useMemo(() => selectVariant(slice, about), [slice, about]);
  const policy = meta.policy_strings;
  const find = (cbsa: string): RankedRow | SuppressedRow | undefined =>
    sel.ranked.find((r) => r.cbsa === cbsa) ?? sel.suppressed.find((r) => r.cbsa === cbsa);
  const isRanked = (r: RankedRow | SuppressedRow | undefined): r is RankedRow =>
    Boolean(r && "rank" in r);
  const rowA = find(cbsaA);
  const rowB = find(cbsaB);
  const rankA = isRanked(rowA) ? rowA : undefined;
  const rankB = isRanked(rowB) ? rowB : undefined;
  return (
    <>
      {/* item 6.1: the gap in places — smaller spot is better, so the
          colour reads through direction −1 */}
      <Row label="Spot in your results">
        {[rowA, rowB].map((r, i) => (
          <td key={i} className="px-5 py-3.5" data-variant="">
            {isRanked(r) ? (
              <span className="font-display text-[21px] font-semibold">{r.rank}</span>
            ) : (
              <span className="text-[13px] leading-snug text-ink-2">
                {r ? policy[r.reason] : "Not covered"}
              </span>
            )}
          </td>
        ))}
        <DiffCell
          id="rank"
          variant
          a={rankA && rankB ? String(rankA.rank) : undefined}
          b={rankA && rankB ? String(rankB.rank) : undefined}
          decimals={0}
          direction={-1}
        />
      </Row>
      {/* Phase 4b (Nathan's change 7): "Overall score", as on the rows */}
      <Row label={policy.overall_score_label}>
        {[rowA, rowB].map((r, i) => (
          <td key={i} className="px-5 py-3.5" data-variant="">
            {isRanked(r) ? (
              <span className="font-display text-[21px] font-semibold">{r.score_display}</span>
            ) : (
              <span className="text-ink-3">—</span>
            )}
          </td>
        ))}
        <DiffCell
          id="score"
          variant
          a={rankA && rankB ? rankA.score_display : undefined}
          b={rankA && rankB ? rankB.score_display : undefined}
          decimals={0}
          direction={1}
        />
      </Row>
      <Row label="People who match">
        {[rowA, rowB].map((r, i) => (
          <td key={i} className="px-5 py-3.5">
            {isRanked(r) ? (
              <span className="font-display text-[21px] font-semibold">
                {r.pool.toLocaleString("en-US")}
              </span>
            ) : (
              <span className="text-[13px] leading-snug text-ink-2">
                {r ? policy[r.reason] : "—"}
              </span>
            )}
          </td>
        ))}
        <DiffCell
          id="pool"
          a={rankA && rankB ? rankA.pool.toLocaleString("en-US") : undefined}
          b={rankA && rankB ? rankB.pool.toLocaleString("en-US") : undefined}
          decimals={0}
          direction={meta.features.pool_size.direction}
        />
      </Row>
      {/* m3.0.0 (ADR 0009): the compatibility figure of a ranked row —
          no band words since Phase 4b (ADR 0018 amended); the difference
          reads through the registry direction like every scored stat */}
      <Row label={meta.features.match_propensity.display_name}>
        {[rankA, rankB].map((r, i) => (
          <td key={i} className="px-5 py-3.5" data-variant="">
            {r?.match?.available && r.match.display != null ? (
              <div className="flex flex-col">
                <span className="font-display text-[21px] font-semibold">
                  {r.match.display}
                </span>
                <span className="text-[12px] text-ink-3">
                  {r.match.unit_line ?? meta.features.match_propensity.unit}
                </span>
              </div>
            ) : (
              <span className="text-ink-3">—</span>
            )}
          </td>
        ))}
        {/* m3.1.0 (Phase 3b A3): a capped figure ("250+") is not a
            number, so no difference is computed from it — the cell shows
            the same dash a missing figure gets */}
        <DiffCell
          id="match_propensity"
          variant
          a={rankA?.match?.available && !rankA.match.capped ? rankA.match.display ?? undefined : undefined}
          b={rankB?.match?.available && !rankB.match.capped ? rankB.match.display ?? undefined : undefined}
          decimals={meta.features.match_propensity.display_decimals}
          direction={meta.features.match_propensity.direction}
        />
      </Row>
      <Row label={meta.features.pool_balance.display_name}>
        {[rowA, rowB].map((r, i) => (
          <td key={i} className="px-5 py-3.5" data-variant="">
            {r ? <BalanceTrack balance={r.balance} meta={meta} id={`cmp-${i}`} caption={false} /> : "—"}
          </td>
        ))}
        <DiffCell
          id="balance"
          variant
          a={rowA?.balance.available ? String(rowA.balance.per_100) : undefined}
          b={rowB?.balance.available ? String(rowB.balance.per_100) : undefined}
          decimals={0}
          direction={meta.features.pool_balance.direction}
        />
      </Row>
    </>
  );
}
