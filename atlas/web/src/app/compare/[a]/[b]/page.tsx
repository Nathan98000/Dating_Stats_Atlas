import Link from "next/link";
import { notFound } from "next/navigation";
import { apiMeta, apiRank } from "@/lib/api";
import {
  describePrefs,
  parsePrefs,
  toRankBody,
  toSearchParams,
  type SearchParams,
} from "@/lib/prefs";
import { Masthead } from "@/components/masthead";
import { fmtInt, signedPoints } from "@/lib/format";
import type { Meta, RankedRow, Stat, SuppressedRow } from "@/lib/types";

export const dynamic = "force-dynamic";

/** The compare page (ADR 0003): two metros side by side under ONE ranking
 * response. Normalization is per query across that query's ranked set, so
 * both metros are picked out of the same /v1/rank result — an endpoint
 * scoring two metros in isolation would renormalize over a set of two and
 * disagree with the ranking page for the same preferences.
 *
 * Differences render only for static stats. A pool difference would be a
 * population figure without a margin (the API computes margins per metro,
 * not per pair), and no population figure renders without one — so the two
 * pools stand side by side, each with its own margin. */
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
  const titles = Object.fromEntries(meta.metros.map((m) => [m.cbsa, m.title]));
  if (!titles[a] || !titles[b]) notFound();

  const find = (c: string): RankedRow | SuppressedRow | undefined =>
    response.ranked.find((r) => r.cbsa === c) ??
    response.suppressed.find((r) => r.cbsa === c);
  const rowA = find(a);
  const rowB = find(b);
  const qs = toSearchParams(prefs).toString();
  const policy = meta.policy_strings;

  const isRanked = (r: RankedRow | SuppressedRow | undefined): r is RankedRow =>
    Boolean(r && "rank" in r);

  const statIds = meta.pillar_order
    .flatMap((p) =>
      Object.entries(meta.features)
        .filter(([, e]) => e.pillar === p && e.status === "active" && e.weight_in_pillar > 0)
        .map(([id]) => id),
    )
    .concat(["cross_group_pairing_rate"]);

  const statOf = (r: RankedRow | SuppressedRow | undefined, id: string): Stat | undefined =>
    r?.stats.find((s) => s.id === id);

  return (
    <>
      <Masthead dataVersion={meta.data_version} modelVersion={meta.model_version} />
      <main id="main" className="mx-auto max-w-5xl px-5">
        <p className="text-xs text-ink-3">
          <Link href={`/?${qs}`} className="text-accent underline underline-offset-2">
            ← back to the ranking
          </Link>
        </p>
        <h1 className="mt-2 font-serif text-3xl font-semibold tracking-tight">
          {titles[a]} <span className="text-ink-3">against</span> {titles[b]}
        </h1>
        <p className="mt-1 max-w-[64ch] text-sm text-ink-2">
          For {describePrefs(prefs)} — the same preferences, the same ranked
          set, the same normalization as the ranking page.
        </p>

        <div className="mt-6 overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm" data-testid="compare-table">
            <caption className="sr-only">
              {titles[a]} compared with {titles[b]} under the current preferences
            </caption>
            <thead>
              <tr className="text-left text-xs text-ink-3">
                <th scope="col" className="w-[30%] py-2 pr-3 font-semibold">Stat</th>
                <th scope="col" className="py-2 pr-3 font-semibold">
                  <Link className="text-accent underline underline-offset-2" href={`/metro/${a}?${qs}`}>{titles[a]}</Link>
                </th>
                <th scope="col" className="py-2 pr-3 font-semibold">
                  <Link className="text-accent underline underline-offset-2" href={`/metro/${b}?${qs}`}>{titles[b]}</Link>
                </th>
                <th scope="col" className="py-2 font-semibold">Difference</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-rule align-baseline">
                <th scope="row" className="py-2 pr-3 text-left font-normal text-ink">Rank</th>
                {[rowA, rowB].map((r, i) => (
                  <td key={i} className="num py-2 pr-3">
                    {isRanked(r) ? (
                      <span className="font-serif text-lg font-semibold">#{r.rank}</span>
                    ) : (
                      <span className="text-ink-2">{r ? policy[r.reason] : "not in this build"}</span>
                    )}
                  </td>
                ))}
                <td className="py-2 text-ink-3">—</td>
              </tr>
              <tr className="border-t border-rule-2 align-baseline">
                <th scope="row" className="py-2 pr-3 text-left font-normal text-ink">Score</th>
                {[rowA, rowB].map((r, i) => (
                  <td key={i} className="num py-2 pr-3">
                    {isRanked(r) ? r.score.toFixed(1) : <span className="text-ink-3">—</span>}
                  </td>
                ))}
                <td className="py-2 text-ink-3">—</td>
              </tr>
              <tr className="border-t border-rule-2 align-baseline">
                <th scope="row" className="py-2 pr-3 text-left font-normal text-ink">
                  {meta.features.pool_size.display_name}
                </th>
                {[rowA, rowB].map((r, i) => (
                  <td key={i} className="py-2 pr-3">
                    {isRanked(r) ? (
                      <span className="whitespace-nowrap">
                        <span className="num font-semibold">{fmtInt(r.pool)}</span>{" "}
                        <span className="text-ink-2">
                          {policy.margin_row} <span className="num">±{fmtInt(r.pool_moe)}</span>
                        </span>
                      </span>
                    ) : (
                      <span className="text-ink-2">{r ? policy[r.reason] : "—"}</span>
                    )}
                  </td>
                ))}
                <td className="py-2 text-xs text-ink-3">
                  each pool carries its own margin; a difference would not
                </td>
              </tr>
              <tr className="border-t border-rule-2 align-baseline">
                <th scope="row" className="py-2 pr-3 text-left font-normal text-ink">
                  {meta.features.partners_per_rival.display_name}
                </th>
                {[rowA, rowB].map((r, i) => {
                  const s = isRanked(r) ? statOf(r, "partners_per_rival") : undefined;
                  return (
                    <td key={i} className="num py-2 pr-3">
                      {s?.display ?? <span className="text-ink-3">—</span>}
                    </td>
                  );
                })}
                <td className="py-2 text-ink-3">—</td>
              </tr>

              {statIds
                .filter((id) => !["pool_size", "partners_per_rival"].includes(id))
                .map((id) => {
                  const le = meta.features[id];
                  const sA = statOf(rowA, id);
                  const sB = statOf(rowB, id);
                  const diff = staticDiff(sA, sB, meta, id);
                  return (
                    <tr key={id} className="border-t border-rule-2 align-baseline">
                      <th scope="row" className="py-2 pr-3 text-left font-normal">
                        <span className="text-ink">{le.display_name}</span>{" "}
                        <span className="text-xs text-ink-3">{le.unit}</span>
                      </th>
                      {[sA, sB].map((s, i) => (
                        <td key={i} className="num py-2 pr-3">
                          {s && s.value !== null && s.value !== undefined ? (
                            <>
                              {s.display}
                              {s.moe_display !== undefined && (
                                <span className="text-ink-2"> ±{s.moe_display}</span>
                              )}
                              {s.contribution !== undefined && s.contribution !== null && (
                                <span
                                  className={`ml-2 text-xs ${s.contribution >= 0 ? "text-pass" : "text-crit"}`}
                                >
                                  {signedPoints(s.contribution)} pts
                                </span>
                              )}
                            </>
                          ) : (
                            <span className="text-ink-3">not available</span>
                          )}
                        </td>
                      ))}
                      <td className="num py-2">{diff ?? <span className="text-ink-3">—</span>}</td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
        <p className="mt-3 max-w-[68ch] text-xs text-ink-3">
          Effects on score are the exact linear attribution under your current
          weights, against the median of this query&apos;s ranked set. The
          difference column is plain subtraction of the two values shown and
          applies only to static stats — never to a population figure, which
          would then lack a margin.
        </p>
      </main>
    </>
  );
}

/** Display-formatted subtraction of two static-stat values — the one
 * deliberate piece of client arithmetic, specified by ADR 0003's compare
 * page, and applied only where no margin is owed. */
function staticDiff(
  sA: Stat | undefined,
  sB: Stat | undefined,
  meta: Meta,
  id: string,
): string | null {
  if (!sA || !sB) return null;
  if (sA.value === null || sA.value === undefined) return null;
  if (sB.value === null || sB.value === undefined) return null;
  if (id === "cross_group_pairing_rate") return null; // carries its own margin
  const le = meta.features[id];
  const d = (sA.value - sB.value) * (le.display_scale ?? 1);
  const nd = le.display_decimals ?? 1;
  const sign = d >= 0 ? "+" : "−";
  return `${sign}${Math.abs(d).toLocaleString("en-US", {
    minimumFractionDigits: nd,
    maximumFractionDigits: nd,
  })}`;
}
