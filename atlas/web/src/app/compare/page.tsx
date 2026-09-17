import { Suspense } from "react";
import { SiteHeader } from "@/components/chrome";
import { ComparePickers } from "@/components/compare-pickers";
import { one, type SearchParams } from "@/lib/prefs";

export const dynamic = "force-dynamic";

/** The compare landing (item 8), reachable from the nav: two city
 * pickers over the same client-side index, pre-filled from ?a=&b= when
 * present. The side-by-side view they lead to renders both cities from
 * one ranking response — a visitor with no preferences set gets the
 * stated default profile there, labelled and one click from theirs. */
export default async function CompareLandingPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const a = one(sp, "a");
  const b = one(sp, "b");
  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto flex max-w-3xl flex-col gap-6 px-6 pb-16 pt-12 sm:px-12">
        <div className="flex flex-col gap-2.5">
          <h1 className="font-display text-[38px] font-semibold leading-tight tracking-tight">
            Compare two cities
          </h1>
          <p className="max-w-[58ch] text-[15.5px] leading-relaxed text-ink-2">
            Side by side: where each lands for your search, the size and
            balance of its dating pool, and every place stat with the
            difference between them.
          </p>
        </div>
        <Suspense fallback={<div className="h-[120px]" />}>
          <ComparePickers initialA={a} initialB={b} />
        </Suspense>
      </main>
    </>
  );
}
