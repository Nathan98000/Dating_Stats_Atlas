import { apiMeta, apiRank } from "@/lib/api";
import { parsePrefs, toRankBody, type SearchParams } from "@/lib/prefs";
import { Home } from "@/components/home";
import { Hero } from "@/components/hero";
import { SiteHeader } from "@/components/chrome";

export const dynamic = "force-dynamic";

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const prefs = parsePrefs(sp);
  const [meta, response] = await Promise.all([
    apiMeta(),
    apiRank(toRankBody(prefs)),
  ]);
  return (
    <>
      <SiteHeader border={false} />
      <Hero />
      <Home meta={meta} initialPrefs={prefs} initialResponse={response} />
    </>
  );
}
