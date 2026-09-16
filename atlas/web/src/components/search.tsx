"use client";

import { useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import index from "@/data/search-index.json";

interface Entry {
  c: string;
  t: string;
  r: boolean;
  k: string[];
}

/** §8.3 search: the ~30 KB committed index (CBSA names, principal cities,
 * state abbreviations, hand-written colloquials), fuzzy-matched in the
 * browser. No server round-trip. */
function score(entry: Entry, q: string): number {
  let best = 0;
  for (const tok of [entry.t, ...entry.k]) {
    const t = tok.toLowerCase();
    if (t === q) best = Math.max(best, 100);
    else if (t.startsWith(q)) best = Math.max(best, 80 - (t.length - q.length) * 0.5);
    else if (t.includes(q)) best = Math.max(best, 50 - t.indexOf(q));
    else {
      // subsequence with small gaps, so "twn cities" still finds it
      let i = 0;
      let gaps = 0;
      for (const ch of t) {
        if (ch === q[i]) i++;
        else if (i > 0) gaps++;
        if (i === q.length) break;
      }
      if (i === q.length && gaps <= q.length * 2) {
        best = Math.max(best, 25 - gaps);
      }
    }
  }
  return best;
}

export function SearchBox() {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const router = useRouter();
  const sp = useSearchParams();
  const listRef = useRef<HTMLUListElement>(null);

  const results = useMemo(() => {
    const query = q.trim().toLowerCase();
    if (query.length < 2) return [];
    return (index as Entry[])
      .map((e) => ({ e, s: score(e, query) }))
      .filter((r) => r.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, 8);
  }, [q]);

  const go = (cbsa: string) => {
    const qs = sp.toString();
    router.push(`/metro/${cbsa}${qs ? `?${qs}` : ""}`);
    setOpen(false);
    setQ("");
  };

  return (
    <div className="relative w-full max-w-xs">
      <label className="sr-only" htmlFor="metro-search">
        Find a metro
      </label>
      <input
        id="metro-search"
        type="search"
        role="combobox"
        aria-expanded={open && results.length > 0}
        aria-controls={open && results.length > 0 ? "metro-search-results" : undefined}
        aria-activedescendant={
          open && results[active] ? `sr-${results[active].e.c}` : undefined
        }
        autoComplete="off"
        placeholder="Find a metro — try “the Triangle”"
        className="w-full border border-rule bg-raised px-3 py-1.5 text-sm text-ink placeholder:text-ink-3"
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
            go(results[active].e.c);
          } else if (e.key === "Escape") {
            setOpen(false);
          }
        }}
      />
      {open && results.length > 0 && (
        <ul
          id="metro-search-results"
          role="listbox"
          ref={listRef}
          className="absolute z-20 mt-1 w-full border border-rule bg-raised text-sm shadow-none"
        >
          {results.map((r, i) => (
            <li
              key={r.e.c}
              id={`sr-${r.e.c}`}
              role="option"
              aria-selected={i === active}
              className={`cursor-pointer px-3 py-1.5 ${i === active ? "bg-chip text-ink" : "text-ink-2"}`}
              onMouseDown={(e) => {
                e.preventDefault();
                go(r.e.c);
              }}
              onMouseEnter={() => setActive(i)}
            >
              {r.e.t}
              {!r.e.r && <span className="ml-2 text-xs text-ink-3">below population floor</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
