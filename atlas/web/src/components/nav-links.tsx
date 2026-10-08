"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { FOOTER_LINKS, isCurrent, NAV_DESTINATIONS } from "@/lib/nav";
import { prefQueryString } from "@/lib/prefs";
import { SearchBox } from "./search";

/** Phase 2f item 2: the nav carries the current preference query string
 * when the page has one, so the common path from results to What we
 * measure and back never needs the cookie at all. Only the preference
 * dialect's own params ride along — page-local params (a stat page's
 * sort, the compare landing's a/b) stay where they belong. */
function useCarried(): string {
  const sp = useSearchParams();
  const qs = prefQueryString(new URLSearchParams(sp.toString()));
  return qs ? `?${qs}` : "";
}

/** Phase 5: the header's nav — the current page underlined in the accent,
 * in --ink 600, with aria-current="page". From 640px. */
export function NavLinks({ labels }: { labels: Record<string, string> }) {
  const suffix = useCarried();
  const pathname = usePathname();
  return (
    <>
      {NAV_DESTINATIONS.map((d) => {
        const on = isCurrent(d.href, pathname);
        return (
          <Link
            key={d.href}
            href={`${d.href}${suffix}`}
            aria-current={on ? "page" : undefined}
            className={`flex h-full items-center border-b-2 pt-0.5 text-body ${on
              ? "border-accent font-semibold text-ink"
              : "border-transparent font-medium text-ink-2 hover:text-ink"}`}
          >
            {labels[d.key]}
          </Link>
        );
      })}
    </>
  );
}

/** The brand link, carrying the same preference params home. */
export function BrandLink() {
  const suffix = useCarried();
  return (
    <Link
      href={`/${suffix}`}
      className="font-display text-h3 font-semibold tracking-tight text-ink max-sm:text-h3"
    >
      Dating Stats Atlas
    </Link>
  );
}

/** Phase 5: the header's search below 1120px — a 44px icon button that
 * opens the find-a-city field across the header (Escape or its close
 * button puts it away). */
export function HeaderSearchToggle({ label, closeLabel }: { label: string; closeLabel: string }) {
  const [open, setOpen] = useState(false);
  const btn = useRef<HTMLButtonElement>(null);
  return (
    <>
      <button
        ref={btn}
        type="button"
        aria-label={label}
        aria-expanded={open}
        onClick={() => setOpen(true)}
        className="flex h-11 w-11 items-center justify-center rounded-full text-ink-2 hover:text-ink"
        data-testid="header-search-button"
      >
        <SearchIcon />
      </button>
      {open && (
        <div
          className="absolute inset-0 z-40 flex items-center gap-2 bg-paper px-4 sm:px-12"
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setOpen(false);
              btn.current?.focus();
            }
          }}
        >
          <SearchBox wide autoFocus />
          <button
            type="button"
            aria-label={closeLabel}
            onClick={() => { setOpen(false); btn.current?.focus(); }}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-ink-2 hover:text-ink"
          >
            <CloseIcon />
          </button>
        </div>
      )}
    </>
  );
}

/** Phase 5: the phone menu — a 44px button opening a panel with the nav
 * and the footer's links. Escape or a link closes it. */
export function MenuButton({ labels, menuLabel, closeLabel }: {
  labels: Record<string, string>; menuLabel: string; closeLabel: string;
}) {
  const [open, setOpen] = useState(false);
  const btn = useRef<HTMLButtonElement>(null);
  const suffix = useCarried();
  const pathname = usePathname();
  useEffect(() => { setOpen(false); }, [pathname]);
  return (
    <>
      <button
        ref={btn}
        type="button"
        aria-label={open ? closeLabel : menuLabel}
        aria-expanded={open}
        aria-controls="site-menu"
        onClick={() => setOpen(!open)}
        className="flex h-11 w-11 items-center justify-center rounded-full text-ink-2 hover:text-ink"
        data-testid="menu-button"
      >
        {open ? <CloseIcon /> : <MenuIcon />}
      </button>
      <nav
        id="site-menu"
        aria-label={menuLabel}
        hidden={!open}
        className="absolute inset-x-0 top-full z-40 border-b border-rule bg-paper px-4 pb-4 shadow-overlay"
        onKeyDown={(e) => {
          if (e.key === "Escape") { setOpen(false); btn.current?.focus(); }
        }}
      >
        <ul className="flex flex-col">
          {NAV_DESTINATIONS.map((d) => {
            const on = isCurrent(d.href, pathname);
            return (
              <li key={d.href}>
                <Link href={`${d.href}${suffix}`} aria-current={on ? "page" : undefined}
                  className={`flex min-h-11 items-center text-body ${on ? "font-semibold text-ink" : "text-ink-2"}`}>
                  {labels[d.key]}
                </Link>
              </li>
            );
          })}
        </ul>
        <ul className="mt-2 flex flex-col border-t border-rule pt-2">
          {FOOTER_LINKS.filter((f) => f.key !== "footer_how").map((f) => (
            <li key={f.key}>
              <Link href={f.href} className="flex min-h-11 items-center text-body-sm text-ink-2">
                {labels[f.key]}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </>
  );
}

function SearchIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" aria-hidden="true" fill="none"
      stroke="currentColor" strokeWidth="1.8">
      <circle cx="8.5" cy="8.5" r="5.5" /><path d="M13 13l4 4" strokeLinecap="round" />
    </svg>
  );
}
function MenuIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" aria-hidden="true" fill="none"
      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <path d="M3 6h14M3 10h14M3 14h14" />
    </svg>
  );
}
function CloseIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 18 18" aria-hidden="true" fill="none"
      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <path d="M4 4l10 10M14 4L4 14" />
    </svg>
  );
}
