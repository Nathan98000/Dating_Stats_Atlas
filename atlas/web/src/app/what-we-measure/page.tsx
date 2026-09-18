import Link from "next/link";
import { apiMeta } from "@/lib/api";
import { SiteHeader } from "@/components/chrome";
import type { Meta } from "@/lib/types";

export const dynamic = "force-dynamic";

/** What we measure (Phase 2e item 12, recomposed in Phase 2f item 8):
 * heading straight into the groups — no intro — with the composition
 * driven by the registry's measure_page block, so this page arranges
 * nothing itself. Each card is a name, one sentence (the registry
 * definition, which is also that statistic's own page subheading), and
 * the stat-page link; the unit no longer appears beside the name.
 * Cost of living shows Rent and Everyday prices — the two RPP
 * components stay the scored features, and only this page's
 * presentation changed (the methodology page still documents that
 * everyday prices is their average). */
export default async function WhatWeMeasurePage() {
  const meta = await apiMeta();
  const policy = meta.policy_strings;

  const heading = (h: string) =>
    h === "people" ? policy.measure_people_heading
    : h === "context" ? policy.measure_context_heading
    : meta.pillars[h]?.display_name ?? h;

  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto flex max-w-3xl flex-col gap-8 px-6 pb-16 pt-10 sm:px-12">
        <h1 className="font-display text-[38px] font-semibold leading-tight tracking-tight">
          What we measure
        </h1>

        {meta.measure_page.map((group) => (
          <section key={group.heading} className="flex flex-col gap-3" data-group={group.heading}>
            <h2 className="font-display text-[24px] font-semibold">
              {heading(group.heading)}
            </h2>
            {(group.pillars ?? []).map((p) => (
              <MeasureRow
                key={p}
                name={meta.pillars[p].display_name}
                sentence={meta.pillars[p].definition}
              />
            ))}
            {(group.features ?? []).map((fid) => {
              const le = meta.features[fid];
              return (
                <MeasureRow
                  key={fid}
                  name={le.display_name}
                  sentence={le.definition}
                  statHref={meta.stat_pages.includes(fid) ? `/stats/${fid}` : undefined}
                  statLabel={policy.stat_page_link.replace(
                    "{name}",
                    (le.stat_page_name ?? le.display_name).toLowerCase(),
                  )}
                />
              );
            })}
            {group.crime && <CrimeMeasureRow meta={meta} />}
          </section>
        ))}
      </main>
    </>
  );
}

function CrimeMeasureRow({ meta }: { meta: Meta }) {
  const policy = meta.policy_strings;
  return (
    <MeasureRow
      name={`${meta.features.violent_crime_rate.display_name} & ${meta.features.property_crime_rate.display_name.toLowerCase()}`}
      sentence={policy.measure_crime_note}
      statHref="/about-crime-data"
      statLabel={policy.measure_crime_link}
      testid="measure-crime"
    />
  );
}

function MeasureRow({
  name,
  sentence,
  statHref,
  statLabel,
  testid,
}: {
  name: string;
  sentence: string;
  statHref?: string;
  statLabel?: string;
  testid?: string;
}) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-rule bg-surface px-5 py-4" data-testid={testid}>
      <span className="text-[15.5px] font-semibold">{name}</span>
      <p className="max-w-[64ch] text-[13.5px] leading-relaxed text-ink-2">{sentence}</p>
      {statHref && statLabel ? (
        <Link
          href={statHref}
          className="self-start pt-0.5 text-[12.5px] font-semibold text-accent hover:text-accent-hover"
        >
          {statLabel}
        </Link>
      ) : null}
    </div>
  );
}
