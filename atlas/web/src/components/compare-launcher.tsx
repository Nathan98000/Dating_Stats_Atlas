"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import index from "@/data/search-index.json";

interface Entry {
  c: string;
  t: string;
  r: boolean;
  k: string[];
}

/** Pick a second metro; the compare URL carries both metros and the whole
 * preference query string, so the comparison is shareable like every other
 * view (ADR 0003). */
export function CompareLauncher({ cbsa }: { cbsa: string }) {
  const [q, setQ] = useState("");
  const router = useRouter();
  const sp = useSearchParams();
  const results = useMemo(() => {
    const query = q.trim().toLowerCase();
    if (query.length < 2) return [];
    return (index as Entry[])
      .filter((e) => e.c !== cbsa)
      .filter((e) =>
        [e.t, ...e.k].some((t) => t.toLowerCase().includes(query)),
      )
      .slice(0, 6);
  }, [q, cbsa]);

  return (
    <div className="mt-2 max-w-xs">
      <label className="sr-only" htmlFor="compare-search">
        Metro to compare with
      </label>
      <input
        id="compare-search"
        type="search"
        autoComplete="off"
        placeholder="Type a metro name"
        className="w-full border border-rule bg-raised px-3 py-1.5 text-sm text-ink placeholder:text-ink-3"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      {results.length > 0 && (
        <ul className="mt-1 border border-rule bg-raised text-sm">
          {results.map((r) => (
            <li key={r.c}>
              <button
                type="button"
                className="block w-full px-3 py-1.5 text-left text-ink-2 hover:bg-chip hover:text-ink"
                onClick={() => {
                  const qs = sp.toString();
                  router.push(`/compare/${cbsa}/${r.c}${qs ? `?${qs}` : ""}`);
                }}
              >
                {r.t}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
