import Link from "next/link";
import { InfoTip } from "./info-tip";
import type { CrimeBlock, Meta } from "@/lib/types";

/** Crime as two ordinary-looking cards (Phase 2e item 2): rate,
 * five-band position (neutral tones — colouring would make the exact
 * comparison the caution disclaims), and an ⓘ. Since Phase 2f item 5.3
 * the popover carries ONLY the FBI's caution with its "See more
 * details" link — the per-city coverage sentence left this surface
 * (the explainer page covers coverage in prose); a blank card's popover
 * keeps its own why-blank sentence, which is about police reporting.
 * Cards share the city grid's six subgrid rows so their indicators
 * align with the other cards (item 5.2). */
export function CrimeCards({ crime, meta }: { crime: CrimeBlock; meta: Meta }) {
  const segments = meta.standing_bands.keys;
  if (!crime.available) {
    return (
      <>
        {["violent_crime_rate", "property_crime_rate"].map((fid) => {
          const le = meta.features[fid];
          return (
            <div key={fid} className="stat-card rounded-xl border border-rule bg-surface p-[18px]" data-card={fid}>
              <span className="flex items-center justify-between text-[13px] font-semibold text-ink-2">
                {le.display_name}
                <CrimeInfo fid={fid} crime={crime} seeMore={meta.policy_strings.crime_see_more} />
              </span>
              <span className="text-sm text-ink-3" data-testid="crime-card-blank">
                {crime.card_blank}
              </span>
              <span aria-hidden="true" />
              <span aria-hidden="true" />
              <span aria-hidden="true" />
              <span aria-hidden="true" />
            </div>
          );
        })}
      </>
    );
  }
  return (
    <>
      {crime.stats!.map((s) => (
        <div key={s.id} className="stat-card rounded-xl border border-rule bg-surface p-[18px]" data-card={s.id}>
          <span className="flex items-center justify-between text-[13px] font-semibold text-ink-2">
            {s.label}
            <CrimeInfo fid={s.id} crime={crime} seeMore={meta.policy_strings.crime_see_more} />
          </span>
          <span className="font-display text-[30px] font-semibold leading-none">
            {s.display}
          </span>
          <span className="unit-line text-[12.5px] text-ink-3">{s.unit_line}</span>
          {s.band ? (
            <div className="flex gap-1 pt-0.5" aria-hidden="true">
              {segments.map((seg) => (
                <span
                  key={seg}
                  className="h-1.5 flex-1 rounded-full"
                  style={{
                    background:
                      s.band!.key === seg ? "var(--ink-3)" : "var(--rule)",
                  }}
                />
              ))}
            </div>
          ) : (
            <span aria-hidden="true" />
          )}
          {s.band ? (
            <span data-testid="band-label" className="text-[12.5px] font-semibold text-ink-2">
              {s.band.label}
            </span>
          ) : (
            <span aria-hidden="true" />
          )}
          <span aria-hidden="true" />
        </div>
      ))}
    </>
  );
}

function CrimeInfo({ fid, crime, seeMore }: {
  fid: string; crime: CrimeBlock; seeMore: string;
}) {
  return (
    <InfoTip
      id={`crime-info-${fid}`}
      label={crime.card_info_label}
      testid={`crime-info-${fid}`}
    >
      {/* item 5.3: the caution replaces the box; the blank state keeps
          its own why-blank sentence first. "See more details" is the
          link, and the closing full stop completes Nathan's sentence. */}
      {!crime.available && crime.note ? <>{crime.note} </> : null}
      {crime.caution}{" "}
      <Link
        href="/about-crime-data"
        className="font-semibold text-accent underline underline-offset-2 hover:text-accent-hover"
      >
        {seeMore}
      </Link>
      .
    </InfoTip>
  );
}
