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
import { FlagChips, PoolFigure } from "@/components/figures";
import { StatsTable } from "@/components/stats-table";
import { CompareLauncher } from "@/components/compare-launcher";
import { fmtInt } from "@/lib/format";

export const dynamic = "force-dynamic";

const PREF_KEYS = ["self_sex", "self_age", "sex", "age", "marital", "edu", "inc", "race", "s", "w"];

/** Metro pages have two layers (§10.5): the objective profile stands alone
 * for a visitor with no preferences; the personalised layer appears above
 * it once preferences exist. Pool and odds are per-query quantities, so
 * they live ONLY in the personalised layer — the objective profile is the
 * metro's static stats, its pairing composition, and the crime context
 * with the FBI's own caveat (D01). An unranked metro gets the explicit
 * not-enough-sample state (D03): an honest empty state, not a bad number. */
export default async function MetroPage({
  params,
  searchParams,
}: {
  params: Promise<{ cbsa: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const { cbsa } = await params;
  const sp = await searchParams;
  const hasPrefs = PREF_KEYS.some((k) => sp[k] !== undefined);
  const prefs = parsePrefs(sp);
  const [meta, response] = await Promise.all([
    apiMeta(),
    apiRank(toRankBody(prefs)),
  ]);
  const known = meta.metros.find((m) => m.cbsa === cbsa);
  if (!known) notFound();

  const ranked = response.ranked.find((r) => r.cbsa === cbsa);
  const suppressed = response.suppressed.find((r) => r.cbsa === cbsa);
  const policy = meta.policy_strings;
  const qs = toSearchParams(prefs).toString();
  const staticStats = (ranked ?? suppressed)?.stats.filter(
    (s) => meta.features[s.id]?.pillar !== "pool" && meta.features[s.id]?.pillar !== "balance",
  ) ?? [];
  const pairing = (ranked ?? suppressed)?.stats.find(
    (s) => s.id === "cross_group_pairing_rate",
  );
  const crime = meta.features.crime_rate_context;

  return (
    <>
      <Masthead dataVersion={meta.data_version} modelVersion={meta.model_version} />
      <main id="main" className="mx-auto max-w-4xl px-5">
        <p className="text-xs text-ink-3">
          <Link href={`/?${qs}`} className="text-accent underline underline-offset-2">
            ← back to the ranking
          </Link>
        </p>
        <h1 className="mt-2 font-serif text-4xl font-semibold tracking-tight">
          {known.title}
        </h1>
        <p className="num mt-1 text-xs text-ink-3">CBSA {cbsa}</p>

        {/* ------------- personalised layer (only when preferences exist) */}
        {hasPrefs && (
          <section aria-labelledby="for-you" className="mt-6 border-l-2 border-accent pl-4">
            <h2 id="for-you" className="font-serif text-xl font-semibold">
              For {describePrefs(prefs)}
            </h2>
            {ranked ? (
              <div className="mt-2 flex flex-col gap-2 text-sm">
                <p>
                  Ranks{" "}
                  <span className="num text-lg font-semibold text-ink">#{ranked.rank}</span>{" "}
                  of <span className="num">{fmtInt(response.counts.ranked)}</span> ranked
                  metros, score <span className="num">{ranked.score.toFixed(1)}</span>.
                </p>
                <p className="flex flex-wrap items-baseline gap-x-2">
                  <PoolFigure
                    pool={ranked.pool}
                    moe={ranked.pool_moe}
                    marginWords={policy.margin_row}
                    label={meta.features.pool_size.display_name}
                    size="lg"
                  />
                  {prefs.race?.length ? (
                    ranked.cross_group_pairing_rate !== null ? (
                      <span className="text-ink-2">
                        <span className="text-ink-3">·</span>{" "}
                        <span className="num font-semibold text-ink">
                          {ranked.cross_group_pairing_display}%
                        </span>{" "}
                        {meta.features.cross_group_pairing_rate.display_name.toLowerCase()}{" "}
                        <span className="num">±{ranked.cross_group_pairing_moe_display}pp</span>
                      </span>
                    ) : (
                      <span className="text-ink-2">
                        <span className="text-ink-3">·</span> pairing rate:{" "}
                        {policy[ranked.cross_group_pairing_suppressed ?? "n_below_100"]}
                      </span>
                    )
                  ) : null}
                </p>
                <p className="max-w-[68ch] text-ink-2">{ranked.explanation}</p>
                <FlagChips flags={ranked.flags} policy={policy} />
                <div className="mt-2">
                  <h3 className="mb-1 text-sm font-semibold">
                    Every stat, under your weights
                  </h3>
                  <StatsTable
                    stats={ranked.stats}
                    meta={meta}
                    withContributions
                    caption={`Every stat for ${known.title} under the current preferences`}
                  />
                </div>
              </div>
            ) : suppressed ? (
              <div className="mt-2 text-sm" data-testid="suppressed-state">
                <p className="max-w-[60ch] text-ink">
                  Not enough sample to rank this metro for this profile.
                </p>
                <p className="mt-1 max-w-[60ch] text-ink-2">
                  {policy[suppressed.reason]}{" "}
                  <span className="num">
                    ({fmtInt(suppressed.n_unweighted)} effective respondents;
                    the bar is 100.)
                  </span>{" "}
                  An honest blank beats a bad number — widen an age band or
                  drop a filter and it may clear the bar.
                </p>
                <p className="mt-1 text-xs">
                  <Link href="/methodology#suppression" className="text-accent underline underline-offset-2">
                    How suppression is decided
                  </Link>
                </p>
              </div>
            ) : (
              <p className="mt-2 max-w-[60ch] text-sm text-ink-2" data-testid="below-floor-state">
                This metro is below the ranking universe&apos;s population floor,
                so it is never ranked — its objective profile is below.
              </p>
            )}
          </section>
        )}

        {/* ------------- objective profile (stands alone, §10.5) */}
        <section aria-labelledby="objective" className="mt-8">
          <h2 id="objective" className="font-serif text-xl font-semibold">
            The place itself
          </h2>
          <p className="mt-1 max-w-[64ch] text-sm text-ink-2">
            Static stats, independent of anyone&apos;s preferences. Standing is
            the metro&apos;s percentile among the{" "}
            <span className="num">{fmtInt(response.counts.ranked)}</span> metros ranked for{" "}
            {hasPrefs ? "the current profile" : "the default profile"}
            {hasPrefs ? "" : " (no preferences are set)"}. Pool and odds exist
            only for a specific search, so they appear in the layer above once
            preferences are set.
          </p>
          {staticStats.length > 0 ? (
            <div className="mt-3">
              <StatsTable
                stats={staticStats.filter((s) => s.id !== "cross_group_pairing_rate")}
                meta={meta}
                withContributions={Boolean(hasPrefs && ranked)}
                caption={`Static context stats for ${known.title}`}
              />
            </div>
          ) : (
            <p className="mt-3 text-sm text-ink-2">
              No stats block arrived for this metro — this is a bug worth
              reporting, not a gap in the data.
            </p>
          )}

          {pairing && (
            <div className="mt-6 max-w-[68ch] text-sm">
              <h3 className="font-semibold">How couples here actually pair</h3>
              {pairing.value !== null && pairing.value !== undefined ? (
                <p className="mt-1 text-ink-2">
                  Among all partnered adults here,{" "}
                  <span className="num font-semibold text-ink">{pairing.display}%</span>{" "}
                  <span className="num">±{pairing.moe_display}pp</span> are partnered
                  outside their own racial or ethnic group.{" "}
                  {policy.pairing_framing} {policy.pairing_interval}
                </p>
              ) : (
                <p className="mt-1 text-ink-2">{policy.n_below_100}</p>
              )}
            </div>
          )}

          <div className="mt-6 max-w-[68ch] text-sm" data-testid="crime-context">
            <h3 className="font-semibold">{crime.display_name}</h3>
            <p className="mt-1 text-ink-2">{crime.definition}</p>
            <p className="mt-1 text-ink-2">
              Context data has not shipped yet: the FBI publishes no
              metro-level table in the current NIBRS era, and building one
              from agency records is exactly the aggregation the FBI&apos;s{" "}
              <a
                className="text-accent underline underline-offset-2"
                href="https://www.fbi.gov/file-repository/ucr/ucr-statistics-their-proper-use.pdf/view"
                rel="noopener"
              >
                caution against ranking
              </a>{" "}
              warns about, so it is deferred rather than improvised. When it
              ships it appears here with that caution attached — and it is
              never part of any score.
            </p>
          </div>
        </section>

        <section className="mt-8 border-t border-rule pt-4">
          <h2 className="text-sm font-semibold">Compare with another metro</h2>
          <CompareLauncher cbsa={cbsa} />
        </section>
      </main>
    </>
  );
}
