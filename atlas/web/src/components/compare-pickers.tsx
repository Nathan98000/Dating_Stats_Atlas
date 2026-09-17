"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import index from "@/data/search-index.json";
import { searchCities, type CityEntry } from "@/lib/search";

/** The compare landing page's two city pickers (item 8): the same
 * client-side search index as Find-a-city, pre-filled from the URL when
 * present. Both chosen, one button — and the compare view itself renders
 * both cities from ONE ranking response (ADR 0003). */
export function ComparePickers({
  initialA,
  initialB,
}: {
  initialA?: string;
  initialB?: string;
}) {
  const router = useRouter();
  const sp = useSearchParams();
  const bySlug = useMemo(() => {
    const m = new Map<string, CityEntry>();
    for (const e of index as CityEntry[]) m.set(e.s, e);
    return m;
  }, []);
  const [a, setA] = useState<string | undefined>(
    initialA && bySlug.has(initialA) ? initialA : undefined);
  const [b, setB] = useState<string | undefined>(
    initialB && bySlug.has(initialB) ? initialB : undefined);

  const go = () => {
    if (!a || !b || a === b) return;
    const qs = new URLSearchParams(sp.toString());
    qs.delete("a");
    qs.delete("b");
    const s = qs.toString();
    router.push(`/compare/${a}/${b}${s ? `?${s}` : ""}`);
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 gap-4 max-sm:grid-cols-1">
        <CityPicker
          id="compare-a"
          label="First city"
          exclude={b}
          value={a ? bySlug.get(a)?.f : undefined}
          onPick={setA}
        />
        <CityPicker
          id="compare-b"
          label="Second city"
          exclude={a}
          value={b ? bySlug.get(b)?.f : undefined}
          onPick={setB}
        />
      </div>
      <button
        type="button"
        data-testid="compare-go"
        disabled={!a || !b || a === b}
        onClick={go}
        className="min-h-[46px] self-start rounded-lg bg-accent px-6 text-[14.5px] font-bold text-white hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-40"
      >
        Compare these two
      </button>
    </div>
  );
}

function CityPicker({
  id,
  label,
  value,
  exclude,
  onPick,
}: {
  id: string;
  label: string;
  value?: string;
  exclude?: string;
  onPick: (slug: string) => void;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  // the SHARED matcher (lib/search): the unranked includes() this
  // replaced served seven upstate metros for "new york" and dropped the
  // city itself off the end (item 5)
  const results = useMemo(
    () => searchCities(index as CityEntry[], q, { limit: 7, exclude }),
    [q, exclude],
  );
  const listOpen = open && results.length > 0;

  const choose = (slug: string, name: string) => {
    onPick(slug);
    setQ(name);
    setOpen(false);
  };

  return (
    <div className="relative">
      <label htmlFor={id} className="mb-1.5 block text-[13px] font-semibold text-ink-2">
        {label}
      </label>
      <input
        id={id}
        type="search"
        role="combobox"
        aria-expanded={listOpen}
        aria-controls={listOpen ? `${id}-list` : undefined}
        aria-activedescendant={
          listOpen && results[active] ? `${id}-${results[active].s}` : undefined}
        autoComplete="off"
        placeholder="Type a city name"
        className="ctl"
        value={open ? q : (value ?? q)}
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
            setActive((x) => Math.min(x + 1, results.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive((x) => Math.max(x - 1, 0));
          } else if (e.key === "Enter" && results[active]) {
            e.preventDefault();
            choose(results[active].s, results[active].f);
          } else if (e.key === "Escape") {
            setOpen(false);
          }
        }}
      />
      {listOpen && (
        <ul
          id={`${id}-list`}
          role="listbox"
          className="absolute z-30 mt-1 w-full overflow-hidden rounded-lg border border-rule bg-surface text-sm"
        >
          {results.map((r, i) => (
            <li
              key={r.s}
              id={`${id}-${r.s}`}
              role="option"
              aria-selected={i === active}
              className={`cursor-pointer px-3.5 py-2.5 ${i === active ? "bg-tint text-ink" : "text-ink-2"}`}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(r.s, r.f);
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
