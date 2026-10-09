import Link from "next/link";
import { BackToResults } from "@/components/back-link";
import { notFound } from "next/navigation";
import { apiMeta, apiPoliticalLean, apiProfile, apiRank } from "@/lib/api";
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
import { SiteFooter, SiteHeader } from "@/components/chrome";
import { CompareVariantRows } from "@/components/compare-variant";
import { DiffCell, edgeOf, Row, ValueCell } from "@/components/compare-cells";
import { PoliticalLeanCell } from "@/components/political-lean";
import { toneText } from "@/lib/tones";
import { CHROME, pageMetadata, pageTitle } from "@/lib/chrome";
import { fill } from "@/lib/results";
import { sliceVariants } from "@/lib/variants";
import type { BaseRow, BaseSuppressedRow, Card } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ a: string; b: string }> }) {
  const { a, b } = await params;
  const meta = await apiMeta();
  const mA = meta.metros.find((m) => m.slug === a);
  const mB = meta.metros.find((m) => m.slug === b);
  if (!mA || !mB) return {};
  return pageMetadata(
    pageTitle(fill(CHROME.title_compare_pair, { a: mA.display_name, b: mB.display_name })),
    meta.policy_strings.compare_page_subtitle, `/compare/${a}/${b}`);
}

/** Two cities side by side, from ONE rank response so both sit under the
 * same normalization. Phase 2f item 6 (ADR 0007, reversing ADR 0003's
 * "pools get no difference"): EVERY row gets a difference, computed as
 * plain subtraction of the two DISPLAYED values — parsed back from the
 * display strings themselves, so the equality with what the visitor
 * sees holds by construction and nothing is recomputed from raw values.
 * Phase 5: the Edge column names the city a difference favours for this
 * visitor (A − B read through the registry's direction field), a dash
 * where the site doesn't judge (population always; a pillar set to Not
 * much, which still carries weight; anything without a direction). */
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
  const [meta, response, lean] = await Promise.all([
    apiMeta(),
    apiRank(toRankBody(prefs)),
    apiPoliticalLean(),
  ]);
  const mA = meta.metros.find((m) => m.slug === a);
  const mB = meta.metros.find((m) => m.slug === b);
  if (!mA || !mB) notFound();
  const [profileA, profileB] = await Promise.all([apiProfile(mA.cbsa), apiProfile(mB.cbsa)]);

  const find = (cbsa: string): BaseRow | BaseSuppressedRow | undefined =>
    response.ranked.find((r) => r.cbsa === cbsa) ??
    response.suppressed.find((r) => r.cbsa === cbsa);
  // each city's stat cards and crime are its profile, which no search
  // changes and every metro has, below the ranked set's floor included; an
  // API from before /v1/profile leaves the search row's copy
  const profA = profileA ?? find(mA.cbsa);
  const profB = profileB ?? find(mB.cbsa);
  const slice = sliceVariants(response, [mA.cbsa, mB.cbsa]);
  const qs = toSearchParams(prefs).toString();
  const policy = meta.policy_strings;
  const cardOf = (r: { cards: Card[] } | undefined, id: string): Card | undefined =>
    r?.cards.find((c) => c.id === id);
  const cityA = mA.display_name_full.split(",")[0];
  const cityB = mB.display_name_full.split(",")[0];

  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto flex max-w-5xl flex-col gap-6 px-4 pb-16 pt-8 sm:px-12">
        <BackToResults href={`/?${qs}`}>← Back to your results</BackToResults>
        <h1 className="font-display text-h2">
          {cityA} <span className="text-ink-3">and</span> {cityB}
        </h1>
        <p className="max-w-[64ch] text-body text-ink-2">
          For {describeSearch(prefs).toLowerCase()} — the same search and the
          same yardstick as your results.
        </p>
        {isDefaultSearch(sp) && !fromCookie && (
          <p className="max-w-[64ch] rounded-md border border-warning bg-warning-soft px-4 py-3 text-body-sm text-warning" data-testid="default-profile-note">
            {policy.compare_default_note.replace(
              "{search}", describeSearch(prefs).toLowerCase())}{" "}
            <Link href={`/?${qs}#search-panel`} className="font-bold underline underline-offset-2">
              Make it your search
            </Link>
          </p>
        )}

        {/* Phase 5: a table from 640px; below that each measure is a block,
            the two cities side by side under a sticky row naming them (no
            sideways scroll) */}
        <div className="rounded-lg border border-rule bg-surface">
          <table role="table" className="block w-full text-body-sm sm:table" data-testid="compare-table">
            <caption className="sr-only">
              {mA.display_name_full} compared with {mB.display_name_full}
            </caption>
            <thead role="rowgroup" className="sticky top-0 z-10 block rounded-t-lg bg-surface sm:static sm:table-header-group">
              <tr role="row" className="grid grid-cols-2 border-b border-rule text-left sm:table-row">
                <td className="w-[26%] max-sm:hidden" />
                {[mA, mB].map((m) => (
                  <th key={m.slug} role="columnheader" scope="col" className="px-4 py-3 sm:px-5 sm:py-3.5">
                    <Link
                      href={`/city/${m.slug}?${qs}`}
                      className="inline-flex items-center max-desk:min-h-11 font-display text-title text-ink hover:text-accent-hover"
                    >
                      {m.display_name}
                    </Link>
                  </th>
                ))}
                <th role="columnheader" scope="col" className="px-5 py-3.5 text-caption font-semibold text-ink-3 max-sm:hidden">
                  {policy.compare_edge}
                </th>
              </tr>
            </thead>
            <tbody role="rowgroup" className="block sm:table-row-group">
              {/* item 6.1 and the people rows: spot, score, the
                  compatibility figure and balance — what an "about you"
                  variant changes, selected in the browser (m4.0.0) */}
              <CompareVariantRows
                slice={slice}
                cbsaA={mA.cbsa}
                cbsaB={mB.cbsa}
                nameA={cityA}
                nameB={cityB}
                meta={meta}
              />
              {meta.city_cards.map((id) => {
                const le = meta.features[id];
                const cA = cardOf(profA, id);
                const cB = cardOf(profB, id);
                const grey = greyRule(id, le.pillar, le.direction, prefs);
                const edge = edgeOf(cA?.display, cB?.display, grey ? 0 : le.direction, grey);
                return (
                  <Row key={id} label={le.display_name}>
                    {[cA, cB].map((c, i) => (
                      <ValueCell key={i} win={edge === (i === 0 ? 1 : -1)} edgeLabel={policy.compare_edge}>
                        {c && c.display !== undefined ? (
                          <div className="flex flex-col">
                            <span className="text-body font-semibold">
                              {id === "rent_1br" ? "$" : ""}
                              {c.display}
                            </span>
                            {c.band && (
                              <span className={`text-overline tracking-normal ${toneText(c.band.tone)}`}>
                                {c.band.label}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-caption text-ink-3">
                            {policy.card_missing}
                          </span>
                        )}
                      </ValueCell>
                    ))}
                    <DiffCell
                      id={id}
                      names={[cityA, cityB]}
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
              {/* Phase 4d (ADR 0019): political lean, context only — both
                  cities' shares as their city cards say them. No
                  difference: one would put one party's share against the
                  other city's, so the cell stays empty */}
              {meta.features.political_lean && Object.keys(lean.metros).length > 0 && (
                <Row label={meta.features.political_lean.display_name}>
                  <PoliticalLeanCell block={lean.metros[mA.cbsa]} />
                  <PoliticalLeanCell block={lean.metros[mB.cbsa]} />
                  <td role="cell" className="px-5 py-3.5 max-sm:hidden" data-no-diff="political_lean" />
                </Row>
              )}
            </tbody>
          </table>
        </div>
        {/* Phase 5: what the Edge column says, from the registry — a dash
            is "we don't judge it", never "this is excluded" */}
        <p className="max-w-[76ch] text-caption text-ink-3" data-testid="diff-legend">
          {policy.compare_edge_note}
        </p>

        {/* Phase 2e item 11, reworded in 2f item 6.4: two numbers per
            city, ONE plain banner above them, the detail one click away —
            and the unit line says per 100,000 so nobody reads a rate as
            a count (item 6.5). */}
        <section className="flex flex-col gap-4 rounded-lg border border-rule bg-surface px-4 py-6 sm:px-7" data-testid="compare-crime">
          <h2 className="font-display text-h3">Reported crime</h2>
          <p
            className="max-w-[76ch] rounded-md border border-warning bg-warning-soft px-4 py-3 text-caption text-warning"
            data-testid="crime-compare-banner"
          >
            {(profA?.crime ?? profB?.crime)?.compare_banner}{" "}
            <Link href="/about-crime-data" className="font-semibold underline underline-offset-2">
              {policy.crime_see_more}
            </Link>
            .
          </p>
          <table className="w-full max-w-[560px] text-body-sm">
            <thead>
              <tr className="border-b border-rule text-left">
                <td />
                {[mA, mB].map((m) => (
                  <th key={m.slug} scope="col" className="py-2 pr-4 text-body-sm font-semibold">
                    {m.display_name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(["violent_crime_rate", "property_crime_rate"] as const).map((fid) => (
                <tr key={fid} className="border-b border-rule last:border-b-0">
                  <th scope="row" className="py-2.5 pr-4 text-left align-top">
                    <span className="block text-caption font-semibold text-ink-2">
                      {meta.features[fid].display_name}
                    </span>
                    <span className="block max-w-[22ch] text-overline font-normal tracking-normal text-ink-3">
                      {meta.features[fid].unit}
                    </span>
                  </th>
                  {[profA, profB].map((r, i) => {
                    const s = r?.crime?.stats?.find((x) => x.id === fid);
                    return (
                      <td key={i} className="py-2.5 pr-4 align-top">
                        {s ? (
                          <span className="text-data-m">{s.display}</span>
                        ) : (
                          <span className="text-caption text-ink-3">
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
      </main>
      <SiteFooter />
    </>
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
