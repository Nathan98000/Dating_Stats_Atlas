import { Suspense } from "react";
import Link from "next/link";
import { apiMeta, apiRank } from "@/lib/api";
import { SiteFooter, SiteHeader } from "@/components/chrome";
import { ComparePickers } from "@/components/compare-pickers";
import { one, parsePrefs, toRankBody, toSearchParams, type SearchParams } from "@/lib/prefs";
import { effectiveSearchParams } from "@/lib/server-prefs";
import { fill } from "@/lib/results";

export const dynamic = "force-dynamic";

/** The compare landing (2d item 8), reachable from the nav: two city
 * pickers over the same client-side index, pre-filled from ?a=&b= when
 * present. The subheading arrives from the registry (Phase 2f item 7).
 * Phase 5: under the pickers, a link to the visitor's own top two — the
 * server ranks their search (the effective prefs: the URL, else the
 * cookie) and takes the first two of the default variant, as the home
 * page's server render does. */
export default async function CompareLandingPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const raw = await searchParams;
  const a = one(raw, "a");
  const b = one(raw, "b");
  const { sp } = await effectiveSearchParams(raw);
  const prefs = parsePrefs(sp);
  const [meta, response] = await Promise.all([apiMeta(), apiRank(toRankBody(prefs))]);
  const qs = toSearchParams(prefs).toString();
  // the default variant's order is the order of `ranked` (lib/variants)
  const [first, second] = response.ranked;
  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto flex max-w-3xl flex-col gap-6 px-4 pb-16 pt-12 sm:px-12">
        <div className="flex flex-col gap-2.5">
          <h1 className="font-display text-display-1">
            Compare two cities
          </h1>
          <p className="max-w-[58ch] text-body-lg text-ink-2">
            {meta.policy_strings.compare_page_subtitle}
          </p>
        </div>
        <Suspense fallback={<div className="h-[120px]" />}>
          <ComparePickers initialA={a} initialB={b} />
        </Suspense>
        {first && second && (
          <Link
            href={`/compare/${first.slug}/${second.slug}${qs ? `?${qs}` : ""}`}
            className="flex min-h-11 items-center self-start rounded-md border border-line-strong bg-surface px-5 text-body font-semibold text-ink hover:bg-hover"
            data-testid="compare-top-two"
          >
            {fill(meta.policy_strings.compare_top_two, { a: first.display_name, b: second.display_name })}
          </Link>
        )}
      </main>
      <SiteFooter />
    </>
  );
}
