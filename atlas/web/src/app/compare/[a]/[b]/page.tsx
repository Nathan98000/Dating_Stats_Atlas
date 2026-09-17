import Link from "next/link";
import { notFound } from "next/navigation";
import { apiMeta, apiRank } from "@/lib/api";
import {
  describeSearch,
  isDefaultSearch,
  parsePrefs,
  toRankBody,
  toSearchParams,
  type SearchParams,
} from "@/lib/prefs";
import { SiteHeader } from "@/components/chrome";
import { BalanceTally } from "@/components/tally";
import type { Card, Meta, RankedRow, SuppressedRow } from "@/lib/types";

export const dynamic = "force-dynamic";

/** Two cities side by side (ADR 0003, restyled to v3), from ONE rank
 * response so both sit under the same normalization. Pools never get a
 * difference (the API computes per-city figures, not pairs); the
 * difference column is plain subtraction of two shown static values — the
 * one deliberate piece of client arithmetic, per the ADR. */
export default async function ComparePage({
  params,
  searchParams,
}: {
  params: Promise<{ a: string; b: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const { a, b } = await params;
  const sp = await searchParams;
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

  return (
    <>
      <SiteHeader />
      <div className="mx-auto flex max-w-5xl flex-col gap-6 px-6 pb-16 pt-8 sm:px-12">
        <Link href={`/?${qs}`} className="text-sm font-semibold text-accent hover:text-accent-hover">
          ← Back to your results
        </Link>
        <h1 className="font-display text-[34px] font-semibold leading-tight tracking-tight">
          {mA.display_name_full.split(",")[0]}{" "}
          <span className="text-ink-3">and</span>{" "}
          {mB.display_name_full.split(",")[0]}
        </h1>
        <p className="max-w-[64ch] text-[15px] text-ink-2">
          For {describeSearch(prefs).toLowerCase()} — the same search and the
          same yardstick as your results.
        </p>
        {isDefaultSearch(sp) && (
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
                <td className="px-5 py-3.5 text-ink-3">—</td>
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
                <td className="px-5 py-3.5 text-ink-3">—</td>
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
                <td className="px-5 py-3.5 text-[12px] leading-snug text-ink-3">
                  counted per city, so no difference is shown
                </td>
              </Row>
              <Row label={meta.features.pool_balance.display_name}>
                {[rowA, rowB].map((r, i) => (
                  <td key={i} className="px-5 py-3.5">
                    {r ? <BalanceTally balance={r.balance} compact /> : "—"}
                  </td>
                ))}
                <td className="px-5 py-3.5 text-ink-3">—</td>
              </Row>
              {meta.city_cards.map((id) => {
                const le = meta.features[id];
                const cA = cardOf(rowA, id);
                const cB = cardOf(rowB, id);
                return (
                  <Row key={id} label={le.display_name}>
                    {[cA, cB].map((c, i) => (
                      <td key={i} className="px-5 py-3.5">
                        {c && c.display !== undefined ? (
                          <div className="flex flex-col">
                            <span className="text-[16px] font-semibold">
                              {id === "median_gross_rent" ? "$" : ""}
                              {c.display}
                            </span>
                            {c.band && (
                              <span
                                className={`text-[12px] font-semibold ${c.band.tone === "good" ? "text-good" : c.band.tone === "poor" ? "text-poor" : "text-ink-3"}`}
                              >
                                {c.band.label}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-ink-3">not available</span>
                        )}
                      </td>
                    ))}
                    <td className="px-5 py-3.5 text-[14px]">
                      {staticDiff(cA, cB, meta, id) ?? <span className="text-ink-3">—</span>}
                    </td>
                  </Row>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Phase 2e item 11: two numbers per city, side by side like the
            other stats, ONE plain banner above them, the detail one
            click away. No coverage percentages, no agency talk. */}
        <section className="flex flex-col gap-4 rounded-xl border border-rule bg-surface px-7 py-6" data-testid="compare-crime">
          <h2 className="font-display text-[21px] font-semibold">Reported crime</h2>
          <p
            className="max-w-[76ch] rounded-lg border border-tint-border bg-tint px-4 py-3 text-[13px] leading-relaxed text-accent-hover"
            data-testid="crime-compare-banner"
          >
            {(rowA?.crime ?? rowB?.crime)?.compare_banner}{" "}
            <Link href="/about-crime-data" className="font-semibold underline underline-offset-2">
              About these figures
            </Link>
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
                  <th scope="row" className="py-2.5 pr-4 text-left text-[13px] font-semibold text-ink-2">
                    {meta.features[fid].display_name}
                  </th>
                  {[rowA, rowB].map((r, i) => {
                    const s = r?.crime?.stats?.find((x) => x.id === fid);
                    return (
                      <td key={i} className="py-2.5 pr-4">
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

function staticDiff(
  cA: Card | undefined,
  cB: Card | undefined,
  meta: Meta,
  id: string,
): string | null {
  if (!cA || !cB) return null;
  if (cA.value === null || cA.value === undefined) return null;
  if (cB.value === null || cB.value === undefined) return null;
  if (id === "who_lives_here") return null; // population stays per-city
  const le = meta.features[id];
  const d = (cA.value - cB.value) * (le.display_scale ?? 1);
  const nd = le.display_decimals ?? 1;
  const sign = d >= 0 ? "+" : "−";
  return `${sign}${Math.abs(d).toLocaleString("en-US", {
    minimumFractionDigits: nd,
    maximumFractionDigits: nd,
  })}`;
}
