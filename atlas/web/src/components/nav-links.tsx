"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { NAV_DESTINATIONS } from "@/lib/nav";
import { prefQueryString } from "@/lib/prefs";

/** Phase 2f item 2: the nav carries the current preference query string
 * when the page has one, so the common path from results to What we
 * measure and back never needs the cookie at all. Only the preference
 * dialect's own params ride along — page-local params (a stat page's
 * sort, the compare landing's a/b) stay where they belong. */
export function NavLinks() {
  const sp = useSearchParams();
  const qs = prefQueryString(new URLSearchParams(sp.toString()));
  const suffix = qs ? `?${qs}` : "";
  return (
    <>
      {NAV_DESTINATIONS.map((d) => (
        <Link
          key={d.href}
          href={`${d.href}${suffix}`}
          className="text-sm font-semibold text-ink-2 hover:text-ink"
        >
          {d.label}
        </Link>
      ))}
    </>
  );
}

/** The brand link, carrying the same preference params home. */
export function BrandLink() {
  const sp = useSearchParams();
  const qs = prefQueryString(new URLSearchParams(sp.toString()));
  return (
    <Link
      href={`/${qs ? `?${qs}` : ""}`}
      className="font-display text-[23px] font-semibold tracking-tight text-ink"
    >
      Dating Stats Atlas
    </Link>
  );
}
