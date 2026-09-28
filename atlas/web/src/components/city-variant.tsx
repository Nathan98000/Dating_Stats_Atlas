"use client";

import { useMemo } from "react";
import type { Meta, VariantResponse } from "@/lib/types";
import { selectVariant } from "@/lib/variants";
import { useAboutYou } from "@/lib/use-about-you";
import { BalanceTally } from "./tally";
import { MatchFigure } from "./match";

/** The parts of the city page an "about you" variant changes (m4.0.0,
 * ADR 0018): the for-your-search card of a ranked city — its rank, the
 * balance, the compatibility figure, the movers line — and, for a city
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
  if (part === "ranked") {
    const ranked = sel.ranked.find((r) => r.cbsa === cbsa);
    if (!ranked) return null;
    return (
      <section
        className="flex flex-col gap-4 rounded-xl border border-rule bg-surface px-7 py-6"
        data-testid="ranked-card"
        data-variant=""
      >
        <h2 className="font-display text-[21px] font-semibold">
          Where {city} lands for your search
        </h2>
        <div className="flex flex-wrap items-center gap-x-12 gap-y-4">
          <div className="flex items-baseline gap-2">
            <span className="font-display text-[44px] font-semibold leading-none" data-testid="city-rank">
              {ranked.rank}
            </span>
            <span className="text-sm text-ink-2">
              of {sel.counts.ranked.toLocaleString("en-US")} cities
              for {searchWords}
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-display text-[30px] font-semibold leading-none">
              {ranked.pool.toLocaleString("en-US")}
            </span>
            <span className="text-sm text-ink-2">
              {meta.features.pool_size.unit}
            </span>
          </div>
          <div className="min-w-[220px]">
            <BalanceTally balance={ranked.balance} compact />
          </div>
          {/* the compatibility figure beside pool and balance */}
          <MatchFigure match={ranked.match} meta={meta} id={`match-${cbsa}`} />
        </div>
        <p className="max-w-[72ch] text-sm text-ink-2">{ranked.summary_line}</p>
      </section>
    );
  }
  const suppressed = sel.suppressed.find((r) => r.cbsa === cbsa);
  const balance = suppressed?.balance;
  if (!balance || !balance.available) return null;
  return (
    <section
      className="flex flex-col gap-2 rounded-xl border border-rule bg-surface px-7 py-6"
      data-testid="balance-survives"
      data-variant=""
    >
      <h2 className="text-[15px] font-semibold">
        {meta.features.pool_balance.display_name} in {city}
      </h2>
      <BalanceTally balance={balance} />
      <p className="max-w-[64ch] text-[12.5px] text-ink-3">
        {policy.balance_caption}
      </p>
    </section>
  );
}
