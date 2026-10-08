import { apiMeta, apiRank } from "@/lib/api";
import { parsePrefs, toRankBody, type SearchParams } from "@/lib/prefs";
import { effectiveSearchParams } from "@/lib/server-prefs";
import { Home } from "@/components/home";
import { SiteFooter, SiteHeader } from "@/components/chrome";
import { cardPhotos } from "@/lib/city-photos";
import { pageMetadata, pageTitle } from "@/lib/chrome";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  const meta = await apiMeta();
  return pageMetadata(pageTitle(), meta.policy_strings.home_subtitle, "/");
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
