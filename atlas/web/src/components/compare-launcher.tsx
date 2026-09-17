"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import index from "@/data/search-index.json";

interface Entry {
  s: string; // slug
  f: string; // display name full
  k: string[];
}

/** Pick a second city; the compare URL carries both slugs and the whole
 * preference query string. */
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
  const results = useMemo(() => {
    const query = q.trim().toLowerCase();
    if (query.length < 2) return [];
    return (index as Entry[])
      .filter((e) => e.s !== slug)
      .filter((e) => [e.f, ...e.k].some((t) => t.toLowerCase().includes(query)))
      .slice(0, 6);
  }, [q, slug]);

  const label = small ? "Compare cities" : "Compare with another city";
  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={
          primary
            ? "min-h-[46px] self-start rounded-lg bg-accent px-5 text-[14.5px] font-bold text-white hover:bg-accent-hover"
            : "min-h-[42px] self-start rounded-lg bg-accent px-4 text-[13.5px] font-bold text-white hover:bg-accent-hover"
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
        <ul className="absolute z-20 mt-1 w-full overflow-hidden rounded-lg border border-rule bg-surface text-sm">
          {results.map((r) => (
            <li key={r.s}>
              <button
                type="button"
                className="block w-full px-3.5 py-2.5 text-left text-ink-2 hover:bg-tint hover:text-ink"
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
