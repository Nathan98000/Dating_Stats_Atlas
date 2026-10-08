"use client";

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState,
  useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import type { Meta, VariantResponse } from "@/lib/types";
import {
  PREFS_COOKIE,
  PREFS_COOKIE_MAX_AGE,
  describeChange,
  describeSearchShort,
  toRankBody,
  toSearchParams,
  type Prefs,
} from "@/lib/prefs";
import {
  effectiveSex,
  migrateLegacy,
  opposite,
  releasePending,
  writeAboutYou,
  type AboutYou,
} from "@/lib/about-you";
import { selectVariant } from "@/lib/variants";
import { fill, INITIAL_VISIBLE, showMore, visibleSlice, visibleToInclude } from "@/lib/results";
import { RailGroups } from "./panel";
import { FeaturedCard, ResultRow } from "./row";
import { NarrowState } from "./narrow";
import { Hero } from "./hero";
import { QuickSearch } from "./quick-search";
import { Segmented } from "./segmented";
import { FindInResults } from "./find-in-results";
import { BottomSheet } from "./bottom-sheet";

const DESK = "(min-width: 70rem)";
const subscribeDesk = (cb: () => void) => {
  const mq = window.matchMedia(DESK);
  mq.addEventListener("change", cb);
  return () => mq.removeEventListener("change", cb);
};

/** Whether the page is at the desk breakpoint (1120px): the rail sits
 * beside the results there, and in the sheet or drawer below it. The
 * server renders the desk layout (the rail is hidden by CSS below 1120px
 * until the page hydrates), so the rail's controls exist once, never
 * twice. */
function useDesk(): boolean {
  return useSyncExternalStore(subscribeDesk, () => window.matchMedia(DESK).matches, () => true);
}

/** FLIP for the result list (Phase 5): before new rows render, each row's
 * position is recorded by cbsa; after, a moved row starts where it was
 * and slides to its new place, 200ms ease-out. Nothing moves under
 * prefers-reduced-motion. */
