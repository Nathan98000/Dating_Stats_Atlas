import Link from "next/link";
import { InfoTip } from "./info-tip";
import type { CrimeBlock, Meta } from "@/lib/types";

/** Crime as two ordinary-looking cards (Phase 2e item 2): rate,
 * five-band position (neutral tones — colouring would make the exact
 * comparison the caution disclaims), and an ⓘ whose popover carries the
 * coverage figure, the FBI's caution and the explainer link. Nothing
 * about reporting appears on the card face; crime is scored nowhere. */
export function CrimeCards({ crime, meta }: { crime: CrimeBlock; meta: Meta }) {
  const segments = meta.standing_bands.keys;
  if (!crime.available) {
    return (
      <>
        {["violent_crime_rate", "property_crime_rate"].map((fid) => {
          const le = meta.features[fid];
          return (
            <div key={fid} className="flex flex-col gap-2.5 rounded-xl border border-rule bg-surface p-[18px]" data-card={fid}>
              <span className="flex items-center justify-between text-[13px] font-semibold text-ink-2">
                {le.display_name}
                <CrimeInfo fid={fid} crime={crime} />
              </span>
              <span className="text-sm text-ink-3" data-testid="crime-card-blank">
                {crime.card_blank}
              </span>
            </div>
          );
        })}
      </>
    );
  }
  return (
    <>
      {crime.stats!.map((s) => (
        <div key={s.id} className="flex flex-col gap-2.5 rounded-xl border border-rule bg-surface p-[18px]" data-card={s.id}>
          <span className="flex items-center justify-between text-[13px] font-semibold text-ink-2">
            {s.label}
            <CrimeInfo fid={s.id} crime={crime} />
          </span>
          <span className="font-display text-[30px] font-semibold leading-none">
            {s.display}
          </span>
          <span className="text-[12.5px] text-ink-3">{s.unit_line}</span>
          {s.band && (
            <>
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
              <span className="text-[12.5px] font-semibold text-ink-2">
                {s.band.label}
              </span>
            </>
          )}
        </div>
      ))}
    </>
  );
}

function CrimeInfo({ fid, crime }: { fid: string; crime: CrimeBlock }) {
  return (
    <InfoTip
      id={`crime-info-${fid}`}
      label={crime.card_info_label}
      testid={`crime-info-${fid}`}
    >
      {crime.available ? crime.coverage_line : crime.note}{" "}
      {crime.caution}{" "}
      <Link
        href="/about-crime-data"
        className="font-semibold text-accent underline underline-offset-2 hover:text-accent-hover"
      >
        About these figures
      </Link>
    </InfoTip>
  );
}
