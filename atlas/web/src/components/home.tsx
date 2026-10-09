"use client";

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState,
  useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import type { Meta, VariantResponse } from "@/lib/types";
import type { CardPhoto } from "@/lib/city-photos";
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
import { readPlace, writePlace } from "@/lib/place";
import { fill, INITIAL_VISIBLE, showMore, visibleSlice, visibleToInclude } from "@/lib/results";
import { RailGroups } from "./panel";
import { FeaturedCard, ResultRow, RowDetail } from "./row";
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

/** Phase 6 (F06): whether the cards sit three to a row (from 768px), so a
 * card's detail opens in one panel under them rather than inside the card.
 * The server renders cards closed, so its answer (true) never shows. */
const WIDE = "(min-width: 48rem)";
const subscribeWide = (cb: () => void) => {
  const mq = window.matchMedia(WIDE);
  mq.addEventListener("change", cb);
  return () => mq.removeEventListener("change", cb);
};
function useWide(): boolean {
  return useSyncExternalStore(subscribeWide, () => window.matchMedia(WIDE).matches, () => true);
}

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
  /** the city photographs on disk, by slug, as a card shows them
   * (lib/city-photos) */
  photos: Record<string, CardPhoto>;
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
  // Phase 6 (F06): the one featured card whose detail is open
  const [openCard, setOpenCard] = useState<string | null>(null);
  const [highlight, setHighlight] = useState<string | null>(null);
  const [live, setLive] = useState("");
  // Phase 6 (F05, F13): when a change lands, the line under the count (6
  // s; its slot stays once used, so later lines don't shift the page) and
  // the tint on the rows and cards that moved (2 s)
  const [notice, setNotice] = useState<{ text: string; n: number } | null>(null);
  const [noticeSlot, setNoticeSlot] = useState(false);
  const [moved, setMoved] = useState<Set<string>>(() => new Set());
  const announce = useRef<string | null>(null);
  const prevOrder = useRef<string[] | null>(null);
  // Phase 6 (F20): "Looking for" touched this visit
  const seekTouched = useRef(false);
  // Phase 6 (F05, F19): where focus goes once the sheet has closed
  const afterSheet = useRef<"results" | "quick" | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [barVisible, setBarVisible] = useState(false);
  const desk = useDesk();
  const wide = useWide();
  const seq = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastPrefs = useRef<Prefs>(initialPrefs);
  const quickRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const adjustRef = useRef<HTMLButtonElement>(null);
  const railRef = useRef<HTMLElement>(null);
  const [railMore, setRailMore] = useState(false);
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
        // Phase 6 (F05): said, shown and tinted once the rows have landed
        announce.current = describeChange(lastPrefs.current, next);
        setResponse(body);
        lastPrefs.current = next;
      })
      .catch(() => {
        if (mine === seq.current) setError("the ranking service is unreachable");
      })
      .finally(() => {
        if (mine === seq.current) setPending(false);
      });
  }, [snapshot]);

  const onChange = useCallback(
    (next: Prefs, now = false) => {
      setPrefs(next);
      setVisible(INITIAL_VISIBLE);
      setOpenRows(new Set());
      setOpenCard(null);
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
    // Phase 6 (F20): the sought sex follows only while "Looking for" hasn't
    // been touched this visit, and the live region says so when it does
    if (was !== prefs.seekSex && sex === prefs.seekSex && !seekTouched.current) {
      const flipped = opposite(sex);
      setLive(fill(policy.sought_flipped, { sought: flipped === "male" ? "Men" : "Women" }));
      onChange({ ...prefs, seekSex: flipped });
    } else if (sex !== was) {
      // Phase 6 (F13): no request — the list changes in place; say so
      announce.current = sex === "male" ? "men" : "women";
    }
  }, [about, prefs, onChange, saveAbout, policy.sought_flipped]);
  /** Sought sex: part of the search. The own sex the panel was showing is
   * kept (stored) so the visitor's "I'm a" never flips under them. */
  const onSeekSex = useCallback((seekSex: "male" | "female") => {
    seekTouched.current = true;
    if (!about.sex) saveAbout({ ...about, sex: effectiveSex(about, prefs.seekSex) });
    onChange({ ...prefs, seekSex });
  }, [about, prefs, onChange, saveAbout]);

  /** Phase 6 (F13): an "about you" change from the rail (education, race)
   * re-selects the list with no request; the live region and the line
   * under the count say what changed. */
  const onAboutChange = useCallback((next: AboutYou) => {
    if ((next.race ?? null) !== (about.race ?? null)) announce.current = policy.results_change_race;
    else if ((next.edu ?? null) !== (about.edu ?? null)) announce.current = policy.results_change_education;
    saveAbout(next);
  }, [about, saveAbout, policy.results_change_race, policy.results_change_education]);

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
  // whether the rail has more below its fold (for the bottom fade)
  useEffect(() => {
    const el = railRef.current;
    if (!el) return;
    const check = () => setRailMore(el.scrollHeight - el.scrollTop - el.clientHeight > 4);
    check();
    el.addEventListener("scroll", check, { passive: true });
    const ro = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(check);
    ro?.observe(el);
    if (el.firstElementChild) ro?.observe(el.firstElementChild);
    return () => {
      el.removeEventListener("scroll", check);
      ro?.disconnect();
    };
  }, [desk]);

  const qs = toSearchParams(prefs).toString();
  const selected = useMemo(() => selectVariant(response, about), [response, about]);
  // the rows have rendered in their new places: slide them there
  useLayoutEffect(() => { play(); }, [selected, play]);
  // Phase 6 (F05, F13): a change has landed — tint what moved, and say
  // what changed and, when it did, the new top three (names only)
  useEffect(() => {
    const order = selected.ranked.map((r) => r.cbsa);
    const was = prevOrder.current;
    prevOrder.current = order;
    const change = announce.current;
    announce.current = null;
    if (change === null || !was) return;
    setMoved(new Set(order.filter((c, i) => was[i] !== c)));
    let text = fill(policy.results_updated, { change });
    const top = selected.ranked.slice(0, 3).map((r) => r.display_name.split(",")[0]);
    if (top.length === 3 && order.slice(0, 3).join() !== was.slice(0, 3).join()) {
      text += ". " + fill(policy.results_new_top, { a: top[0], b: top[1], c: top[2] });
    }
    setLive(text);
    setNotice({ text, n: Date.now() });
    setNoticeSlot(true);
  }, [selected, policy.results_updated, policy.results_new_top]);
  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(null), 6000);
    return () => clearTimeout(t);
  }, [notice]);
  useEffect(() => {
    if (!moved.size) return;
    const t = setTimeout(() => setMoved(new Set()), 2000);
    return () => clearTimeout(t);
  }, [moved]);
  // Phase 6 (F27): while the bottom bar shows, focus never hides under it
  useEffect(() => {
    const on = !desk && barVisible;
    document.documentElement.style.scrollPaddingBottom = on ? "88px" : "";
    return () => { document.documentElement.style.scrollPaddingBottom = ""; };
  }, [desk, barVisible]);
  // Phase 6 (F18): the visitor's place in these results — how many rows
  // showed and the city they opened — kept for this tab (sessionStorage,
  // never an "about you" detail) and restored on the way back
  useLayoutEffect(() => {
    const place = readPlace();
    if (!place || place.from !== window.location.pathname + window.location.search) return;
    setVisible((v) => Math.max(v, place.visible));
    requestAnimationFrame(() => requestAnimationFrame(() => {
      listRef.current?.querySelector<HTMLElement>(`[data-cbsa="${place.cbsa}"]`)
        ?.scrollIntoView({ block: "center" });
    }));
  }, []);
  const keepPlace = (e: React.MouseEvent) => {
    const a = (e.target as HTMLElement).closest<HTMLAnchorElement>('a[href^="/city/"]');
    const holder = a?.closest<HTMLElement>("[data-cbsa]");
    if (!a || !holder) return;
    writePlace({
      from: window.location.pathname + window.location.search,
      to: a.getAttribute("href") ?? "",
      visible,
      cbsa: holder.dataset.cbsa!,
    });
  };
  const afterClose = useCallback(() => {
    const go = afterSheet.current;
    afterSheet.current = null;
    if (go === "results" && headingRef.current) {
      headingRef.current.scrollIntoView({ block: "start" });
      headingRef.current.focus({ preventScroll: true });
      return true;
    }
    if (go === "quick" && quickRef.current) {
      quickRef.current.scrollIntoView({ block: "start" });
      quickRef.current.querySelector<HTMLElement>('[data-testid="self-sex"]')?.focus({ preventScroll: true });
      return true;
    }
    return false;
  }, []);
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
  const compareFrom = (slug: string) => router.push(`/compare?a=${slug}${qs ? `&${qs}` : ""}`);
  const cardOpen = featured.find((r) => r.cbsa === openCard) ?? null;
  // Best first / Worst first: in the results header, and below 640px under
  // the three cards instead (Phase 6, F15: the #1 card's score in the
  // first screen of a phone) — the same control, shown in one place
  const sortControl = (
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
  );

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
      onAbout={onAboutChange}
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

        {/* Phase 6 (F27): the bar's markup comes before the results, so the
            keyboard reaches it before the list (it stays fixed at the
            bottom of the screen) */}
        {!desk && (
          <div
            className={`fixed inset-x-0 bottom-0 z-30 bg-surface px-4 pb-[calc(14px+env(safe-area-inset-bottom))] pt-2.5 shadow-overlay ${barVisible ? "" : "hidden"}`}
            data-testid="bottom-bar"
          >
            {/* Phase 6 (F05): a search in flight shows on the bar itself,
                where a phone's eyes are (static under reduced motion) */}
            <div aria-hidden="true" className={`absolute inset-x-0 top-0 ${pending ? "progress-line" : "h-0.5"}`}
              data-testid="bar-pending-line" />
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
        )}

        <div className="grid gap-8 pt-5 sm:pt-11 desk:grid-cols-[288px_1fr] desk:items-start">
          {desk && (
            // after the Phase 5 report (Nathan): the rail scrolls inside
            // itself, so its last controls never wait for the page to end;
            // it sits above the results (z-10), so nothing it opens is
            // covered by a card
            <aside
              ref={railRef}
              aria-label={policy.adjust_search}
              className="rail-scroll sticky top-4 z-10 max-h-[calc(100dvh-2rem)] overflow-y-auto overscroll-contain rounded-lg border border-rule bg-surface p-5 max-desk:hidden"
              data-testid="rail"
            >
              {rail}
              {/* a fade at the bottom while there is more to scroll to */}
              <div
                aria-hidden="true"
                className={`pointer-events-none sticky bottom-0 -mx-5 -mt-10 h-10 bg-gradient-to-t from-surface to-transparent transition-opacity ${railMore ? "opacity-100" : "opacity-0"}`}
                data-testid="rail-more"
              />
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
                    <h2 id="results-heading" ref={headingRef} tabIndex={-1}
                      className="mt-1 scroll-mt-4 font-display text-h2" data-testid="list-heading">
                      {fill(prefs.sort === "worst_first" ? policy.results_heading_worst
                        : policy.results_heading_best, short)}
                    </h2>
                    <p className="text-body-sm text-ink-3" data-testid="results-count">
                      {fill(policy.results_count, { n: selected.counts.ranked.toLocaleString("en-US") })}
                    </p>
                    {noticeSlot && (
                      <p className="mt-1 min-h-5 text-body-sm font-semibold text-ink-2" data-testid="results-notice">
                        {notice?.text}
                      </p>
                    )}
                    {excluded > 0 && (
                      <p className="mt-1 text-body-sm text-ink-2" data-testid="excluded-note">
                        {policy.excluded_count.replace("{n}", excluded.toLocaleString("en-US"))}
                      </p>
                    )}
                    {/* Phase 6 (F01): on a same-sex search the count is every
                        single person of the sought sex in these ages — said
                        here, chosen in the browser from the stored own sex,
                        inside the variant veil (never in the server's HTML) */}
                    {sameSex && (
                      <p data-variant="" className="mt-1.5 max-w-[58ch] text-caption text-ink-2" data-testid="same-sex-note">
                        {fill(policy.same_sex_pool_note, {
                          sought_one: prefs.seekSex === "male" ? "man" : "woman", sought: short.sought })}
                      </p>
                    )}
                  </div>
                  <div className="max-sm:hidden">{sortControl}</div>
                </div>
                <div aria-hidden="true" className={pending ? "progress-line mb-3" : "mb-3 h-0.5"} data-testid="pending-line" />
                <p className="sr-only" aria-live="polite" data-testid="results-live">{live}</p>

                <div ref={listRef} data-testid="ranked-list" data-variant="" onClickCapture={keepPlace}>
                  <ol aria-label="Cities" className="grid gap-4 md:grid-cols-3">
                    {featured.map((row, i) => (
                      <FeaturedCard
                        key={row.cbsa}
                        first={i === 0}
                        row={row}
                        meta={meta}
                        href={cityHref(row.slug)}
                        photo={photos[row.slug]}
                        median={selected.score_median}
                        open={openCard === row.cbsa}
                        tinted={moved.has(row.cbsa)}
                        inline={!wide}
                        sameSex={sameSex}
                        onToggle={() => setOpenCard((c) => (c === row.cbsa ? null : row.cbsa))}
                        onCompare={() => compareFrom(row.slug)}
                      />
                    ))}
                  </ol>
                  {/* Phase 6 (F06): from 768px a card's detail opens in one
                      panel spanning the three cards, directly under them */}
                  {wide && cardOpen && (
                    <div className="mt-4" data-cbsa={cardOpen.cbsa}>
                      <RowDetail id={`card-detail-${cardOpen.cbsa}`} row={cardOpen} meta={meta}
                        href={cityHref(cardOpen.slug)} sameSex={sameSex} variant="panel"
                        testid="card-detail" onCompare={() => compareFrom(cardOpen.slug)} />
                    </div>
                  )}
                  <div className="mt-6 sm:hidden">{sortControl}</div>

                  {rest.length > 0 && (
                    <>
                      <div className="mt-7 flex flex-wrap items-center justify-between gap-3">
                        <FindInResults
                          label={policy.find_in_results}
                          clearLabel={policy.clear}
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
                            onCompare={() => compareFrom(row.slug)}
                            highlighted={highlight === row.slug || moved.has(row.cbsa)}
                            sameSex={sameSex}
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

                <ScoreExplainer meta={meta} sameSex={sameSex} />
              </>
            )}
          </section>
        </div>
      </main>

      {!desk && (
        <>
          <BottomSheet
            open={sheetOpen}
            onClose={() => setSheetOpen(false)}
            title={policy.adjust_search}
            footerLabel={policy.show_results}
            closeLabel={policy.close}
            returnFocus={adjustRef}
            onFooter={() => { afterSheet.current = "results"; }}
            afterClose={afterClose}
            lead={
              // Phase 6 (F19): the whole search, and the way to the part
              // the sheet doesn't hold (sex and ages are in the hero)
              <button
                type="button"
                data-testid="sheet-summary"
                onClick={() => { afterSheet.current = "quick"; setSheetOpen(false); }}
                className="mb-4 flex min-h-11 w-full items-center rounded-md bg-sunken px-3.5 text-left text-body-sm font-semibold text-ink hover:bg-hover"
              >
                {fill(policy.sheet_search_summary, {
                  you: selfSex === "male" ? "Man" : "Woman",
                  age: prefs.selfAge,
                  sought: prefs.seekSex === "male" ? "Men" : "Women",
                  ages: `${prefs.ageMin}–${prefs.ageMax}`,
                })}
              </button>
            }
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
function ScoreExplainer({ meta, sameSex }: { meta: Meta; sameSex: boolean }) {
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
      {/* Phase 6 (F01): the same-sex caption on a same-sex search, chosen in
          the browser like the results header's note */}
      <p data-variant="" className="mt-1 max-w-[70ch] text-caption text-ink-3" data-testid="balance-footnote">
        {sameSex ? s.balance_caption_same_sex : s.balance_caption}
      </p>
    </section>
  );
}
