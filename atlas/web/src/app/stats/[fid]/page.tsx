import fs from "fs";
import path from "path";
import { notFound } from "next/navigation";
import { SiteHeader } from "@/components/chrome";
import { Attribution } from "@/components/attribution";
import { StatList, type StatRow } from "@/components/stat-list";
import statPages from "@/data/stat-pages.json";
import statImages from "@/data/stat-images.json";

/** One page per static statistic (item 9, extended by Phase 2e): a
 * cleared full-width photograph with its recorded attribution, a
 * distribution strip of all ranked cities along the stat's range, and
 * the list itself with a both-ways sort that never renumbers. Served
 * entirely from build-time JSON — no API call, and the numbers are the
 * city pages' numbers by construction. Matches and balance never get a
 * page (they depend on the visitor's search); crime has an explainer
 * instead. */

interface StatImage {
  file: string;
  alt: string | null;
  author: string | null;
  license: string;
  license_url: string | null;
  source_url: string;
}

const DATA = statPages as unknown as {
  pages: Record<string, { title: string; unit: string; definition: string;
                          rows: StatRow[]; missing_in_ranked_set: number;
                          default_is_low_first: boolean;
                          strip: { ticks: number[]; axis: [string, string] };
                          note: string | null }>;
  order: string[];
  strings: { intro: string; missing: string; sort_low: string;
             sort_high: string; strip_label: string };
};
const IMAGES = statImages as unknown as Record<string, StatImage>;

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
  const img = IMAGES[fid];
  const imgExists =
    img && fs.existsSync(path.join(process.cwd(), "public", "stats", img.file));

  return (
    <>
      <SiteHeader />
      {imgExists && (
        <figure className="mx-auto max-w-5xl px-6 pt-6 sm:px-12">
          {/* the photo ships UNMODIFIED — scaled to fit, never cropped
              (an adapted CC-BY-SA image would drag its licence onto the
              adaptation), which is why this is not object-cover */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`/stats/${img.file}`}
            alt={img.alt ?? ""}
            className="max-h-[380px] w-full rounded-xl bg-surface object-contain"
          />
          <figcaption className="pt-1.5">
            <Attribution image={img} />
          </figcaption>
        </figure>
      )}
      <main id="main" className="mx-auto flex max-w-3xl flex-col gap-6 px-6 pb-16 pt-8 sm:px-12">
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
          {page.note && (
            <p className="max-w-[64ch] rounded-lg border border-tint-border bg-tint px-4 py-3 text-[13.5px] leading-relaxed text-accent-hover" data-testid="stat-note">
              {page.note}
            </p>
          )}
        </div>

        {/* item 6: the distribution strip — every ranked city as a tick
            along the stat's own range, axis labelled at the ends */}
        <div data-testid="stat-strip">
          <div
            role="img"
            aria-label={DATA.strings.strip_label}
            className="relative h-8 overflow-hidden rounded-md border border-rule bg-surface"
          >
            {page.strip.ticks.map((t, i) => (
              <span
                key={i}
                className="absolute bottom-1 top-1 w-px bg-accent opacity-40"
                style={{ left: `calc(${t}% * 0.99 + 0.5%)` }}
              />
            ))}
          </div>
          <div className="flex justify-between pt-1 text-[12px] text-ink-3">
            <span>
              {isDollar ? "$" : ""}
              {page.strip.axis[0]}
            </span>
            <span>
              {isDollar ? "$" : ""}
              {page.strip.axis[1]}
            </span>
          </div>
        </div>

        <StatList
          rows={page.rows}
          isDollar={isDollar}
          ariaLabel={`Cities by ${page.title.toLowerCase()}`}
          defaultIsLowFirst={page.default_is_low_first}
          strings={DATA.strings}
        />
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
