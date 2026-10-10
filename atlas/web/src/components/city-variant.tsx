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
 * ADR 0018): the for-your-search card of a ranked city — its rank, the
 * balance, the compatibility figure, the movers as chips (Phase 5: led by
 * the overall score out of 100) — and, for a city
 * the search leaves out, the balance that survives. The server cut the
 * response down to this city (lib/variants sliceVariants); this selects
 * the visitor's variant from it and renders the API's numbers. */
export function CityVariantPart({
  part,
  slice,
  cbsa,
  city,
  searchWords,
  meta,
}: {
  part: "ranked" | "balance";
  slice: VariantResponse;
  cbsa: string;
  city: string;
  searchWords: string;
  meta: Meta;
}) {
  const about = useAboutYou();
  const sel = useMemo(() => selectVariant(slice, about), [slice, about]);
  const policy = meta.policy_strings;
  // Phase 6 (F01): a same-sex search, as this browser holds the visitor's
  // own sex — the notes are chosen here, inside the variant veil
  const sought = slice.variants.sought_sex;
  const sameSex = effectiveSex(about, sought) === sought;
  if (part === "ranked") {
    const ranked = sel.ranked.find((r) => r.cbsa === cbsa);
    if (!ranked) return null;
    return (
      <section
        className="flex flex-col gap-5 rounded-lg border border-rule bg-surface px-5 py-6 sm:px-7"
        data-testid="ranked-card"
        data-variant=""
      >
        <h2 className="font-display text-h3">
          Where {city} lands for your search
        </h2>
        {/* Phase 5: the overall score leads — out of 100, on its track */}
        <div className="flex max-w-[420px] flex-col gap-2">
          <p className="flex items-baseline gap-1">
            <span className="font-display text-data-xl" data-testid="score">{ranked.score_display}</span>
            <span className="text-body-sm font-medium text-ink-3">{policy.score_out_of}</span>
          </p>
          <ScoreTrack score={ranked.score} className="h-1.5 w-full" median={sel.score_median}
            medianCaption={policy.score_median_caption} />
          <span className="text-caption font-semibold text-ink-2" data-testid="score-label">
            {policy.overall_score_label}
          </span>
        </div>
        <div className="flex flex-wrap items-start gap-x-12 gap-y-5">
          <div className="flex flex-col gap-1">
            <p className="flex items-baseline gap-2">
              <span className="font-display text-h2" data-testid="city-rank">{ranked.rank}</span>
              <span className="text-body-sm text-ink-2">
                of {sel.counts.ranked.toLocaleString("en-US")} cities
                for {searchWords}
              </span>
            </p>
            <p className="flex items-baseline gap-2">
              <span className="text-data-m">{ranked.pool.toLocaleString("en-US")}</span>
              <span className="text-body-sm text-ink-2">{meta.features.pool_size.unit}</span>
            </p>
            {/* Phase 6: under the matches line, the metro's served cautions
                (F08) and, on a same-sex search, what matches count (F01) */}
            <FlagCaptions flags={ranked.flags} meta={meta} className="mt-1 max-w-[46ch]" />
            {sameSex && (
              <p className="mt-1 max-w-[46ch] text-caption text-ink-2" data-testid="same-sex-note">
                {fill(policy.same_sex_pool_note, { sought_one: sought === "male" ? "man" : "woman",
                  sought: sought === "male" ? "men" : "women" })}
              </p>
            )}
          </div>
          <div className="min-w-[200px]">
            <h3 className="mb-2 text-caption font-semibold text-ink-2">{policy.balance_label}</h3>
            <BalanceDots balance={ranked.balance} meta={meta} id={`city-${cbsa}`} sameSex={sameSex} />
          </div>
          {/* the compatibility figure beside pool and balance (no box or
              band since Phase 4b) */}
          <MatchFigure match={ranked.match} meta={meta} />
        </div>
        <WhyChips movers={ranked.lifestyle_movers} meta={meta} />
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
        {sameSex ? policy.balance_caption_same_sex : policy.balance_caption}
      </p>
    </section>
  );
}