function useFlip(container: React.RefObject<HTMLElement | null>) {
  const before = useRef<Map<string, number> | null>(null);
  const snapshot = useCallback(() => {
    const el = container.current;
    if (!el || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const m = new Map<string, number>();
    el.querySelectorAll<HTMLElement>("[data-cbsa]").forEach((n) => {
      m.set(n.dataset.cbsa!, n.getBoundingClientRect().top);
    });
    before.current = m;
  }, [container]);
  const play = useCallback(() => {
    const m = before.current;
    before.current = null;
    const el = container.current;
    if (!m || !el) return;
    el.querySelectorAll<HTMLElement>("[data-cbsa]").forEach((n) => {
      const was = m.get(n.dataset.cbsa!);
      if (was === undefined) return;
      const dy = was - n.getBoundingClientRect().top;
      if (Math.abs(dy) < 1) return;
      n.style.transition = "none";
      n.style.transform = `translateY(${dy}px)`;
      requestAnimationFrame(() => {
        n.style.transition = "transform 200ms ease-out";
        n.style.transform = "";
        n.addEventListener("transitionend", () => { n.style.transition = ""; }, { once: true });
      });
    });
  }, [container]);
  return { snapshot, play };
}

/** The home page's client shell (Phase 5, the design audit of 8 October
 * 2026): the hero with its quick search, the rail beside the results
 * from 1120px (in a sheet or drawer below that), and the results — a
 * header, the top three as cards, the rows from the fourth, ten at a
 * time, and how the score works. The first response arrives server-
 * rendered; every change of the search re-asks the API through the same-
 * origin proxy and rewrites the query string. m4.0.0 (ADR 0018): the
 * visitor's own sex, education and race live in this browser (lib/about-
 * you) and are never sent — the response carries every variant, and
 * changing one of them only selects another (lib/variants), with no
 * request at all. Nothing is recomputed here. */
export function Home({
  meta,
  initialPrefs,
  initialResponse,
  photos,
}: {
  meta: Meta;
  initialPrefs: Prefs;
  initialResponse: VariantResponse;
  /** the croppable city photographs on disk, by slug (lib/city-photos) */
  photos: Record<string, { src: string; alt: string }>;
}) {
  const router = useRouter();
  const [prefs, setPrefs] = useState<Prefs>(initialPrefs);
  const [response, setResponse] = useState<VariantResponse>(initialResponse);
  // the server renders the default variant; the stored one is read after
  // hydration, before the pending veil lifts (the pre-paint script)
  const [about, setAbout] = useState<AboutYou>({});
  const [ready, setReady] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visible, setVisible] = useState(INITIAL_VISIBLE);
  const [openRows, setOpenRows] = useState<Set<string>>(() => new Set());
  const [highlight, setHighlight] = useState<string | null>(null);
  const [live, setLive] = useState("");
  const [sheetOpen, setSheetOpen] = useState(false);
  const [barVisible, setBarVisible] = useState(false);
  const desk = useDesk();
  const seq = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastPrefs = useRef<Prefs>(initialPrefs);
  const quickRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const adjustRef = useRef<HTMLButtonElement>(null);
  const { snapshot, play } = useFlip(listRef);
  const policy = meta.policy_strings;

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
        const body = await r.json();
        if (mine !== seq.current) return;
        snapshot();
        setResponse(body);
        setLive(fill(policy.results_updated, { change: describeChange(lastPrefs.current, next) }));
        lastPrefs.current = next;
      })
      .catch(() => {
        if (mine === seq.current) setError("the ranking service is unreachable");
      })
      .finally(() => {
        if (mine === seq.current) setPending(false);
      });
  }, [snapshot, policy.results_updated]);

  const onChange = useCallback(
    (next: Prefs, now = false) => {
      setPrefs(next);
      setVisible(INITIAL_VISIBLE);
      setOpenRows(new Set());
      const qs = toSearchParams(next).toString();
      window.history.replaceState(null, "", `${window.location.pathname}?${qs}`);
      // Phase 2f item 2 (ADR 0007): the search follows the visitor. The
      // query string stays the shareable form; the cookie is only the
      // fallback for a bare URL, and explicit parameters always win. It
      // holds no "about you" detail (m4.0.0).
      try {
        document.cookie = `${PREFS_COOKIE}=${encodeURIComponent(qs)}; ` +
          `path=/; max-age=${PREFS_COOKIE_MAX_AGE}; samesite=lax`;
      } catch {
        /* a blocked cookie jar never blocks the search itself */
      }
      if (timer.current) clearTimeout(timer.current);
      if (now) refetch(next);
      else timer.current = setTimeout(() => refetch(next), 180);
    },
    [refetch],
  );

  // m4.0.0: the details this browser holds (old links' and cookies' moved
  // in first); an old link that named no sought sex meant the opposite of
  // its self_sex, and the search follows it
  useLayoutEffect(() => {
    const { about: stored, soughtSex } = migrateLegacy(PREFS_COOKIE, PREFS_COOKIE_MAX_AGE);
    setAbout(stored);
    if (soughtSex && soughtSex !== initialPrefs.seekSex) {
      onChange({ ...initialPrefs, seekSex: soughtSex }, true);
    } else {
      setReady(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  // the veil lifts once the stored variant has rendered (and, for an old
  // link that changed the search, once its response has arrived)
  useLayoutEffect(() => {
    if (ready) releasePending();
  }, [ready]);
  useEffect(() => {
    if (!ready && !pending && response.variants.sought_sex === prefs.seekSex) setReady(true);
  }, [ready, pending, response, prefs.seekSex]);

  const saveAbout = useCallback((next: AboutYou) => {
    snapshot();
    writeAboutYou(next);
    setAbout(next);
  }, [snapshot]);
  /** Own sex: stored in this browser. A search that was opposite-sex stays
   * opposite-sex (the sought sex follows, as it did when it defaulted to
   * the opposite of the visitor's); a same-sex search keeps its sought
   * sex. */
  const onSelfSex = useCallback((sex: "male" | "female") => {
    const was = effectiveSex(about, prefs.seekSex);
    saveAbout({ ...about, sex });
    if (was !== prefs.seekSex && sex === prefs.seekSex) {
      onChange({ ...prefs, seekSex: opposite(sex) });
    }
  }, [about, prefs, onChange, saveAbout]);
  /** Sought sex: part of the search. The own sex the panel was showing is
   * kept (stored) so the visitor's "I'm a" never flips under them. */
  const onSeekSex = useCallback((seekSex: "male" | "female") => {
    if (!about.sex) saveAbout({ ...about, sex: effectiveSex(about, prefs.seekSex) });
    onChange({ ...prefs, seekSex });
  }, [about, prefs, onChange, saveAbout]);

  // the sticky bottom bar (below 1120px) appears once the quick search
  // has scrolled out of view
  useEffect(() => {
    const el = quickRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(([entry]) => setBarVisible(!entry.isIntersecting));
    io.observe(el);
    return () => io.disconnect();
  }, []);
  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  const qs = toSearchParams(prefs).toString();
  const selected = useMemo(() => selectVariant(response, about), [response, about]);
  // the rows have rendered in their new places: slide them there
  useLayoutEffect(() => { play(); }, [selected, play]);
  useEffect(() => {
    if (!highlight) return;
    const t = setTimeout(() => setHighlight(null), 2000);
    return () => clearTimeout(t);
  }, [highlight]);

  const excluded = selected.counts.suppressed;
  const allOut = selected.counts.ranked === 0;
  const selfSex = effectiveSex(about, prefs.seekSex);
  const sameSex = selfSex === prefs.seekSex;
  const short = describeSearchShort(prefs);
  const { featured, rest } = visibleSlice(selected.ranked, visible);
  const total = selected.ranked.length;
  const cityHref = (slug: string) => `/city/${slug}${qs ? `?${qs}` : ""}`;

  const findCity = (slug: string) => {
    const i = selected.ranked.findIndex((r) => r.slug === slug);
    if (i < 0) return;
    setVisible((v) => visibleToInclude(v, i));
    setHighlight(slug);
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const li = listRef.current?.querySelector<HTMLElement>(`[data-slug="${slug}"]`);
      li?.scrollIntoView({ block: "center" });
      li?.querySelector<HTMLAnchorElement>("a")?.focus({ preventScroll: true });
    }));
  };
  const toggleRow = (cbsa: string) =>
    setOpenRows((cur) => {
      const next = new Set(cur);
      if (next.has(cbsa)) next.delete(cbsa);
      else next.add(cbsa);
      return next;
    });

  const rail = (
    <RailGroups
      prefs={prefs}
      meta={meta}
      onChange={onChange}
      sameSex={sameSex}
      sameSexNote={response.variants.same_sex_note}
      about={about}
      onAbout={saveAbout}
    />
  );

  return (
    <>
      <main id="main" className="mx-auto max-w-[1200px] px-4 pb-16 sm:px-12">
        <Hero title={policy.home_title} subtitle={policy.home_subtitle}>
          <div ref={quickRef}>
            <QuickSearch
              prefs={prefs}
              meta={meta}
              selfSex={selfSex}
              onSelfSex={onSelfSex}
              onSeekSex={onSeekSex}
              onChange={onChange}
            />
          </div>
        </Hero>

        <div className="grid gap-8 pt-5 sm:pt-11 desk:grid-cols-[288px_1fr] desk:items-start">
          {desk && (
            <aside
              aria-label={policy.adjust_search}
              className="sticky top-4 rounded-lg border border-rule bg-surface p-5 max-desk:hidden"
              data-testid="rail"
            >
              {rail}
            </aside>
          )}

          <section aria-labelledby="results-heading" aria-busy={pending} className="min-w-0">
            {error && (
              <p role="alert" className="mb-4 rounded-md border border-error bg-error-soft px-4 py-3 text-body-sm text-error">
                {error}
              </p>
            )}

            {allOut ? (
              <NarrowState prefs={prefs} meta={meta} onWiden={onChange} />
            ) : (
              <>
                <div className="flex flex-wrap items-end justify-between gap-4 pb-3 max-sm:flex-col max-sm:items-start">
                  <div className="flex max-w-[60ch] flex-col">
                    <p className="text-overline uppercase text-ink-3">{policy.results_eyebrow}</p>
                    <h2 id="results-heading" className="mt-1 font-display text-h2" data-testid="list-heading">
                      {fill(prefs.sort === "worst_first" ? policy.results_heading_worst
                        : policy.results_heading_best, short)}
                    </h2>
                    <p className="text-body-sm text-ink-3" data-testid="results-count">
                      {fill(policy.results_count, { n: selected.counts.ranked.toLocaleString("en-US") })}
                    </p>
                    {excluded > 0 && (
                      <p className="mt-1 text-body-sm text-ink-2" data-testid="excluded-note">
                        {policy.excluded_count.replace("{n}", excluded.toLocaleString("en-US"))}
                      </p>
                    )}
                  </div>
                  <Segmented
                    inline
                    label="Show"
                    testid="sort"
                    options={[
                      { value: "best_first", label: "Best first" },
                      { value: "worst_first", label: "Worst first" },
                    ]}
                    value={prefs.sort}
                    onChange={(v) => onChange({ ...prefs, sort: v as Prefs["sort"] })}
                  />
                </div>
                <div aria-hidden="true" className={pending ? "progress-line mb-3" : "mb-3 h-0.5"} data-testid="pending-line" />
                <p className="sr-only" aria-live="polite" data-testid="results-live">{live}</p>

                <div ref={listRef} data-testid="ranked-list" data-variant="">
                  <ol aria-label="Cities" className="grid gap-4 md:grid-cols-3">
                    {featured.map((row) => (
                      <FeaturedCard
                        key={row.cbsa}
                        row={row}
                        meta={meta}
                        href={cityHref(row.slug)}
                        sought={short.sought}
                        photo={photos[row.slug]}
                        median={selected.score_median}
                      />
                    ))}
                  </ol>

                  {rest.length > 0 && (
                    <>
                      <div className="mt-7 flex flex-wrap items-center justify-between gap-3">
                        <FindInResults
                          label={policy.find_in_results}
                          ranked={selected.ranked.map((r) => r.slug)}
                          onPick={findCity}
                        />
                      </div>
                      <div className="mt-4 hidden grid-cols-[40px_1fr_112px_104px_18px] gap-x-3.5 border-b border-rule px-4 pb-2 text-overline uppercase text-ink-3 sm:grid">
                        <span>{policy.col_rank}</span>
                        <span>{policy.col_city}</span>
                        <span className="text-right">{policy.col_matches}</span>
                        <span className="text-right" data-testid="score-label">{policy.col_score}</span>
                        <span />
                      </div>
                      <ol start={featured.length + 1} aria-label="More cities" className="max-sm:mt-3 max-sm:border-t max-sm:border-rule">
                        {rest.map((row) => (
                          <ResultRow
                            key={row.cbsa}
                            row={row}
                            meta={meta}
                            href={cityHref(row.slug)}
                            sought={short.sought}
                            open={openRows.has(row.cbsa)}
                            onToggle={() => toggleRow(row.cbsa)}
                            onCompare={() => router.push(`/compare?a=${row.slug}${qs ? `&${qs}` : ""}`)}
                            highlighted={highlight === row.slug}
                          />
                        ))}
                      </ol>
                    </>
                  )}
                </div>

                {visible < total && (
                  <div className="flex items-center gap-4 pt-6 max-sm:flex-col max-sm:items-stretch">
                    <button
                      type="button"
                      data-testid="show-more"
                      onClick={() => setVisible((v) => showMore(v, total))}
                      className="flex h-11 items-center justify-center rounded-md border border-line-strong bg-surface px-5 text-body font-semibold text-ink hover:bg-hover"
                    >
                      {policy.show_more}
                    </button>
                    <button
                      type="button"
                      data-testid="show-all"
                      onClick={() => setVisible(total)}
                      className="flex min-h-11 items-center justify-center text-body font-semibold text-accent hover:text-accent-hover"
                    >
                      {fill(policy.show_all, { n: total.toLocaleString("en-US") })}
                    </button>
                  </div>
                )}

                <ScoreExplainer meta={meta} />
              </>
            )}
          </section>
        </div>
      </main>

      {!desk && (
        <>
          <div
            className={`fixed inset-x-0 bottom-0 z-30 bg-surface px-4 pb-[calc(14px+env(safe-area-inset-bottom))] pt-2.5 shadow-overlay ${barVisible ? "" : "hidden"}`}
            data-testid="bottom-bar"
          >
            <button
              ref={adjustRef}
              type="button"
              onClick={() => setSheetOpen(true)}
              className="flex h-[52px] w-full items-center justify-center gap-2.5 rounded-md bg-accent text-body font-semibold text-white hover:bg-accent-hover"
            >
              <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true" fill="none"
                stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                <path d="M3 6h9M15 6h2M3 14h2M8 14h9" />
                <circle cx="13.5" cy="6" r="1.8" />
                <circle cx="6.5" cy="14" r="1.8" />
              </svg>
              {policy.adjust_search}
            </button>
          </div>
          <BottomSheet
            open={sheetOpen}
            onClose={() => setSheetOpen(false)}
            title={policy.adjust_search}
            footerLabel={policy.show_results}
            closeLabel={policy.close}
            returnFocus={adjustRef}
          >
            {rail}
          </BottomSheet>
        </>
      )}
    </>
  );
}

