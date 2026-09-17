"use client";

import { useState } from "react";

/** The accessible information affordance from Phase 2d item 2, shared
 * since Phase 2e (the slider note and the crime cards use it): a real
 * button, not a hover-only tooltip — it opens on hover AND focus AND
 * tap, closes on Escape, blur and pointer-exit, and is wired with
 * aria-expanded + aria-describedby so the note reaches keyboard and
 * touch users. Click/tap OPENS rather than toggling: a toggle fights
 * the hover-open on pointer devices (the click's own hover reopens, the
 * toggle re-closes); on touch, tapping anywhere else blurs. `children`
 * is the note's content — text, or text with a link. */
export function InfoTip({
  id,
  label,
  testid = "info-tip",
  children,
}: {
  id: string;
  label: string;
  testid?: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <span className="relative inline-flex">
      <button
        type="button"
        data-testid={testid}
        aria-label={label}
        aria-expanded={open}
        aria-describedby={open ? id : undefined}
        className="flex h-[22px] w-[22px] items-center justify-center rounded-full border-[1.5px] border-ink-3 text-[12px] font-bold leading-none text-ink-2 hover:border-accent hover:text-accent"
        onClick={() => setOpen(true)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
        }}
      >
        i
      </button>
      {open && (
        <span
          id={id}
          role="note"
          data-testid={`${testid}-note`}
          className="absolute left-1/2 top-[30px] z-40 w-[290px] -translate-x-1/2 rounded-lg border border-rule bg-surface px-3.5 py-3 text-left text-[12.5px] font-normal leading-relaxed text-ink-2"
        >
          {children}
        </span>
      )}
    </span>
  );
}
