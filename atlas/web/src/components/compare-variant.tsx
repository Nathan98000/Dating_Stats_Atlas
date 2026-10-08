"use client";

import { useMemo } from "react";
import type { Meta, RankedRow, SuppressedRow, VariantResponse } from "@/lib/types";
import { selectVariant } from "@/lib/variants";
import { useAboutYou } from "@/lib/use-about-you";
import { BalanceTrack } from "./balance-track";
import { DiffCell, edgeOf, Row, ValueCell, type Edge } from "./compare-cells";

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
  nameA,
  nameB,
  meta,
}: {
  slice: VariantResponse;
  cbsaA: string;
  cbsaB: string;
  nameA: string;
  nameB: string;
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
  const names: [string, string] = [nameA, nameB];
  const edge = policy.compare_edge;
  const rankEdge = edgeOf(rankA && rankB ? String(rankA.rank) : undefined,
    rankA && rankB ? String(rankB.rank) : undefined, -1);
  const scoreEdge = edgeOf(rankA?.score_display, rankB?.score_display, 1);
  const poolEdge = edgeOf(rankA && rankB ? rankA.pool.toLocaleString("en-US") : undefined,
    rankA && rankB ? rankB.pool.toLocaleString("en-US") : undefined, meta.features.pool_size.direction);
  const matchA = rankA?.match?.available && !rankA.match.capped ? rankA.match.display ?? undefined : undefined;
  const matchB = rankB?.match?.available && !rankB.match.capped ? rankB.match.display ?? undefined : undefined;
  const matchEdge = edgeOf(matchA, matchB, meta.features.match_propensity.direction);
  const balA = rowA?.balance.available ? String(rowA.balance.per_100) : undefined;
  const balB = rowB?.balance.available ? String(rowB.balance.per_100) : undefined;
  const balEdge = edgeOf(balA, balB, meta.features.pool_balance.direction);
  const win = (e: Edge, i: number) => e === (i === 0 ? 1 : -1);
  return (
    <>
      {/* item 6.1: the gap in places — smaller spot is better, so the
          edge reads through direction −1 */}
      <Row label="Spot in your results">
        {[rowA, rowB].map((r, i) => (
          <ValueCell key={i} variant win={win(rankEdge, i)} edgeLabel={edge}>
            {isRanked(r) ? (
              <span className="font-display text-h3">{r.rank}</span>
            ) : (
              <span className="text-caption text-ink-2">
                {r ? policy[r.reason] : "Not covered"}
              </span>
            )}
          </ValueCell>
        ))}
        <DiffCell
          id="rank"
          variant
          names={names}
          a={rankA && rankB ? String(rankA.rank) : undefined}
          b={rankA && rankB ? String(rankB.rank) : undefined}
          decimals={0}
          direction={-1}
        />
      </Row>
      {/* Phase 4b (Nathan's change 7): "Overall score" */}
      <Row label={policy.overall_score_label}>
        {[rowA, rowB].map((r, i) => (
          <ValueCell key={i} variant win={win(scoreEdge, i)} edgeLabel={edge}>
            {isRanked(r) ? (
              <span className="font-display text-h3">{r.score_display}</span>
            ) : (
              <span className="text-ink-3">—</span>
            )}
          </ValueCell>
        ))}
        <DiffCell
          id="score"
          variant
          names={names}
          a={rankA && rankB ? rankA.score_display : undefined}
          b={rankA && rankB ? rankB.score_display : undefined}
          decimals={0}
          direction={1}
        />
      </Row>
      <Row label="People who match">
        {[rowA, rowB].map((r, i) => (
          <ValueCell key={i} win={win(poolEdge, i)} edgeLabel={edge}>
            {isRanked(r) ? (
              <span className="text-data-m">{r.pool.toLocaleString("en-US")}</span>
            ) : (
              <span className="text-caption text-ink-2">
                {r ? policy[r.reason] : "—"}
              </span>
            )}
          </ValueCell>
        ))}
        <DiffCell
          id="pool"
          names={names}
          a={rankA && rankB ? rankA.pool.toLocaleString("en-US") : undefined}
          b={rankA && rankB ? rankB.pool.toLocaleString("en-US") : undefined}
          decimals={0}
          direction={meta.features.pool_size.direction}
        />
      </Row>
      {/* m3.0.0 (ADR 0009): the compatibility figure of a ranked row —
          no band words since Phase 4b (ADR 0018 amended) */}
      <Row label={meta.features.match_propensity.display_name}>
        {[rankA, rankB].map((r, i) => (
          <ValueCell key={i} variant win={win(matchEdge, i)} edgeLabel={edge}>
            {r?.match?.available && r.match.display != null ? (
              <div className="flex flex-col">
                <span className="text-data-m">{r.match.display}</span>
                <span className="text-caption text-ink-3">
                  {r.match.unit_line ?? meta.features.match_propensity.unit}
                </span>
              </div>
            ) : (
              <span className="text-ink-3">—</span>
            )}
          </ValueCell>
        ))}
        {/* m3.1.0 (Phase 3b A3): a capped figure ("250+") is not a
            number, so no difference is computed from it — the cell shows
            the same dash a missing figure gets */}
        <DiffCell
          id="match_propensity"
          variant
          names={names}
          a={matchA}
          b={matchB}
          decimals={meta.features.match_propensity.display_decimals}
          direction={meta.features.match_propensity.direction}
        />
      </Row>
      <Row label={meta.features.pool_balance.display_name}>
        {[rowA, rowB].map((r, i) => (
          <ValueCell key={i} variant win={win(balEdge, i)} edgeLabel={edge}>
            {r ? <BalanceTrack balance={r.balance} meta={meta} id={`cmp-${i}`} caption={false} /> : "—"}
          </ValueCell>
        ))}
        <DiffCell
          id="balance"
          variant
          names={names}
          a={balA}
          b={balB}
          decimals={0}
          direction={meta.features.pool_balance.direction}
        />
      </Row>
    </>
  );
}
