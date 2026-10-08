"use client";

import Link from "next/link";
import type { Meta, RankedRow } from "@/lib/types";
import { divergingBar, fill } from "@/lib/results";
import { signedPoints } from "@/lib/format";
import { BalanceTrack } from "./balance-track";
import { WhyChips } from "./why-chips";

/** A score's 0-100 track: --sunken, filled in the accent to the served
 * score (presentation scaling of the served value). */
export function ScoreTrack({ score, className }: { score: number; className: string }) {
  return (
    <div aria-hidden="true" className={`relative overflow-hidden rounded-full bg-sunken ${className}`}>
      <div
        className="absolute inset-y-0 left-0 rounded-full bg-accent"
        style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
      />
    </div>
  );
}

/** Phase 5: one of the top three, as a card — a photo slot (the city's
 * photograph only where it may be cropped, public domain or CC0, cover-
 * cropped; otherwise its locator map), a rank medallion (amber for the top
 * three ranks), the city, the score out of 100 with its track, the pool,
 * and the chips. */
export function FeaturedCard({
  row,
  meta,
  href,
  sought,
  photo,
}: {
  row: RankedRow;
  meta: Meta;
  href: string;
  sought: string;
  photo?: { src: string; alt: string };
}) {
  const s = meta.policy_strings;
  const top = row.rank <= 3;
  return (
    <li
      className="flex flex-col overflow-hidden rounded-lg border border-rule bg-surface"
      data-cbsa={row.cbsa}
      data-rank={row.rank}
      data-slug={row.slug}
      data-testid="featured-card"
    >
      <div className="relative aspect-[16/10] bg-sunken max-sm:aspect-[2/1]">
        {photo ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img src={photo.src} alt={photo.alt} className="h-full w-full object-cover" data-testid="card-photo" />
        ) : (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img src={`/map/${row.cbsa}.svg`} alt="" className="h-full w-full object-contain p-3" data-testid="card-map" />
        )}
        <span
          aria-hidden="true"
          className={`absolute left-3 top-3 flex h-9 w-9 items-center justify-center rounded-full font-display text-data-m font-bold text-ink shadow-sm ${top ? "bg-highlight" : "border border-line-strong bg-surface"}`}
        >
          {row.rank}
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-2.5 px-4 pb-[18px] pt-4">
        <h3 className="font-display text-h3">
          <span className="sr-only">Ranked {row.rank}: </span>
          <Link href={href} className="hover:text-accent-hover hover:underline">
            {row.display_name}
          </Link>
        </h3>
        <div className="flex items-end justify-between gap-3">
          <p className="flex items-baseline gap-1">
            <span className="font-display text-data-xl" data-testid="score">{row.score_display}</span>
            <span className="text-body-sm font-medium text-ink-3">{s.score_out_of}</span>
          </p>
          <p className="flex flex-col items-end text-right">
            <span className="text-data-m">{row.pool.toLocaleString("en-US")}</span>
            <span className="text-caption text-ink-3">{fill(s.pool_short_unit, { sought })}</span>
          </p>
        </div>
        <ScoreTrack score={row.score} className="h-1.5 w-full" />
        <WhyChips movers={row.movers} meta={meta} />
        <span className="sr-only">{row.summary_line}</span>
      </div>
    </li>
  );
}

/** Phase 5: a result row from the fourth on — rank, city with its chips,
 * the pool, the score over its track, and a chevron that opens the row's
 * detail (a click on the row's empty space does too). Column labels sit
 * once above the list, so "Overall score" no longer repeats here. On a
 * phone the pool moves under the city's name and the score sits top
 * right. */
export function ResultRow({
  row,
  meta,
  href,
  sought,
  open,
  onToggle,
  onCompare,
  highlighted = false,
}: {
  row: RankedRow;
  meta: Meta;
  href: string;
  sought: string;
  open: boolean;
  onToggle: () => void;
  onCompare: () => void;
  highlighted?: boolean;
}) {
  const s = meta.policy_strings;
  const detailId = `detail-${row.cbsa}`;
  const pool = row.pool.toLocaleString("en-US");
  return (
    <li
      className={`border-b border-rule ${open ? "bg-hover" : ""} ${highlighted ? "bg-hover transition-colors" : ""}`}
      data-cbsa={row.cbsa}
      data-rank={row.rank}
      data-slug={row.slug}
    >
      <div
        className="grid cursor-pointer grid-cols-[32px_1fr_74px] items-center gap-x-2.5 px-1 py-3.5 hover:bg-hover sm:grid-cols-[40px_1fr_112px_104px_18px] sm:gap-x-3.5 sm:px-4"
        onClick={(e) => {
          // a click on the row's empty space toggles it; links and
          // buttons keep their own job
          if (!(e.target as HTMLElement).closest("a,button")) onToggle();
        }}
      >
        <span aria-hidden="true" className="font-display text-h3 text-ink-2">{row.rank}</span>
        <div className="flex min-w-0 flex-col gap-1.5">
          <h3 className="text-title">
            <span className="sr-only">Ranked {row.rank}: </span>
            <Link href={href} className="hover:text-accent-hover hover:underline">
              {row.display_name}
            </Link>
          </h3>
          <p className="-mt-0.5 text-caption text-ink-3 sm:hidden">
            {pool} {fill(s.pool_short_unit, { sought })}
          </p>
          <WhyChips movers={row.movers} meta={meta} />
          <span className="sr-only">{row.summary_line}</span>
        </div>
        <p className="flex flex-col items-end text-right max-sm:hidden">
          <span className="text-body font-semibold">{pool}</span>
          <span className="text-overline font-normal tracking-normal text-ink-3">
            {fill(s.pool_row_unit, { sought })}
          </span>
        </p>
        <div className="flex flex-col items-end gap-1.5 max-sm:row-span-2 max-sm:self-start">
          <span className="font-display text-data-l" data-testid="score">{row.score_display}</span>
          <ScoreTrack score={row.score} className="h-1 w-16 sm:w-24" />
          <ToggleButton open={open} detailId={detailId} label={fill(s.row_details, { city: row.display_name })}
            onToggle={onToggle} className="mt-1 sm:hidden" />
        </div>
        <ToggleButton open={open} detailId={detailId} label={fill(s.row_details, { city: row.display_name })}
          onToggle={onToggle} className="max-sm:hidden" />
      </div>
      {open && <RowDetail id={detailId} row={row} meta={meta} href={href} onCompare={onCompare} />}
    </li>
  );
}

