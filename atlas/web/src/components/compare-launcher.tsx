"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import index from "@/data/search-index.json";
import { searchCities, type CityEntry } from "@/lib/search";

/** Pick a second city; the compare URL carries both slugs and the whole
 * preference query string. Matching goes through lib/search — the one
 * matcher every city chooser shares (item 5). */
export function CompareLauncher({
  slug,
  primary = false,
  small = false,
}: {
  slug: string;
  primary?: boolean;
  small?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const router = useRouter();
  const sp = useSearchParams();
  const results = useMemo(
    () => searchCities(index as CityEntry[], q, { limit: 6, exclude: slug }),
    [q, slug],
  );

  const label = small ? "Compare cities" : "Compare with another city";
  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={
          primary
            ? "min-h-11 self-start rounded-md bg-accent px-5 text-body-sm font-bold text-white hover:bg-accent-hover"
            : "min-h-11 self-start rounded-md bg-accent px-4 text-caption font-bold text-white hover:bg-accent-hover"
        }
      >
        {label}
      </button>
    );
  }
  return (
    <div className="relative w-full max-w-[260px]">
      <label className="sr-only" htmlFor={`cmp-${slug}`}>City to compare with</label>
      <input
        id={`cmp-${slug}`}
        type="search"
        autoComplete="off"
        autoFocus
        placeholder="Type a city name"
        className="ctl"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
          if (e.key === "Enter" && results[0]) {
            const qs = sp.toString();
            router.push(`/compare/${slug}/${results[0].s}${qs ? `?${qs}` : ""}`);
          }
        }}
      />
      {results.length > 0 && (
        <ul className="absolute z-20 mt-1 w-full overflow-hidden rounded-lg border border-rule bg-surface text-body-sm shadow-overlay">
          {results.map((r) => (
            <li key={r.s}>
              <button
                type="button"
                className="block w-full px-3.5 py-2.5 text-left text-ink-2 hover:bg-hover hover:text-ink"
                onClick={() => {
                  const qs = sp.toString();
                  router.push(`/compare/${slug}/${r.s}${qs ? `?${qs}` : ""}`);
                }}
              >
                {r.f}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
