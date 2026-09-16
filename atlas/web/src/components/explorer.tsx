"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Meta, RankResponse } from "@/lib/types";
import {
  describePrefs,
  toRankBody,
  toSearchParams,
  type Prefs,
} from "@/lib/prefs";
import { Controls } from "./controls";
import { RankRow } from "./rank-row";
import { SuppressionFooter } from "./suppression-footer";
import { fmtInt } from "@/lib/format";

/** The ranking page's client shell (§10.2): results first, controls beside
 * them, the list visibly reordering as a control moves. The first response
 * arrives server-rendered; every change re-asks the API through the
 * same-origin proxy and rewrites the query string, so the URL stays the
 * state (§10.1). Nothing is recomputed here — score, margins, tiers,
 * contributions and explanations all arrive from the API. */
export function Explorer({
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
  const seq = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

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
          setError(typeof j.detail === "string" ? j.detail : `request failed (${r.status})`);
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
      // the URL is the state — rewrite it without a navigation
      const qs = toSearchParams(next).toString();
      window.history.replaceState(null, "", `${window.location.pathname}?${qs}`);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => refetch(next), 180);
    },
    [refetch],
  );

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  const raceActive = Boolean(prefs.race?.length);
  const [mobileControls, setMobileControls] = useState(false);

  return (
    <div className="mx-auto grid max-w-6xl grid-cols-1 gap-x-10 px-5 lg:grid-cols-[280px_1fr]">
      <aside className="lg:sticky lg:top-6 lg:self-start" aria-label="Your preferences">
        {/* ONE Controls instance: duplicated form fields break both strict
            label association and screen-reader navigation */}
        <button
          type="button"
          className="mb-3 w-full border border-rule bg-raised px-3 py-2 text-left text-sm font-semibold lg:hidden"
          aria-expanded={mobileControls}
          onClick={() => setMobileControls((o) => !o)}
        >
          {mobileControls ? "Hide preferences" : "Edit preferences"}
        </button>
        <div className={`${mobileControls ? "block" : "hidden"} pb-6 lg:block lg:pb-0`}>
          <Controls prefs={prefs} meta={meta} onChange={onChange} />
        </div>
      </aside>

      <main id="main" className="min-w-0">
        <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-rule pb-2">
          <h2 className="text-sm text-ink-2">
            Showing <span className="num text-ink">{fmtInt(response.counts.ranked)}</span>{" "}
            ranked metros for {describePrefs(prefs, { withIdentity: false })}
            {raceActive ? ", filtered by race or ethnicity" : ""}.
          </h2>
          <p aria-live="polite" className="min-h-4 text-xs text-ink-3">
            {pending ? "recalculating…" : ""}
          </p>
        </div>

        {error && (
          <p role="alert" className="mt-3 border-l-2 border-crit pl-3 text-sm text-crit">
            {error}
          </p>
        )}

        {response.few_metros_notice && (
          <p
            className="mt-3 border-l-2 border-warn pl-3 text-sm text-ink-2"
            data-testid="few-metros-notice"
          >
            {meta.policy_strings.few_metros}
          </p>
        )}

        <ol
          aria-label="Ranked metros"
          className={pending ? "opacity-60 transition-opacity" : "transition-opacity"}
          aria-busy={pending}
          data-testid="ranked-list"
        >
          {response.ranked.map((row) => (
            <RankRow
              key={row.cbsa}
              row={row}
              meta={meta}
              raceActive={raceActive}
              queryString={toSearchParams(prefs).toString()}
            />
          ))}
        </ol>
        {response.ranked.length === 0 && (
          <p className="mt-6 text-sm text-ink-2">
            No metro has enough sample to rank for this query. Loosen a filter
            — every widening adds metros back.
          </p>
        )}

        <SuppressionFooter response={response} meta={meta} />

        <p className="mt-4 text-xs text-ink-3">
          Reproducible link for this exact ranking, pinned to data{" "}
          <span className="num">{response.data_version}</span> and model{" "}
          <span className="num">{response.model_version}</span>:{" "}
          <a className="text-accent underline underline-offset-2" href={response.permalink}>
            permalink
          </a>
        </p>
      </main>
    </div>
  );
}
