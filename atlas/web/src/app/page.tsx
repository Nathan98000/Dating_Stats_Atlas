import { apiMeta, apiRank } from "@/lib/api";
import { describeSearchShort, parsePrefs, PREF_KEYS, toRankBody, toSearchParams,
  type SearchParams } from "@/lib/prefs";
import { fill } from "@/lib/results";
import { effectiveSearchParams } from "@/lib/server-prefs";
import { Home } from "@/components/home";
import { SiteFooter, SiteHeader } from "@/components/chrome";
import { cardPhotos } from "@/lib/city-photos";
import { HOME_OG_IMAGE, pageMetadata, pageTitle, resultsTitle } from "@/lib/chrome";

export const dynamic = "force-dynamic";

/** Phase 6 (F31): a home URL carrying a search is a shared result — its
 * title is the results heading and its og:url the URL itself; a bare URL
 * is the site's front page. Both preview with the home image. */
export async function generateMetadata({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const meta = await apiMeta();
  const ps = meta.policy_strings;
  const raw = await searchParams;
  const qs = new URLSearchParams(
    Object.entries(raw).flatMap(([k, v]) => (PREF_KEYS as readonly string[]).includes(k) && v !== undefined
      ? [[k, Array.isArray(v) ? v[0] : v] as [string, string]] : []));
  if (![...qs.keys()].length) {
    return pageMetadata(pageTitle(), ps.home_subtitle, "/", HOME_OG_IMAGE);
  }
  const prefs = parsePrefs(raw);
  const heading = fill(prefs.sort === "worst_first" ? ps.results_heading_worst : ps.results_heading_best,
    describeSearchShort(prefs));
  return pageMetadata(resultsTitle(ps, heading), ps.home_subtitle, `/?${toSearchParams(prefs).toString()}`,
    HOME_OG_IMAGE);
}

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  // explicit URL parameters always win; a bare URL falls back to the
  // visitor's own last search (Phase 2f item 2 / ADR 0007)
  const { sp } = await effectiveSearchParams(await searchParams);
  const prefs = parsePrefs(sp);
  const [meta, response] = await Promise.all([
    apiMeta(),
    apiRank(toRankBody(prefs)),
  ]);
  return (
    <>
      <SiteHeader />
      <Home meta={meta} initialPrefs={prefs} initialResponse={response} photos={cardPhotos()} />
      <SiteFooter />
    </>
  );
}
