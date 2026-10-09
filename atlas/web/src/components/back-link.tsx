"use client";

import Link from "next/link";
import { cameFromResults } from "@/lib/place";

/** "← Back to your results" (Phase 6, F18): when this page was opened from
 * a results page's city link in this tab, it goes back in history — the
 * browser's own Back, so the list comes back where the visitor left it
 * (the home page restores the rows shown and the city, lib/place) — and
 * otherwise it is the plain link to the results for this search. */
export function BackToResults({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      onClick={(e) => {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
        if (cameFromResults()) {
          e.preventDefault();
          window.history.back();
        }
      }}
      className="inline-flex min-h-11 items-center self-start text-body-sm font-semibold text-accent hover:text-accent-hover"
      data-testid="back-to-results"
    >
      {children}
    </Link>
  );
}
