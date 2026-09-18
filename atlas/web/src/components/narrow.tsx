"use client";

import type { Meta } from "@/lib/types";
import { describeSearch, wideners, type Prefs } from "@/lib/prefs";
import { PrimaryButton } from "./chrome";

/** NarrowV3, approved copy verbatim from the policy strings: the shape of
 * the problem, three one-click wideners, and the plain statement that too
 * few matches in the survey is not too few people in the country. No "0
 * cities", no "0 people", no count of anything (item 8). */
export function NarrowState({
  prefs,
  meta,
  onWiden,
}: {
  prefs: Prefs;
  meta: Meta;
  onWiden: (next: Prefs) => void;
}) {
  const policy = meta.policy_strings;
  const body = policy.narrow_body.replace("{search}", describeSearch(prefs));
  const opts = wideners(prefs);
  return (
    <div
      className="flex flex-col items-center gap-8 px-6 py-14 text-center"
      data-testid="narrow-state"
    >
      <svg width="72" height="72" viewBox="0 0 72 72" aria-hidden="true">
        <circle cx="36" cy="36" r="34" fill="var(--tint)" />
        <circle cx="32" cy="32" r="13" fill="none" stroke="var(--accent)" strokeWidth="3" />
        <path d="M42 42L54 54" fill="none" stroke="var(--accent)" strokeWidth="3" strokeLinecap="round" />
      </svg>
      <div className="flex flex-col items-center gap-3.5">
        <h2 className="max-w-[26ch] text-balance font-display text-[34px] font-semibold leading-tight">
          {policy.narrow_title}
        </h2>
        <p className="max-w-[66ch] text-[16.5px] leading-relaxed text-ink-2">
          {body}
        </p>
      </div>
      {/* Phase 2g item 2.3: the note box below the wideners is GONE —
          the body's second sentence now says what it said. Its "How it
          works" link went with it; the header nav still carries the
          route on this screen, recorded in PHASE2G.md. */}
      <div className="flex flex-wrap justify-center gap-4">
        {opts.map((w, i) =>
          i === 0 ? (
            <button
              key={w.label}
              type="button"
              onClick={() => onWiden(w.next)}
              className="flex min-h-[54px] flex-col items-start gap-[3px] rounded-[10px] bg-accent px-[22px] py-3 text-left hover:bg-accent-hover"
            >
              <span className="text-[15px] font-bold text-white">{w.label}</span>
              <span className="text-[12.5px] text-tint">{w.sub}</span>
            </button>
          ) : (
            <button
              key={w.label}
              type="button"
              onClick={() => onWiden(w.next)}
              className="flex min-h-[54px] flex-col items-start gap-[3px] rounded-[10px] border-[1.5px] border-ink bg-surface px-[22px] py-3 text-left hover:bg-tint"
            >
              <span className="text-[15px] font-bold text-ink">{w.label}</span>
              <span className="text-[12.5px] text-ink-3">{w.sub}</span>
            </button>
          ),
        )}
      </div>
    </div>
  );
}

export { PrimaryButton };
