"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import index from "@/data/search-index.json";

interface Entry {
  s: string; // slug
  f: string; // "Provo, Utah"
  r: boolean;
  k: string[];
}

function score(entry: Entry, q: string): number {
  let best = 0;
  for (const tok of [entry.f, ...entry.k]) {
    const t = tok.toLowerCase();
    if (t === q) best = Math.max(best, 100);
    else if (t.startsWith(q)) best = Math.max(best, 80 - (t.length - q.length) * 0.5);
    else if (t.includes(q)) best = Math.max(best, 50 - t.indexOf(q));
    else {
      let i = 0;
      let gaps = 0;
      for (const ch of t) {
        if (ch === q[i]) i++;
        else if (i > 0) gaps++;
        if (i === q.length) break;
      }
      if (i === q.length && gaps <= q.length * 2) best = Math.max(best, 25 - gaps);
    }
  }
  return best;
}

/** Find-a-city (§8.3): the committed index, fuzzy-matched in the browser,
 * routed by slug. */
export function SearchBox() {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const router = useRouter();
  const sp = useSearchParams();

  const results = useMemo(() => {
    const query = q.trim().toLowerCase();
    if (query.length < 2) return [];
    return (index as Entry[])
      .map((e) => ({ e, s: score(e, query) }))
      .filter((r) => r.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, 8);
  }, [q]);

  const go = (slug: string) => {
    const qs = sp.toString();
    router.push(`/city/${slug}${qs ? `?${qs}` : ""}`);
    setOpen(false);
    setQ("");
  };

  const listOpen = open && results.length > 0;
  return (
    <div className="relative w-[190px]">
      <label className="sr-only" htmlFor="city-search">Find a city</label>
      <input
        id="city-search"
        type="search"
        role="combobox"
        aria-expanded={listOpen}
        aria-controls={listOpen ? "city-search-results" : undefined}
        aria-activedescendant={listOpen && results[active] ? `cs-${results[active].e.s}` : undefined}
        autoComplete="off"
        placeholder="Find a city"
        className="ctl !min-h-[42px]"
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
            go(results[active].e.s);
          } else if (e.key === "Escape") {
            setOpen(false);
          }
        }}
      />
      {listOpen && (
        <ul
          id="city-search-results"
          role="listbox"
          className="absolute right-0 z-30 mt-1 w-[260px] overflow-hidden rounded-lg border border-rule bg-surface text-sm"
        >
          {results.map((r, i) => (
            <li
              key={r.e.s}
              id={`cs-${r.e.s}`}
              role="option"
              aria-selected={i === active}
              className={`cursor-pointer px-3.5 py-2 ${i === active ? "bg-tint text-ink" : "text-ink-2"}`}
              onMouseDown={(e) => {
                e.preventDefault();
                go(r.e.s);
              }}
              onMouseEnter={() => setActive(i)}
            >
              {r.e.f}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
