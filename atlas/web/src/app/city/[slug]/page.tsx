import Link from "next/link";
import { notFound } from "next/navigation";
import { apiMeta, apiPoliticalLean, apiRank } from "@/lib/api";
import {
  describeSearch,
  parsePrefs,
  toRankBody,
  toSearchParams,
  type SearchParams,
} from "@/lib/prefs";
import { effectiveSearchParams } from "@/lib/server-prefs";
import { SiteHeader } from "@/components/chrome";
import { LocatorMap } from "@/components/locator-map";
import { CityArt } from "@/components/city-art";
import { CityVariantPart } from "@/components/city-variant";
import { sliceVariants } from "@/lib/variants";
import { CityNarrowCard, CityWideners } from "@/components/city-cards";
import { CompareLauncher } from "@/components/compare-launcher";
import { CrimeCards } from "@/components/crime-cards";
import { PoliticalLeanCard } from "@/components/political-lean";
import { toneSeg, toneText } from "@/lib/tones";
import type { Card } from "@/lib/types";

export const dynamic = "force-dynamic";

/** The v3 city page (MetroV3): name, the one-line description (from the
 * build, never hand-written), locator map, the for-your-search card —
 * ranked, or the approved hard-to-answer card with one-click wideners —
 * then the stat cards with their standing bands, and the compare CTA.
 * m4.0.0 (ADR 0018): what an "about you" variant changes (the ranked
 * card, a left-out city's balance) is selected in the browser from this
 * city's slice of the response (components/city-variant). */
export default async function CityPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const { slug } = await params;
  // explicit URL parameters always win; a bare URL falls back to the
  // visitor's own last search (Phase 2f item 2 / ADR 0007)
  const { sp } = await effectiveSearchParams(await searchParams);
  const prefs = parsePrefs(sp);
  const [meta, response, lean] = await Promise.all([
    apiMeta(),
    apiRank(toRankBody(prefs)),
    apiPoliticalLean(),
  ]);
  const metro = meta.metros.find((m) => m.slug === slug);
  if (!metro) notFound();

  const ranked = response.ranked.find((r) => r.cbsa === metro.cbsa);
  const suppressed = response.suppressed.find((r) => r.cbsa === metro.cbsa);
  const slice = sliceVariants(response, [metro.cbsa]);
  const qs = toSearchParams(prefs).toString();
  const policy = meta.policy_strings;
  const cards: Card[] = (ranked ?? suppressed)?.cards ?? [];
  const crime = (ranked ?? suppressed)?.crime;
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
          <LocatorMap focus={metro} />
        </div>

        {/* item 7: every page gets a face — deterministic artwork in the
            site palette, overridden by a photo when one exists */}
        <CityArt cbsa={metro.cbsa} slug={slug} />

        {/* for-your-search: the ranked card, or the approved narrow card */}
        {ranked ? (
          <CityVariantPart
            part="ranked"
            slice={slice}
            cbsa={metro.cbsa}
            city={city}
            searchWords={describeSearch(prefs).toLowerCase()}
            meta={meta}
          />
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

        {suppressed && (
          <CityVariantPart
            part="balance"
            slice={slice}
            cbsa={metro.cbsa}
            city={city}
            searchWords={describeSearch(prefs).toLowerCase()}
            meta={meta}
          />
        )}

        <section className="flex flex-col gap-4">
          <h2 className="font-display text-[26px] font-semibold">
            What {city} is like
          </h2>
          {/* item 5.2: each card is a SUBGRID over six shared rows (name /
              value / unit / segments / band label / link), so the
              five-segment indicators sit at one height across a row of
              cards even when a neighbour's unit line wraps */}
          <div className="grid grid-cols-4 gap-4 max-lg:grid-cols-3 max-md:grid-cols-2 max-sm:grid-cols-1">
            {cards.map((c) => (
              <StatCard key={c.id} card={c} meta={meta} />
            ))}
            {/* Phase 4d (ADR 0019): political lean, context only, beside
                who lives here — shown with the metro's other cards */}
            {cards.length > 0 && lean.metros[metro.cbsa] && (
              <PoliticalLeanCard block={lean.metros[metro.cbsa]} meta={meta} />
            )}
            {/* item 2 (2e): crime as two cards in the SAME grid — rate,
                band, ⓘ; the FBI's caution lives in the popover */}
            {crime && <CrimeCards crime={crime} meta={meta} />}
            <div className="stat-card !flex flex-col justify-center gap-2.5 rounded-xl border border-tint-border bg-tint p-[18px]">
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
  // item 6 (2d) + Phase 2f item 1: the position label is descriptive;
  // its COLOUR comes from the registry's direction through the served
  // tone — five tones now, extremes reading harder — and the lit
  // segment matches, so "cheapest" can glow deep green while "more
  // students" stays quiet
  const toneColor = toneText(card.band?.tone);
  const segColor = toneSeg(card.band?.tone);
  const isDollar = card.id === "rent_1br";
  const segments = meta.standing_bands.keys;
  const statPage = meta.stat_pages.includes(card.id);
  const statName = (le.stat_page_name ?? le.display_name).toLowerCase();
  const missing = card.missing || card.display === undefined;
  return (
    <div className="stat-card rounded-xl border border-rule bg-surface p-[18px]" data-card={card.id}>
      <span className="text-[13px] font-semibold text-ink-2">{le.display_name}</span>
      {missing ? (
        <>
          <span className="text-sm text-ink-3">
            {meta.policy_strings.card_missing}
          </span>
          <span aria-hidden="true" />
          <span aria-hidden="true" />
          <span aria-hidden="true" />
          <span aria-hidden="true" />
        </>
      ) : (
        <>
          <span className="font-display text-[30px] font-semibold leading-none">
            {isDollar ? "$" : ""}
            {card.display}
          </span>
          <span className="unit-line text-[12.5px] text-ink-3">{card.unit_line}</span>
          {card.band ? (
            <div className="flex gap-1 pt-0.5" aria-hidden="true">
              {segments.map((seg) => (
                <span
                  key={seg}
                  className="h-1.5 flex-1 rounded-full"
                  style={{
                    background:
                      card.band!.key === seg ? segColor : "var(--rule)",
                  }}
                />
              ))}
            </div>
          ) : (
            <span aria-hidden="true" />
          )}
          {card.band ? (
            <span data-testid="band-label" className={`text-[12.5px] font-semibold ${toneColor}`}>
              {card.band.label}
            </span>
          ) : (
            <span aria-hidden="true" />
          )}
          {statPage ? (
            <Link
              href={`/stats/${card.id}`}
              className="self-start text-[12.5px] font-semibold text-accent hover:text-accent-hover"
            >
              {meta.policy_strings.stat_page_link.replace("{name}", statName)}
            </Link>
          ) : (
            <span aria-hidden="true" />
          )}
        </>
      )}
    </div>
  );
}
