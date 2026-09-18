import Link from "next/link";
import { notFound } from "next/navigation";
import { apiMeta, apiRank } from "@/lib/api";
import {
  describeSearch,
  IMPORTANCE_PILLARS,
  isDefaultSearch,
  parsePrefs,
  toRankBody,
  toSearchParams,
  type ImportancePillar,
  type Prefs,
  type SearchParams,
} from "@/lib/prefs";
import { effectiveSearchParams } from "@/lib/server-prefs";
import { SiteHeader } from "@/components/chrome";
import { BalanceTally } from "@/components/tally";
import { toneText } from "@/lib/tones";
import type { Card, RankedRow, SuppressedRow } from "@/lib/types";

export const dynamic = "force-dynamic";

/** Two cities side by side, from ONE rank response so both sit under the
 * same normalization. Phase 2f item 6 (ADR 0007, reversing ADR 0003's
 * "pools get no difference"): EVERY row gets a difference, computed as
 * plain subtraction of the two DISPLAYED values — parsed back from the
 * display strings themselves, so the equality with what the visitor
 * sees holds by construction and nothing is recomputed from raw values.
 * The colour of a difference says whether A − B favours the left-hand
 * city for this visitor, from the registry's direction field; grey
 * means no judgement (population always; a pillar set to Not much,
 * which still carries weight; anything without a direction). */
