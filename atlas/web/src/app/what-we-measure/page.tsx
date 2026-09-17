import Link from "next/link";
import { apiMeta } from "@/lib/api";
import { SiteHeader } from "@/components/chrome";

export const dynamic = "force-dynamic";

/** What we measure (Phase 2e item 12): every statistic, grouped by the
 * four importance controls plus the two people-based measures — plain
 * name, unit, one sentence, and a link to its stat page. Crime gets its
 * own line with the non-comparability note, linking to the explainer
 * rather than to a ranking that deliberately does not exist. Every word
 * arrives from the registry through /v1/meta; this page composes
 * nothing. */
export default async function WhatWeMeasurePage() {
  const meta = await apiMeta();
  const policy = meta.policy_strings;
  const features = Object.entries(meta.features).filter(
    ([, le]) => le.status === "active" || le.status === "context_only",
  );
  const byPillar = (p: string) =>
    features.filter(([, le]) => le.pillar === p && le.weight_in_pillar > 0);
  const contextIds = ["everyday_prices", "who_lives_here"];
  const peoplePillars = ["pool", "balance"];
  const controlPillars = meta.controls.importance_pillars;

  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto flex max-w-3xl flex-col gap-8 px-6 pb-16 pt-10 sm:px-12">
        <div className="flex flex-col gap-2.5">
          <h1 className="font-display text-[38px] font-semibold leading-tight tracking-tight">
            What we measure
          </h1>
          <p className="max-w-[62ch] text-[15.5px] leading-relaxed text-ink-2">
            {policy.measure_page_intro}
          </p>
        </div>

        <section className="flex flex-col gap-3" data-group="people">
          <h2 className="font-display text-[24px] font-semibold">
            {policy.measure_people_heading}
          </h2>
          {peoplePillars.map((p) => (
            <MeasureRow
              key={p}
              name={meta.pillars[p].display_name}
              unit=""
              sentence={meta.pillars[p].definition}
            />
          ))}
        </section>

        {controlPillars.map((p) => (
          <section key={p} className="flex flex-col gap-3" data-group={p}>
            <h2 className="font-display text-[24px] font-semibold">
              {meta.pillars[p].display_name}
            </h2>
            {byPillar(p).map(([fid, le]) => (
              <MeasureRow
                key={fid}
                name={le.display_name}
                unit={le.unit}
                sentence={le.definition}
                statHref={meta.stat_pages.includes(fid) ? `/stats/${fid}` : undefined}
                statLabel={policy.stat_page_link.replace(
                  "{name}",
                  (le.stat_page_name ?? le.display_name).toLowerCase(),
                )}
              />
            ))}
          </section>
        ))}

        <section className="flex flex-col gap-3" data-group="context">
          <h2 className="font-display text-[24px] font-semibold">
            Also on every city page
          </h2>
          {contextIds.map((fid) => {
            const le = meta.features[fid];
            return (
              <MeasureRow
                key={fid}
                name={le.display_name}
                unit={le.unit}
                sentence={le.definition}
                statHref={meta.stat_pages.includes(fid) ? `/stats/${fid}` : undefined}
                statLabel={policy.stat_page_link.replace(
                  "{name}",
                  (le.stat_page_name ?? le.display_name).toLowerCase(),
                )}
              />
            );
          })}
          <MeasureRow
            name={`${meta.features.violent_crime_rate.display_name} & ${meta.features.property_crime_rate.display_name.toLowerCase()}`}
            unit={meta.features.violent_crime_rate.unit}
            sentence={policy.measure_crime_note}
            statHref="/about-crime-data"
            statLabel="About the crime figures"
            testid="measure-crime"
          />
        </section>
      </main>
    </>
  );
}

function MeasureRow({
  name,
  unit,
  sentence,
  statHref,
  statLabel,
  testid,
}: {
  name: string;
  unit: string;
  sentence: string;
  statHref?: string;
  statLabel?: string;
  testid?: string;
}) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-rule bg-surface px-5 py-4" data-testid={testid}>
      <span className="flex flex-wrap items-baseline gap-x-2.5">
        <span className="text-[15.5px] font-semibold">{name}</span>
        {unit ? <span className="text-[12.5px] text-ink-3">{unit}</span> : null}
      </span>
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
