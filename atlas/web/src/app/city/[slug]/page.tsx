import Link from "next/link";
import { notFound } from "next/navigation";
import { apiMeta, apiRank } from "@/lib/api";
import {
  describeSearch,
  parsePrefs,
  toRankBody,
  toSearchParams,
  type SearchParams,
} from "@/lib/prefs";
import { SiteHeader } from "@/components/chrome";
import { LocatorMap } from "@/components/locator-map";
import { BalanceTally } from "@/components/tally";
import { CityNarrowCard, CityWideners } from "@/components/city-cards";
import { CompareLauncher } from "@/components/compare-launcher";
import type { Card } from "@/lib/types";

export const dynamic = "force-dynamic";

/** The v3 city page (MetroV3): name, the one-line description (from the
 * build, never hand-written), locator map, the for-your-search card —
 * ranked, or the approved hard-to-answer card with one-click wideners —
 * then the stat cards with their standing bands, and the compare CTA. */
export default async function CityPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const { slug } = await params;
  const sp = await searchParams;
  const prefs = parsePrefs(sp);
  const [meta, response] = await Promise.all([
    apiMeta(),
    apiRank(toRankBody(prefs)),
  ]);
  const metro = meta.metros.find((m) => m.slug === slug);
  if (!metro) notFound();

  const ranked = response.ranked.find((r) => r.cbsa === metro.cbsa);
  const suppressed = response.suppressed.find((r) => r.cbsa === metro.cbsa);
  const qs = toSearchParams(prefs).toString();
  const policy = meta.policy_strings;
  const cards: Card[] = (ranked ?? suppressed)?.cards ?? [];
  const balance = (ranked ?? suppressed)?.balance;
  const city = metro.display_name_full.split(",")[0];

  return (
    <>
      <SiteHeader />
      <div className="mx-auto flex max-w-6xl flex-col gap-7 px-6 pb-16 pt-8 sm:px-12">
        <Link
          href={`/?${qs}`}
          className="text-sm font-semibold text-accent hover:text-accent-hover"
        >
          ← Back to your results
        </Link>

        <div className="grid grid-cols-[1fr_300px] items-center gap-12 max-md:grid-cols-1">
          <div className="flex flex-col gap-3.5">
            <h1 className="font-display text-[48px] font-semibold leading-[1.05] tracking-tight max-sm:text-[34px]">
              {metro.display_name_full}
            </h1>
            <p className="max-w-[52ch] text-[17px] leading-relaxed text-ink-2" data-testid="city-description">
              {metro.description}
            </p>
            <div className="flex flex-wrap gap-3 pt-1">
              <CompareLauncher slug={slug} primary />
              <Link
                href={`/?${qs}#search-panel`}
                className="flex min-h-[46px] items-center rounded-lg border-[1.5px] border-ink px-5 text-[14.5px] font-bold text-ink hover:bg-tint"
              >
                Change your search
              </Link>
            </div>
          </div>
          <LocatorMap metros={meta.metros} focus={metro} />
        </div>

        {/* for-your-search: the ranked card, or the approved narrow card */}
        {ranked ? (
          <section
            className="flex flex-col gap-4 rounded-xl border border-rule bg-surface px-7 py-6"
            data-testid="ranked-card"
          >
            <h2 className="font-display text-[21px] font-semibold">
              Where {city} lands for your search
            </h2>
            <div className="flex flex-wrap items-center gap-x-12 gap-y-4">
              <div className="flex items-baseline gap-2">
                <span className="font-display text-[44px] font-semibold leading-none">
                  {ranked.rank}
                </span>
                <span className="text-sm text-ink-2">
                  of {response.counts.ranked.toLocaleString("en-US")} cities
                  for {describeSearch(prefs).toLowerCase()}
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="font-display text-[30px] font-semibold leading-none">
                  {ranked.pool.toLocaleString("en-US")}
                </span>
                <span className="text-sm text-ink-2">
                  {meta.features.pool_size.unit}
                </span>
              </div>
              <div className="min-w-[220px]">
                <BalanceTally balance={ranked.balance} compact />
              </div>
            </div>
            <p className="max-w-[72ch] text-sm text-ink-2">{ranked.summary_line}</p>
          </section>
        ) : suppressed ? (
          <CityNarrowCard
            city={city}
            search={describeSearch(prefs)}
            policy={policy}
          >
            <CityWideners prefs={prefs} />
          </CityNarrowCard>
        ) : (
          <section className="rounded-xl border border-rule bg-surface px-7 py-6">
            <p className="max-w-[72ch] text-sm leading-relaxed text-ink-2">
              {city} sits below the population floor this site ranks, so it
              never appears in results — its profile is below.
            </p>
          </section>
        )}

        {balance && !ranked && balance.available && (
          <section className="flex flex-col gap-2 rounded-xl border border-rule bg-surface px-7 py-6" data-testid="balance-survives">
            <h2 className="text-[15px] font-semibold">
              {meta.features.pool_balance.display_name} in {city}
            </h2>
            <BalanceTally balance={balance} />
            <p className="max-w-[64ch] text-[12.5px] text-ink-3">
              {policy.balance_caption}
            </p>
          </section>
        )}

        <section className="flex flex-col gap-4">
          <h2 className="font-display text-[26px] font-semibold">
            What {city} is like
          </h2>
          <div className="grid grid-cols-4 gap-4 max-lg:grid-cols-3 max-md:grid-cols-2 max-sm:grid-cols-1">
            {cards.map((c) => (
              <StatCard key={c.id} card={c} meta={meta} />
            ))}
            <div className="flex flex-col justify-center gap-2.5 rounded-xl border border-tint-border bg-tint p-[18px]">
              <span className="font-display text-[17px] font-semibold leading-snug text-accent-hover">
                See how {city} stacks up against a city you know
              </span>
              <CompareLauncher slug={slug} small />
            </div>
          </div>
        </section>
      </div>
    </>
  );
}

function StatCard({ card, meta }: { card: Card; meta: import("@/lib/types").Meta }) {
  const le = meta.features[card.id];
  if (!le) return null;
  const toneColor =
    card.band?.tone === "good" ? "text-good"
    : card.band?.tone === "poor" ? "text-poor"
    : "text-ink-2";
  const isDollar = card.id === "median_gross_rent";
  const segments: ("low" | "mid" | "high")[] = ["low", "mid", "high"];
  return (
    <div className="flex flex-col gap-2.5 rounded-xl border border-rule bg-surface p-[18px]" data-card={card.id}>
      <span className="text-[13px] font-semibold text-ink-2">{le.display_name}</span>
      {card.missing || card.display === undefined ? (
        <span className="text-sm text-ink-3">
          Not available for this city.
        </span>
      ) : (
        <>
          <span className="font-display text-[30px] font-semibold leading-none">
            {isDollar ? "$" : ""}
            {card.display}
          </span>
          <span className="text-[12.5px] text-ink-3">{card.unit_line}</span>
          {card.band && (
            <>
              <div className="flex gap-1 pt-0.5" aria-hidden="true">
                {segments.map((seg) => (
                  <span
                    key={seg}
                    className="h-1.5 flex-1 rounded-full"
                    style={{
                      background:
                        card.band!.key === seg ? "var(--accent)" : "var(--rule)",
                    }}
                  />
                ))}
              </div>
              <span className={`text-[12.5px] font-semibold ${toneColor}`}>
                {card.band.label}
              </span>
            </>
          )}
        </>
      )}
    </div>
  );
}
