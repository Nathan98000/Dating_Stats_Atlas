"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import index from "@/data/search-index.json";
import { searchCities, type CityEntry } from "@/lib/search";
import { ClearButton } from "./clear-button";

/** Pick a second city; the compare URL carries both slugs and the whole
 * preference query string. Matching goes through lib/search — the one
 * matcher every city chooser shares (item 5). */
export function CompareLauncher({
  slug,
  outlined = false,
  clearLabel,
  label,
  fieldLabel,
  placeholder,
}: {
  slug: string;
  /** Phase 7 (Nathan, 13 October 2026): the city page's top button takes
   * the outlined style of "Change your search" beside it (same size,
   * --line-strong border, --ink text), so the page's one filled button is
   * "Compare cities" at its foot */
  outlined?: boolean;
  /** Phase 6 (F35): the registry's "Clear", from the server page */
  clearLabel: string;
  /** Phase 8 (R15): the registry's words, from the server page: the
   * button's (compare_with_another or compare_cities), the field's
   * (compare_with_label) and its placeholder (city_input_placeholder) */
  label: string;
  fieldLabel: string;
  placeholder: string;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const router = useRouter();
  const sp = useSearchParams();
  const results = useMemo(
    () => searchCities(index as CityEntry[], q, { limit: 6, exclude: slug }),
    [q, slug],
  );

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={
          outlined
            ? "flex min-h-11 items-center self-start rounded-md border border-line-strong bg-surface px-5 text-body font-semibold text-ink hover:bg-hover"
            : "min-h-11 self-start rounded-md bg-accent px-4 text-caption font-bold text-white hover:bg-accent-hover"
        }
      >
        {label}
      </button>
    );
  }
  return (
    <div className="relative w-full max-w-[260px]">
      <label className="sr-only" htmlFor={`cmp-${slug}`}>{fieldLabel}</label>
      <input
        id={`cmp-${slug}`}
        type="search"
        autoComplete="off"
        autoFocus
        placeholder={placeholder}
        className={`ctl ${q ? "pr-11" : ""}`}
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
      {q && <ClearButton label={clearLabel} onClear={() => setQ("")} />}
      {results.length > 0 && (
        <ul className="absolute z-20 mt-1 w-full overflow-hidden rounded-lg border border-rule bg-surface text-body-sm shadow-overlay">
          {results.map((r) => (
            <li key={r.s}>
              <button
                type="button"
                className="flex min-h-11 w-full items-center px-3.5 text-left text-ink-2 hover:bg-hover hover:text-ink"
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