/** "How the score works", below the list: the two people pillars in their
 * served definitions, the lifestyle line, a link to How it works, and the
 * balance caption. */
function ScoreExplainer({ meta }: { meta: Meta }) {
  const s = meta.policy_strings;
  const [lifeHead, ...lifeRest] = s.explainer_lifestyle.split(":");
  const cols = [
    { head: meta.pillars.pool?.display_name, body: meta.pillars.pool?.definition },
    { head: meta.pillars.match?.display_name, body: meta.pillars.match?.definition },
    { head: lifeHead, body: lifeRest.join(":").trim() },
  ];
  return (
    <section className="mt-14 border-t border-rule pt-8" aria-labelledby="score-explainer" data-testid="score-explainer">
      <h2 id="score-explainer" className="font-display text-h3">{s.explainer_heading}</h2>
      <div className="mt-4 grid gap-6 sm:grid-cols-3">
        {cols.map((c) => (
          <div key={c.head}>
            <h3 className="text-body-sm font-semibold text-ink">{c.head}</h3>
            <p className="mt-1 text-body-sm text-ink-2">{c.body}</p>
          </div>
        ))}
      </div>
      <p className="mt-5 text-body-sm">
        <a href="/about" className="inline-flex min-h-11 items-center font-semibold text-accent hover:text-accent-hover">
          {s.nav_how} →
        </a>
      </p>
      <p className="mt-1 max-w-[70ch] text-caption text-ink-3" data-testid="balance-footnote">
        {s.balance_caption}
      </p>
    </section>
  );
}
