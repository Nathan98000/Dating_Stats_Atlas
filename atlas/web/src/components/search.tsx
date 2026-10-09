"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import index from "@/data/search-index.json";
import { searchCities, type CityEntry } from "@/lib/search";
import { ClearButton } from "./clear-button";

/** Find-a-city (§8.3): the committed index, matched in the browser
 * through lib/search — the ONE matcher every city chooser shares since
 * Phase 2e item 5 — routed by slug. Phase 5: 240px in the desk header
 * (its menu 260px); `wide` fills the phone header's overlay. */
export function SearchBox({ wide = false, autoFocus = false, clearLabel = "" }: {
  wide?: boolean; autoFocus?: boolean;
  /** Phase 6 (F35): the registry's "Clear", from the server-rendered header (lib/chrome is
   * server data: importing it here would ship stat-pages.json to every page) */
  clearLabel?: string;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const router = useRouter();
  const sp = useSearchParams();

  const results = useMemo(
    () => searchCities(index as CityEntry[], q, { limit: 8 }),
    [q],
  );

  const go = (slug: string) => {
    const qs = sp.toString();
    router.push(`/city/${slug}${qs ? `?${qs}` : ""}`);
    setOpen(false);
    setQ("");
  };

  const listOpen = open && results.length > 0;
  return (
    <div className={`relative ${wide ? "flex-1" : "w-[240px]"}`}>
      <label className="sr-only" htmlFor="city-search">Find a city</label>
      <input
        id="city-search"
        type="search"
        role="combobox"
        aria-expanded={listOpen}
        aria-controls={listOpen ? "city-search-results" : undefined}
        aria-activedescendant={listOpen && results[active] ? `cs-${results[active].s}` : undefined}
        autoComplete="off"
        placeholder="Find a city"
        autoFocus={autoFocus}
        className={`ctl ${wide ? "" : "!min-h-10"} ${q && !wide && clearLabel ? "pr-11" : ""}`}
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
          setActive(0);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setActive((a) => Math.min(a + 1, results.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive((a) => Math.max(a - 1, 0));
          } else if (e.key === "Enter" && results[active]) {
            e.preventDefault();
            go(results[active].s);
          } else if (e.key === "Escape") {
            setOpen(false);
          }
        }}
      />
      {q && !wide && clearLabel && (
        <ClearButton label={clearLabel} onClear={() => { setQ(""); setOpen(false); }} />
      )}
      {listOpen && (
        <ul
          id="city-search-results"
          role="listbox"
          className={`absolute right-0 z-30 mt-1 overflow-hidden rounded-lg border border-rule bg-surface text-body-sm shadow-overlay ${wide ? "left-0" : "w-[260px]"}`}
        >
          {results.map((r, i) => (
            <li
              key={r.s}
              id={`cs-${r.s}`}
              role="option"
              aria-selected={i === active}
              className={`flex min-h-11 cursor-pointer items-center px-3.5 desk:min-h-9 ${i === active ? "bg-tint text-ink" : "text-ink-2"}`}
              onMouseDown={(e) => {
                e.preventDefault();
                go(r.s);
              }}
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
