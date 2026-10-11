"use client";

import { useMemo } from "react";
import type { Meta, VariantResponse } from "@/lib/types";
import { selectVariant } from "@/lib/variants";
import { useAboutYou } from "@/lib/use-about-you";
import { BalanceDots } from "./balance-dots";
import { MatchFigure } from "./match";
import { FlagCaptions, ScoreTrack } from "./row";
import { effectiveSex } from "@/lib/about-you";
import { fill } from "@/lib/results";
import { WhyChips } from "./why-chips";

/** The parts of the city page an "about you" variant changes (m4.0.0,
 * ADR 0018): the for-your-search card of a ranked city and, for a city the
 * search leaves out, the balance that survives. The server cut the response
 * down to this city (lib/variants sliceVariants); this selects the visitor's
 * variant from it and renders the API's numbers.
 *
 * The card reads in the order a visitor asks (Nathan, 2026-10-10, on its
 * hierarchy): where the city ranks — the ranking cards' medallion, amber for
 * the top three — then its overall score, its label before it, on its track,
 * then why (the chips). Past a hairline come the people numbers: the two the
 * score counts (matches, then compatibility), each label, figure, unit, and
 * last balance, which is shown and never scored. From 768px the verdict and
 * the people sit side by side; one column below. */
export function CityVariantPart({
  part,
  slice,
  cbsa,
  city,
  search,
  meta,
}: {
  part: "ranked" | "balance";
  slice: VariantResponse;
  cbsa: string;
  city: string;
  /** the search in words, the line under the card's heading ("Single men
   * 28–40 (never married, divorced or widowed)") */
  search: string;
  meta: Meta;
}) {
  const about = useAboutYou();
  const sel = useMemo(() => selectVariant(slice, about), [slice, about]);
  const policy = meta.policy_strings;
  // Phase 6 (F01): a same-sex search, as this browser holds the visitor's
  // own sex — the notes are chosen here, inside the variant veil
  const sought = slice.variants.sought_sex;
  const sameSex = effectiveSex(about, sought) === sought;
  const soughtWords = sought === "male" ? "men" : "women";
  if (part === "ranked") {
    const ranked = sel.ranked.find((r) => r.cbsa === cbsa);
    if (!ranked) return null;
    const top = ranked.rank <= 3;
    return (
      <section
        className="flex flex-col gap-5 rounded-lg border border-rule bg-surface px-5 py-6 sm:px-7"
        data-testid="ranked-card"
        data-variant=""
      >
        <div className="flex flex-col gap-1">
          <h2 className="font-display text-h3">
            Where {city} lands for your search
          </h2>
          <p className="text-caption text-ink-3" data-testid="city-search">{search}</p>
        </div>
        <div className="grid gap-y-5 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] md:gap-x-8">
          {/* the verdict: the spot, the score, why */}
          <div className="flex flex-col gap-5" data-testid="city-spot">
            <p className="flex items-center gap-3">
              <span className="sr-only">Ranked </span>
              <span
                className={`inline-flex h-14 min-w-14 items-center justify-center rounded-full px-3 font-display text-data-l font-bold text-ink ${top ? "bg-highlight" : "border border-line-strong bg-surface"}`}
                data-testid="city-rank"
              >
                {ranked.rank}
              </span>
              <span className="text-body-lg text-ink-2">
                of {sel.counts.ranked.toLocaleString("en-US")} cities
              </span>
            </p>
            <div className="flex max-w-[420px] flex-col gap-1">
              <span className="text-caption font-semibold text-ink-2" data-testid="score-label">
                {policy.overall_score_label}
              </span>
              <p className="flex items-baseline gap-1">
                <span className="font-display text-data-xl" data-testid="score">{ranked.score_display}</span>
                <span className="text-body-sm font-medium text-ink-3">{policy.score_out_of}</span>
              </p>
              <ScoreTrack score={ranked.score} className="mt-2 h-1.5 w-full" median={sel.score_median}
                medianCaption={policy.score_median_caption} />
            </div>
            <WhyChips movers={ranked.lifestyle_movers} meta={meta} />
          </div>
          {/* the people: matches and compatibility, then balance */}
          <div className="flex flex-col gap-4 border-t border-rule pt-5 md:border-l md:border-t-0 md:pl-8 md:pt-0"
            data-testid="city-people">
            <div className="grid grid-cols-2 gap-x-6 gap-y-4">
              <div className="flex flex-col gap-1" data-testid="city-matches">
                <span className="text-caption font-semibold text-ink-2">{meta.features.pool_size.display_name}</span>
                <span className="text-data-m">{ranked.pool.toLocaleString("en-US")}</span>
                <span className="text-caption text-ink-3">{fill(policy.pool_row_unit, { sought: soughtWords })}</span>
              </div>
              {/* no box or band since Phase 4b */}
              <MatchFigure match={ranked.match} meta={meta} />
            </div>
            {/* Phase 6: what qualifies the matches — the metro's served
                cautions (F08) and, on a same-sex search, what they count (F01) */}
            <FlagCaptions flags={ranked.flags} meta={meta} className="max-w-[52ch]" />
            {sameSex && (
              <p className="max-w-[52ch] text-caption text-ink-2" data-testid="same-sex-note">
                {fill(policy.same_sex_pool_note, { sought_one: sought === "male" ? "man" : "woman",
                  sought: soughtWords })}
              </p>
            )}
            <div className="border-t border-rule pt-4">
              <h3 className="mb-2 text-caption font-semibold text-ink-2">{policy.balance_label}</h3>
              <BalanceDots balance={ranked.balance} meta={meta} id={`city-${cbsa}`} />
            </div>
          </div>
        </div>
        <p className="sr-only">{ranked.summary_line}</p>
      </section>
    );
  }
  const suppressed = sel.suppressed.find((r) => r.cbsa === cbsa);
  const balance = suppressed?.balance;
  if (!balance || !balance.available) return null;
  return (
    <section
      className="flex flex-col gap-2 rounded-lg border border-rule bg-surface px-5 py-6 sm:px-7"
      data-testid="balance-survives"
      data-variant=""
    >
      <h2 className="text-body font-semibold">
        {meta.features.pool_balance.display_name} in {city}
      </h2>
      <BalanceDots balance={balance} meta={meta} id={`city-${cbsa}-s`} caption={false} />
      <p className="max-w-[64ch] text-caption text-ink-3">
        {policy.balance_caption}
      </p>
    </section>
  );
}
