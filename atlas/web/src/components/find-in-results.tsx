"use client";

import { useId, useMemo, useState } from "react";
import index from "@/data/search-index.json";
import { searchCities, type CityEntry } from "@/lib/search";
import { ClearButton } from "./clear-button";

/** Phase 5: "Find a city in your results" — the one city matcher
 * (lib/search) over the cities ranked for this search only. Picking one
 * hands its slug to the list, which widens to include it, scrolls to it,
 * focuses its link and tints its row for two seconds. */
export function FindInResults({
  label,
  clearLabel,
  ranked,
  onPick,
}: {
  label: string;
  /** Phase 6 (F35): the registry's "Clear" */
  clearLabel: string;
  /** the slugs ranked for this search */
  ranked: string[];
  onPick: (slug: string) => void;
}) {
  const uid = useId();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const pool = useMemo(() => {
    const set = new Set(ranked);
    return (index as CityEntry[]).filter((e) => set.has(e.s));
  }, [ranked]);
  const results = useMemo(() => searchCities(pool, q, { limit: 8 }), [pool, q]);
  const listOpen = open && results.length > 0;
  const pick = (slug: string) => {
    setOpen(false);
    setQ("");
    onPick(slug);
  };
  return (
    <div className="relative w-full sm:w-[280px]">
      <label className="sr-only" htmlFor={`${uid}-q`}>{label}</label>
      <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true"
        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-3"
        fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="8.5" cy="8.5" r="5.5" /><path d="M13 13l4 4" strokeLinecap="round" />
      </svg>
      <input
        id={`${uid}-q`}
        type="search"
        role="combobox"
        aria-expanded={listOpen}
        aria-controls={listOpen ? `${uid}-list` : undefined}
        aria-autocomplete="list"
        aria-activedescendant={listOpen && results[active] ? `${uid}-${results[active].s}` : undefined}
        autoComplete="off"
        placeholder={label}
        data-testid="find-in-results"
        className={`ctl !pl-9 ${q ? "pr-11" : ""}`}
        value={q}
        onChange={(e) => { setQ(e.target.value); setOpen(true); setActive(0); }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, results.length - 1)); }
          else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
          else if (e.key === "Enter" && results[active]) { e.preventDefault(); pick(results[active].s); }
          else if (e.key === "Escape") setOpen(false);
        }}
      />
      {q && <ClearButton label={clearLabel} onClear={() => { setQ(""); setOpen(false); }} />}
      {listOpen && (
        <ul id={`${uid}-list`} role="listbox" aria-label={label}
          className="absolute left-0 right-0 z-30 mt-1 overflow-hidden rounded-lg border border-rule bg-surface text-body-sm shadow-overlay">
          {results.map((r, i) => (
            <li
              key={r.s}
              id={`${uid}-${r.s}`}
              role="option"
              aria-selected={i === active}
              className={`flex min-h-11 cursor-pointer items-center px-3.5 ${i === active ? "bg-tint text-ink" : "text-ink-2"}`}
              onMouseDown={(e) => { e.preventDefault(); pick(r.s); }}
              onMouseEnter={() => setActive(i)}
            >
              {r.f}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
