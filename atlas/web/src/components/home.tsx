"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Meta, RankResponse } from "@/lib/types";
import {
  searchChips,
  toRankBody,
  toSearchParams,
  type Prefs,
} from "@/lib/prefs";
import { SearchPanel } from "./panel";
import { ResultRow } from "./row";
import { NarrowState } from "./narrow";

/** The home page's client shell (HomeV3): hero, the full panel, results.
 * The first response arrives server-rendered; every change re-asks the API
 * through the same-origin proxy and rewrites the query string. Nothing is
 * recomputed here. A sticky search-summary bar with Change search appears
 * once the panel scrolls out of view (StatesV3/NarrowV3's chips row). */
export function Home({
  meta,
  initialPrefs,
  initialResponse,
}: {
  meta: Meta;
  initialPrefs: Prefs;
  initialResponse: RankResponse;
}) {
  const [prefs, setPrefs] = useState<Prefs>(initialPrefs);
  const [response, setResponse] = useState<RankResponse>(initialResponse);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chipsVisible, setChipsVisible] = useState(false);
  const seq = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const refetch = useCallback((next: Prefs) => {
    const mine = ++seq.current;
    setPending(true);
    fetch("/api/rank", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(toRankBody(next)),
    })
      .then(async (r) => {
        if (mine !== seq.current) return;
        if (!r.ok) {
          const j = await r.json().catch(() => ({}));
          setError(typeof j.detail === "string" ? j.detail : "that search couldn't run");
          return;
        }
        setError(null);
        setResponse(await r.json());
      })
      .catch(() => {
        if (mine === seq.current) setError("the ranking service is unreachable");
      })
      .finally(() => {
        if (mine === seq.current) setPending(false);
      });
  }, []);

  const onChange = useCallback(
    (next: Prefs) => {
      setPrefs(next);
      const qs = toSearchParams(next).toString();
      window.history.replaceState(null, "", `${window.location.pathname}?${qs}`);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => refetch(next), 180);
    },
    [refetch],
  );

  useEffect(() => {
    const el = panelRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(
      ([entry]) => setChipsVisible(!entry.isIntersecting),
      { rootMargin: "-80px 0px 0px 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  const policy = meta.policy_strings;
  const qs = toSearchParams(prefs).toString();
  const excluded = response.counts.suppressed;
  const allOut = response.counts.ranked === 0;
  const sameSex = (prefs.seekSex ?? (prefs.selfSex === "female" ? "male" : "female")) === prefs.selfSex;

  return (
    <>
      {/* sticky search summary (visible once the panel scrolls away) */}
      <div
        className={`sticky top-0 z-30 border-b border-t border-rule bg-surface px-6 py-3 sm:px-12 ${chipsVisible ? "" : "hidden"}`}
        data-testid="chips-bar"
      >
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3">
          <span className="text-[13px] font-bold text-ink-2">Your search</span>
          {searchChips(prefs).map((c) => (
            <span
              key={c.label}
              className={`flex min-h-[36px] items-center rounded-full border px-3.5 py-2 text-[13px] ${c.active ? "border-tint-border bg-tint font-semibold text-accent-hover" : "border-rule bg-paper"}`}
            >
              {c.label}
            </span>
          ))}
          <button
            type="button"
            className="ml-auto min-h-[40px] rounded-lg bg-accent px-[18px] text-[13.5px] font-bold text-white hover:bg-accent-hover"
            onClick={() => {
              panelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
              const first = panelRef.current?.querySelector<HTMLElement>("input, select, button");
              first?.focus({ preventScroll: true });
            }}
          >
            Change search
          </button>
        </div>
      </div>

      <div className="mx-auto grid max-w-6xl grid-cols-[360px_1fr] gap-10 px-6 pb-16 pt-8 sm:px-12 max-lg:grid-cols-1">
        <div ref={panelRef} id="search-panel" className="lg:sticky lg:top-16 lg:self-start">
          <SearchPanel prefs={prefs} meta={meta} onChange={onChange} sameSexNote={sameSex} />
        </div>

        <main id="main" className="min-w-0" aria-busy={pending}>
          {error && (
            <p role="alert" className="mb-4 rounded-lg border border-tint-border bg-tint px-4 py-3 text-sm text-accent-hover">
              {error}
            </p>
          )}

          {allOut ? (
            <NarrowState prefs={prefs} meta={meta} onWiden={onChange} />
          ) : (
            <>
              <div className="flex flex-wrap items-end justify-between gap-4 pb-2">
                <div className="flex max-w-[58ch] flex-col gap-1.5">
                  <h2 className="font-display text-2xl font-semibold" data-testid="list-heading">
                    {excluded > 0
                      ? policy.list_heading_count.replace(
                          "{n}", response.counts.ranked.toLocaleString("en-US"))
                      : policy.list_heading}
                  </h2>
                  {excluded > 0 && (
                    <p className="text-[13.5px] leading-relaxed text-ink-2" data-testid="excluded-note">
                      {policy.excluded_count.replace(
                        "{n}", excluded.toLocaleString("en-US"))}
                    </p>
                  )}
                </div>
                <label className="flex items-center gap-2.5 text-[13px] font-semibold text-ink-2">
                  Show
                  <select
                    className="ctl !w-auto !min-h-[40px] pr-9 text-[13.5px] font-semibold text-ink"
                    value={prefs.sort}
                    data-testid="sort"
                    onChange={(e) =>
                      onChange({ ...prefs, sort: e.target.value as Prefs["sort"] })
                    }
                  >
                    <option value="best_first">Best first</option>
                    <option value="worst_first">Worst first</option>
                  </select>
                </label>
              </div>

              <ol
                aria-label="Cities"
                data-testid="ranked-list"
                className={pending ? "opacity-60 transition-opacity" : "transition-opacity"}
              >
                {response.ranked.map((row) => (
                  <ResultRow key={row.cbsa} row={row} meta={meta} queryString={qs} />
                ))}
              </ol>

              <p className="mx-auto max-w-[70ch] pt-8 text-center text-[13px] leading-relaxed text-ink-3">
                {response.balance_applies
                  ? policy.balance_caption
                  : policy.balance_same_sex}{" "}
                <a href="/how-it-works" className="font-semibold text-accent hover:text-accent-hover">
                  How it works
                </a>
              </p>
            </>
          )}
        </main>
      </div>
    </>
  );
}