export default async function ComparePage({
  params,
  searchParams,
}: {
  params: Promise<{ a: string; b: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const { a, b } = await params;
  // explicit URL parameters always win; a bare URL falls back to the
  // visitor's own last search (Phase 2f item 2 / ADR 0007)
  const { sp, fromCookie } = await effectiveSearchParams(await searchParams);
  const prefs = parsePrefs(sp);
  const [meta, response] = await Promise.all([
    apiMeta(),
    apiRank(toRankBody(prefs)),
  ]);
  const mA = meta.metros.find((m) => m.slug === a);
  const mB = meta.metros.find((m) => m.slug === b);
  if (!mA || !mB) notFound();

  const find = (cbsa: string): RankedRow | SuppressedRow | undefined =>
    response.ranked.find((r) => r.cbsa === cbsa) ??
    response.suppressed.find((r) => r.cbsa === cbsa);
  const rowA = find(mA.cbsa);
  const rowB = find(mB.cbsa);
  const isRanked = (r: RankedRow | SuppressedRow | undefined): r is RankedRow =>
    Boolean(r && "rank" in r);
  const qs = toSearchParams(prefs).toString();
  const policy = meta.policy_strings;
  const cardOf = (r: RankedRow | SuppressedRow | undefined, id: string): Card | undefined =>
    r?.cards.find((c) => c.id === id);
  const cityA = mA.display_name_full.split(",")[0];
  const cityB = mB.display_name_full.split(",")[0];

  const rankA = isRanked(rowA) ? rowA : undefined;
  const rankB = isRanked(rowB) ? rowB : undefined;

  return (
    <>
      <SiteHeader />
      <div className="mx-auto flex max-w-5xl flex-col gap-6 px-6 pb-16 pt-8 sm:px-12">
        <Link href={`/?${qs}`} className="text-sm font-semibold text-accent hover:text-accent-hover">
          ← Back to your results
        </Link>
        <h1 className="font-display text-[34px] font-semibold leading-tight tracking-tight">
          {cityA} <span className="text-ink-3">and</span> {cityB}
        </h1>
        <p className="max-w-[64ch] text-[15px] text-ink-2">
          For {describeSearch(prefs).toLowerCase()} — the same search and the
          same yardstick as your results.
        </p>
        {isDefaultSearch(sp) && !fromCookie && (
          <p className="max-w-[64ch] rounded-lg border border-tint-border bg-tint px-4 py-3 text-[13.5px] leading-relaxed text-accent-hover" data-testid="default-profile-note">
            {policy.compare_default_note.replace(
              "{search}", describeSearch(prefs).toLowerCase())}{" "}
            <Link href={`/?${qs}#search-panel`} className="font-bold underline underline-offset-2">
              Make it your search
            </Link>
          </p>
        )}

        <div className="overflow-x-auto rounded-xl border border-rule bg-surface">
          <table className="w-full min-w-[620px] text-sm" data-testid="compare-table">
            <caption className="sr-only">
              {mA.display_name_full} compared with {mB.display_name_full}
            </caption>
            <thead>
              <tr className="border-b border-rule text-left">
                <th scope="col" className="w-[26%] px-5 py-3.5 text-[13px] font-semibold text-ink-3" />
                {[mA, mB].map((m) => (
                  <th key={m.slug} scope="col" className="px-5 py-3.5">
                    <Link
                      href={`/city/${m.slug}?${qs}`}
                      className="font-display text-[17px] font-semibold text-ink hover:text-accent-hover"
                    >
                      {m.display_name}
                    </Link>
                  </th>
                ))}
                <th scope="col" className="px-5 py-3.5 text-[13px] font-semibold text-ink-3">
                  Difference
                </th>
              </tr>
            </thead>
            <tbody>
              {/* item 6.1: the gap in places — smaller spot is better,
                  so the colour reads through direction −1 */}
              <Row label="Spot in your results">
                {[rowA, rowB].map((r, i) => (
                  <td key={i} className="px-5 py-3.5">
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
                  a={rankA && rankB ? String(rankA.rank) : undefined}
                  b={rankA && rankB ? String(rankB.rank) : undefined}
                  decimals={0}
                  direction={-1}
                />
              </Row>
              <Row label="Score out of 100">
                {[rowA, rowB].map((r, i) => (
                  <td key={i} className="px-5 py-3.5">
                    {isRanked(r) ? (
                      <span className="font-display text-[21px] font-semibold">{r.score_display}</span>
                    ) : (
                      <span className="text-ink-3">—</span>
                    )}
                  </td>
                ))}
                <DiffCell
                  id="score"
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
              <Row label={meta.features.pool_balance.display_name}>
                {[rowA, rowB].map((r, i) => (
                  <td key={i} className="px-5 py-3.5">
                    {r ? <BalanceTally balance={r.balance} compact /> : "—"}
                  </td>
                ))}
                <DiffCell
                  id="balance"
                  a={rowA?.balance.available ? String(rowA.balance.per_100) : undefined}
                  b={rowB?.balance.available ? String(rowB.balance.per_100) : undefined}
                  decimals={0}
                  direction={meta.features.pool_balance.direction}
                />
              </Row>
              {meta.city_cards.map((id) => {
                const le = meta.features[id];
                const cA = cardOf(rowA, id);
                const cB = cardOf(rowB, id);
                const grey = greyRule(id, le.pillar, le.direction, prefs);
                return (
                  <Row key={id} label={le.display_name}>
                    {[cA, cB].map((c, i) => (
                      <td key={i} className="px-5 py-3.5">
                        {c && c.display !== undefined ? (
                          <div className="flex flex-col">
                            <span className="text-[16px] font-semibold">
                              {id === "rent_1br" ? "$" : ""}
                              {c.display}
                            </span>
                            {c.band && (
                              <span className={`text-[12px] font-semibold ${toneText(c.band.tone)}`}>
                                {c.band.label}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-[12.5px] text-ink-3">
                            {policy.card_missing}
                          </span>
                        )}
                      </td>
                    ))}
                    <DiffCell
                      id={id}
                      a={cA?.display}
                      b={cB?.display}
                      decimals={le.display_decimals}
                      direction={grey ? 0 : le.direction}
                      grey={grey}
                      dollar={id === "rent_1br"}
                    />
                  </Row>
                );
              })}
            </tbody>
          </table>
        </div>
        {/* item 6.3: what the colours mean, from the registry — grey is
            "we don't judge it", never "this is excluded" */}
        <p className="max-w-[76ch] text-[12.5px] leading-relaxed text-ink-3" data-testid="diff-legend">
          {policy.compare_diff_legend
            .replace("{a}", cityA)
            .replace("{b}", cityB)}
        </p>

        {/* Phase 2e item 11, reworded in 2f item 6.4: two numbers per
            city, ONE plain banner above them, the detail one click away —
            and the unit line says per 100,000 so nobody reads a rate as
            a count (item 6.5). */}
        <section className="flex flex-col gap-4 rounded-xl border border-rule bg-surface px-7 py-6" data-testid="compare-crime">
          <h2 className="font-display text-[21px] font-semibold">Reported crime</h2>
          <p
            className="max-w-[76ch] rounded-lg border border-tint-border bg-tint px-4 py-3 text-[13px] leading-relaxed text-accent-hover"
            data-testid="crime-compare-banner"
          >
            {(rowA?.crime ?? rowB?.crime)?.compare_banner}{" "}
            <Link href="/about-crime-data" className="font-semibold underline underline-offset-2">
              {policy.crime_see_more}
            </Link>
            .
          </p>
          <table className="w-full max-w-[560px] text-sm">
            <thead>
              <tr className="border-b border-rule text-left">
                <th scope="col" className="py-2 pr-4 text-[13px] font-semibold text-ink-3" />
                {[mA, mB].map((m) => (
                  <th key={m.slug} scope="col" className="py-2 pr-4 font-display text-[15px] font-semibold">
                    {m.display_name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(["violent_crime_rate", "property_crime_rate"] as const).map((fid) => (
                <tr key={fid} className="border-b border-rule last:border-b-0">
                  <th scope="row" className="py-2.5 pr-4 text-left align-top">
                    <span className="block text-[13px] font-semibold text-ink-2">
                      {meta.features[fid].display_name}
                    </span>
                    <span className="block max-w-[22ch] text-[11.5px] font-normal leading-snug text-ink-3">
                      {meta.features[fid].unit}
                    </span>
                  </th>
                  {[rowA, rowB].map((r, i) => {
                    const s = r?.crime?.stats?.find((x) => x.id === fid);
                    return (
                      <td key={i} className="py-2.5 pr-4 align-top">
                        {s ? (
                          <span className="font-display text-[19px] font-semibold">{s.display}</span>
                        ) : (
                          <span className="text-[12.5px] text-ink-3">
                            {r?.crime?.card_blank ?? "Not covered"}
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <tr className="border-b border-rule last:border-b-0">
      <th scope="row" className="px-5 py-3.5 text-left align-top text-[13px] font-semibold text-ink-2">
        {label}
      </th>
      {children}
    </tr>
  );
}

/** The grey rules (item 6.3): population is a fact, not a virtue; a
 * pillar set to Not much is "you told us this matters least" (it still
 * carries weight 0.4); no direction means no judgement. Everyday prices
 * is the average of the two scored cost features (the registry says
 * so), so the importance control that covers it is Cost of living even
 * though its own pillar field reads context. */
function greyRule(id: string, pillar: string | undefined, direction: number,
                  prefs: Prefs): boolean {
  if (id === "who_lives_here") return true;
  if (!direction) return true;
  const imp = id === "everyday_prices" ? "cost" : pillar;
  return Boolean(
    imp &&
    (IMPORTANCE_PILLARS as readonly string[]).includes(imp) &&
    prefs.importance[imp as ImportancePillar] === "not_much",
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

function DiffCell({
  id,
  a,
  b,
  decimals,
  direction,
  grey = false,
  dollar = false,
}: {
  id: string;
  a?: string;
  b?: string;
  decimals: number;
  direction: number;
  grey?: boolean;
  dollar?: boolean;
}) {
  if (a === undefined || b === undefined) {
    return (
      <td className="px-5 py-3.5 text-ink-3" data-diff-for={id}>
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
    <td className={`px-5 py-3.5 text-[14px] font-semibold ${tone}`} data-diff-for={id}>
      {body}
    </td>
  );
}
