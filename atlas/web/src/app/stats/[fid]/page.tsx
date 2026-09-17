import Link from "next/link";
import { notFound } from "next/navigation";
import { SiteHeader } from "@/components/chrome";
import statPages from "@/data/stat-pages.json";

/** One page per static statistic (item 9): the 193 ranked-set cities —
 * the same universe the search list returns — ordered on that one
 * measure. Served entirely from the build-time JSON: no API call, no
 * recomputation, and the numbers are the city pages' numbers by
 * construction (same artifact, same formatting code, asserted by e2e).
 * Matches and balance never get one of these — they depend on the
 * visitor's search — and crime gets an explainer instead of a ranking. */

interface StatRow {
  slug: string;
  name: string;
  display: string;
  unit_line: string;
  pos: number;
  band: { label: string; tone: string; key: string } | null;
}

const DATA = statPages as unknown as {
  pages: Record<string, { title: string; unit: string; definition: string;
                          rows: StatRow[]; missing_in_ranked_set: number }>;
  order: string[];
  strings: { intro: string; missing: string };
};

export function generateStaticParams() {
  return DATA.order.map((fid) => ({ fid }));
}

export default async function StatPage({
  params,
}: {
  params: Promise<{ fid: string }>;
}) {
  const { fid } = await params;
  const page = DATA.pages[fid];
  if (!page) notFound();
  const isDollar = fid === "median_gross_rent";

  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto flex max-w-3xl flex-col gap-6 px-6 pb-16 pt-10 sm:px-12">
        <div className="flex flex-col gap-2.5">
          <h1 className="font-display text-[38px] font-semibold leading-tight tracking-tight">
            Cities by {page.title.toLowerCase()}
          </h1>
          <p className="max-w-[64ch] text-[15px] leading-relaxed text-ink-2">
            {page.definition}
          </p>
          <p className="max-w-[64ch] text-[13.5px] text-ink-3">
            {DATA.strings.intro}
          </p>
        </div>
        <ol aria-label={`Cities by ${page.title.toLowerCase()}`} data-testid="stat-list">
          {page.rows.map((r) => (
            <li
              key={r.slug}
              className="grid grid-cols-[44px_1fr_auto] items-baseline gap-x-4 border-b border-rule py-3"
              data-slug={r.slug}
            >
              <span aria-hidden="true" className="font-display text-[19px] font-semibold text-ink-3">
                {r.pos}
              </span>
              <span className="min-w-0">
                <Link
                  href={`/city/${r.slug}`}
                  className="text-[15.5px] font-semibold hover:text-accent-hover hover:underline"
                >
                  <span className="sr-only">{r.pos}: </span>
                  {r.name}
                </Link>
                {r.band && (
                  <span
                    className={`ml-2.5 text-[12px] font-semibold ${
                      r.band.tone === "good" ? "text-good"
                      : r.band.tone === "poor" ? "text-poor" : "text-ink-3"}`}
                  >
                    {r.band.label}
                  </span>
                )}
              </span>
              <span className="text-right">
                <span className="font-display text-[19px] font-semibold">
                  {isDollar ? "$" : ""}
                  {r.display}
                </span>
                <span className="ml-1.5 hidden text-[12px] text-ink-3 sm:inline">
                  {r.unit_line}
                </span>
              </span>
            </li>
          ))}
        </ol>
        {page.missing_in_ranked_set > 0 && (
          <p className="text-[13px] text-ink-3">
            {DATA.strings.missing.replace(
              "{n}", page.missing_in_ranked_set.toLocaleString("en-US"))}
          </p>
        )}
      </main>
    </>
  );
}
