import Link from "next/link";
import { notFound } from "next/navigation";
import { apiMeta, apiPoliticalLean, apiProfile, apiRank } from "@/lib/api";
import {
  describeSearch,
  parsePrefs,
  toRankBody,
  toSearchParams,
  type SearchParams,
} from "@/lib/prefs";
import { effectiveSearchParams } from "@/lib/server-prefs";
import { SiteFooter, SiteHeader } from "@/components/chrome";
import { LocatorMap } from "@/components/locator-map";
import { CityArt } from "@/components/city-art";
import { CityVariantPart } from "@/components/city-variant";
import { sliceVariants } from "@/lib/variants";
import { CityNarrowCard, CityWideners } from "@/components/city-cards";
import { CompareLauncher } from "@/components/compare-launcher";
import { CrimeCards } from "@/components/crime-cards";
import { PoliticalLeanCard } from "@/components/political-lean";
import { toneSeg, toneText } from "@/lib/tones";
import { pageMetadata, pageTitle } from "@/lib/chrome";
import { IMAGES, onDisk } from "@/lib/city-photos";
import type { Card } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const meta = await apiMeta();
  const metro = meta.metros.find((m) => m.slug === slug);
  if (!metro) return {};
  const img = IMAGES[slug];
  const image = img && onDisk(img) ? `/cities/${img.file}` : undefined;
  return pageMetadata(pageTitle(metro.display_name), metro.description, `/city/${slug}`, image);
}

/** The v3 city page (MetroV3): name, the one-line description (from the
 * build, never hand-written), locator map, the for-your-search card —
 * ranked, or the approved hard-to-answer card with one-click wideners —
 * then the stat cards with their standing bands, and the compare CTA.
 * m4.0.0 (ADR 0018): what an "about you" variant changes (the ranked
 * card, a left-out city's balance) is selected in the browser from this
 * city's slice of the response (components/city-variant). The stat cards
 * and crime are the metro's profile (POST /v1/profile), which no search
 * changes and every metro has — the 194 below the ranked set's population
 * floor included, which no search returns. */
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
  const profile = await apiProfile(metro.cbsa);

  const ranked = response.ranked.find((r) => r.cbsa === metro.cbsa);
  const suppressed = response.suppressed.find((r) => r.cbsa === metro.cbsa);
  const slice = sliceVariants(response, [metro.cbsa]);
  const qs = toSearchParams(prefs).toString();
  const policy = meta.policy_strings;
  // an API from before /v1/profile: the search row's copy of the same
  // blocks, so a metro below the floor shows none (the old behaviour)
  const cards: Card[] = profile?.cards ?? (ranked ?? suppressed)?.cards ?? [];
  const crime = profile?.crime ?? (ranked ?? suppressed)?.crime;
  const city = metro.display_name_full.split(",")[0];

  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto flex max-w-6xl flex-col gap-7 px-4 pb-16 pt-6 sm:px-12 sm:pt-8">
        <Link
          href={`/?${qs}`}
          className="inline-flex min-h-11 items-center self-start text-body-sm font-semibold text-accent hover:text-accent-hover"
        >
          ← Back to your results
        </Link>

        <div className="grid grid-cols-[1fr_300px] items-center gap-12 max-md:grid-cols-1 max-md:gap-6">
          <div className="flex flex-col gap-3.5">
            {/* Phase 5: on a phone the locator map is a 96px thumbnail
                beside the city's name */}
            <div className="flex items-center gap-4">
              <h1 className="min-w-0 flex-1 font-display text-display-1">
                {metro.display_name_full}
              </h1>
              <div className="w-24 shrink-0 sm:hidden" data-testid="locator-thumb">
                <LocatorMap focus={metro} thumb />
              </div>
            </div>
            <p className="max-w-[52ch] text-body-lg text-ink-2" data-testid="city-description">
              {metro.description}
            </p>
            <div className="flex flex-wrap gap-3 pt-1">
              <CompareLauncher slug={slug} primary />
              <Link
                href={`/?${qs}#search-panel`}
                className="flex min-h-11 items-center rounded-md border border-line-strong bg-surface px-5 text-body font-semibold text-ink hover:bg-hover"
              >
                Change your search
              </Link>
            </div>
          </div>
          <div className="max-sm:hidden">
            <LocatorMap focus={metro} />
          </div>
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
          <section className="rounded-lg border border-rule bg-surface px-5 py-6 sm:px-7">
            <p className="max-w-[72ch] text-body-sm text-ink-2">
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
          <h2 className="font-display text-h2">
            What {city} is like
          </h2>
          {/* item 5.2: each card is a SUBGRID over six shared rows (name /
              value / unit / segments / band label / link), so the
              five-segment indicators sit at one height across a row of
              cards even when a neighbour's unit line wraps */}
          <div className="grid grid-cols-4 gap-4 max-lg:grid-cols-3 max-md:grid-cols-2 max-sm:gap-3">
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
            <div className="stat-card col-span-full !flex flex-col justify-center gap-2.5 rounded-lg border border-rule bg-surface p-[18px] sm:col-span-1">
              <span className="font-display text-title text-ink">
                See how {city} stacks up against a city you know
              </span>
              <CompareLauncher slug={slug} small />
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
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
    <div className="stat-card rounded-lg border border-rule bg-surface p-[18px] max-sm:p-3.5" data-card={card.id}>
      <span className="text-caption font-semibold text-ink-2">{le.display_name}</span>
      {missing ? (
        <>
          <span className="text-body-sm text-ink-3">
            {meta.policy_strings.card_missing}
          </span>
          <span aria-hidden="true" />
          <span aria-hidden="true" />
          <span aria-hidden="true" />
          <span aria-hidden="true" />
        </>
      ) : (
        <>
          <span className="text-data-l max-sm:text-h2 max-sm:leading-none">
            {isDollar ? "$" : ""}
            {card.display}
          </span>
          <span className="unit-line text-caption text-ink-3">{card.unit_line}</span>
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
            <span data-testid="band-label" className={`text-caption font-semibold ${toneColor}`}>
              {card.band.label}
            </span>
          ) : (
            <span aria-hidden="true" />
          )}
          {statPage ? (
            <Link
              href={`/stats/${card.id}`}
              className="inline-flex items-center max-desk:min-h-11 self-start text-caption font-semibold text-accent hover:text-accent-hover"
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
