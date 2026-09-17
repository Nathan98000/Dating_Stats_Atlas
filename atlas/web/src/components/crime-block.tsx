import Link from "next/link";
import type { CrimeBlock as CrimeBlockData } from "@/lib/types";

/** Reported crime, city-page shape (item 5): the two rates with their
 * coverage figure and the FBI's caution — or the blank state when too few
 * of the metro's agencies reported a full year. Every sentence arrives
 * composed from the API; crime is never scored (D01) and never ranked,
 * which is why the only onward link is the explainer, not a stat page. */
export function CrimeSection({ crime, city }: { crime: CrimeBlockData; city: string }) {
  return (
    <section className="flex flex-col gap-4" data-testid="crime-section">
      <h2 className="font-display text-[26px] font-semibold">
        Reported crime in {city}
      </h2>
      <div className="flex flex-col gap-4 rounded-xl border border-rule bg-surface px-7 py-6">
        {crime.available ? (
          <>
            <div className="flex flex-wrap gap-x-14 gap-y-4">
              {crime.stats!.map((s) => (
                <div key={s.id} className="flex flex-col gap-1" data-crime={s.id}>
                  <span className="text-[13px] font-semibold text-ink-2">{s.label}</span>
                  <span className="font-display text-[30px] font-semibold leading-none">
                    {s.display}
                  </span>
                  <span className="max-w-[26ch] text-[12.5px] text-ink-3">{s.unit_line}</span>
                </div>
              ))}
            </div>
            <p className="max-w-[72ch] text-[13.5px] leading-relaxed text-ink-2" data-testid="crime-coverage">
              {crime.coverage_line}
            </p>
          </>
        ) : (
          <p className="max-w-[72ch] text-[14.5px] leading-relaxed text-ink-2" data-testid="crime-blank">
            {crime.note}
          </p>
        )}
        <p className="max-w-[72ch] border-t border-rule pt-4 text-[13px] leading-relaxed text-ink-3" data-testid="crime-caution">
          {crime.caution}{" "}
          <Link
            href="/about-crime-data"
            className="font-semibold text-accent hover:text-accent-hover"
          >
            About these figures
          </Link>
        </p>
      </div>
    </section>
  );
}
