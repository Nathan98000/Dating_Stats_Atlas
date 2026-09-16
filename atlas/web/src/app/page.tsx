import { apiMeta, apiRank } from "@/lib/api";
import { parsePrefs, toRankBody, type SearchParams } from "@/lib/prefs";
import { Explorer } from "@/components/explorer";
import { Masthead } from "@/components/masthead";

export const dynamic = "force-dynamic";

/** Open on results, not on a form (§10.2): the first ranking is
 * server-rendered from the URL's preferences (or the stated default
 * profile), controls beside it. */
export default async function RankingPage({
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
      <Masthead
        dataVersion={meta.data_version}
        modelVersion={meta.model_version}
        brandAsH1
      />
      <Explorer meta={meta} initialPrefs={prefs} initialResponse={response} />
    </>
  );
}