function ToggleButton({ open, detailId, label, onToggle, className }: {
  open: boolean; detailId: string; label: string; onToggle: () => void; className: string;
}) {
  return (
    <button
      type="button"
      aria-expanded={open}
      aria-controls={detailId}
      aria-label={label}
      data-testid="row-toggle"
      onClick={onToggle}
      className={`-m-[13px] flex h-11 w-11 items-center justify-center rounded-full text-ink-3 hover:text-ink ${className}`}
    >
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" fill="none"
        stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"
        className={open ? "rotate-180" : ""}>
        <path d="M4 6l4 4 4-4" />
      </svg>
    </button>
  );
}

/** A row's detail: the balance, the compatibility figure, and what moved
 * the score — the six pillar contributions the API served, as diverging
 * bars (±25 points spans the half-width, clamped), sorted by value. Every
 * number is served; the bars are presentation scaling. */
function RowDetail({ id, row, meta, href, onCompare }: {
  id: string; row: RankedRow; meta: Meta; href: string; onCompare: () => void;
}) {
  const s = meta.policy_strings;
  const label = (pillar: string) =>
    pillar === "pool" ? meta.features.pool_size.chip_label
    : pillar === "match" ? meta.features.match_propensity.chip_label
    : meta.pillars[pillar]?.display_name ?? pillar;
  const parts = row.contributions
    .filter((c): c is { pillar: string; value: number } => c.value != null)
    .sort((a, b) => b.value - a.value);
  const city = row.display_name.split(",")[0];
  const match = row.match;
  return (
    <div
      id={id}
      className="grid gap-7 bg-hover px-1 pb-5 pt-1 sm:grid-cols-[1fr_1fr_1.4fr] sm:pl-[70px] sm:pr-4"
      data-testid="row-detail"
    >
      <section>
        <h4 className="mb-2 text-caption font-semibold text-ink-2">{s.balance_label}</h4>
        <BalanceTrack balance={row.balance} meta={meta} id={id} />
      </section>
      <section data-testid={match.available && match.display != null ? "match-figure" : undefined}>
        <h4 className="mb-2 text-caption font-semibold text-ink-2">
          {meta.features.match_propensity.display_name}
        </h4>
        {match.available && match.display != null ? (
          <div>
            <p className="flex flex-wrap items-baseline gap-x-2">
              <span className="text-data-l" data-figure="">{match.display}</span>
              <span className="text-caption text-ink-3">{match.unit_line}</span>
            </p>
            <p className="mt-1.5 text-caption text-ink-3">{meta.pillars.match?.definition}</p>
          </div>
        ) : (
          <p className="text-body-sm text-ink-3">{s.card_missing}</p>
        )}
      </section>
      <section>
        <h4 className="text-caption font-semibold text-ink-2">{s.moved_heading}</h4>
        <p className="mb-2 text-caption text-ink-3">{s.moved_caption}</p>
        <ul className="flex flex-col gap-1" data-testid="moved-bars">
          {parts.map((c) => {
            const bar = divergingBar(c.value);
            const plus = c.value >= 0;
            return (
              <li key={c.pillar} className="grid grid-cols-[96px_1fr_44px] items-center gap-2 text-caption">
                <span className="text-ink-2">{label(c.pillar)}</span>
                <span aria-hidden="true" className="relative h-2.5">
                  <span className="absolute -inset-y-[3px] left-1/2 w-px bg-line-strong" />
                  <span
                    className={`absolute top-px h-2 rounded-xs ${plus ? "bg-good" : "bg-poor"}`}
                    style={{ left: `${bar.left * 100}%`, width: `${bar.width * 100}%` }}
                  />
                </span>
                <span className={`text-right font-semibold ${plus ? "text-good-strong" : "text-poor-strong"}`}>
                  {signedPoints(c.value)}
                </span>
              </li>
            );
          })}
        </ul>
        <p className="mt-3 flex flex-wrap gap-x-5 text-body-sm font-semibold">
          <Link href={href} className="inline-flex min-h-11 items-center text-accent hover:text-accent-hover">
            {fill(s.open_city, { city })}
          </Link>
          <button type="button" onClick={onCompare}
            className="inline-flex min-h-11 items-center text-accent hover:text-accent-hover">
            {s.compare_action}
          </button>
        </p>
      </section>
    </div>
  );
}
