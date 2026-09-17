"use client";

import { useRouter } from "next/navigation";
import { toSearchParams, wideners, type Prefs } from "@/lib/prefs";

/** MetroV3's approved hard-to-answer card. The wording arrives from the
 * policy strings with {search} and {city} filled — no count of anything,
 * never a zero (item 8). */
export function CityNarrowCard({
  city,
  search,
  policy,
  children,
}: {
  city: string;
  search: string;
  policy: Record<string, string>;
  children: React.ReactNode;
}) {
  const body = policy.city_narrow_body
    .replace("{search}", search.toLowerCase())
    .replaceAll("{city}", city);
  return (
    <section
      className="flex flex-col gap-4 rounded-xl border border-rule bg-surface px-7 py-6"
      data-testid="city-narrow-card"
    >
      <div className="flex items-start gap-4">
        <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-tint">
          <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
            <circle cx="8.5" cy="8.5" r="6" fill="none" stroke="var(--accent)" strokeWidth="1.8" />
            <path d="M13 13L18 18" fill="none" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </span>
        <div className="flex flex-col gap-[7px]">
          <span className="font-display text-[21px] font-semibold">
            {policy.city_narrow_title}
          </span>
          <p className="max-w-[78ch] text-[15px] leading-relaxed text-ink-2">
            {body}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-3 pl-14 max-sm:pl-0">{children}</div>
    </section>
  );
}

/** One-click loosenings that navigate back to results with exactly one
 * thing changed. */
export function CityWideners({ prefs }: { prefs: Prefs }) {
  const router = useRouter();
  const opts = wideners(prefs);
  return (
    <>
      {opts.map((w, i) => (
        <button
          key={w.label}
          type="button"
          onClick={() => router.push(`/?${toSearchParams(w.next).toString()}`)}
          className={
            i === 0
              ? "min-h-[42px] rounded-lg bg-accent px-[18px] text-[13.5px] font-bold text-white hover:bg-accent-hover"
              : "min-h-[42px] rounded-lg border-[1.5px] border-ink bg-paper px-[18px] text-[13.5px] font-bold text-ink hover:bg-tint"
          }
        >
          {w.label}
        </button>
      ))}
    </>
  );
}
