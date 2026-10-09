import Link from "next/link";
import { Suspense } from "react";
import { SearchBox } from "./search";
import { BrandLink, HeaderSearchToggle, MenuButton, NavLinks } from "./nav-links";
import { FOOTER_LINKS } from "@/lib/nav";
import { CHROME } from "@/lib/chrome";

/** Phase 5's header: brand, nav and find-a-city, one row 64px tall (56px
 * on phones). From 1120px the nav and a 240px search field; 640-1119px
 * the nav and a search icon; below 640px a search icon and a menu button,
 * whose panel holds the nav and the footer's links. Labels come from the
 * registry (lib/chrome: no API call, so prerendered pages have them); the links carry the visitor's preference query string when
 * the page has one (Phase 2f item 2; the Suspense fallbacks render the
 * same links bare, so nothing shifts). */
export function SiteHeader() {
  const labels = CHROME;
  return (
    <header className="relative h-16 border-b border-rule bg-paper max-sm:h-14">
      <div className="mx-auto flex h-full max-w-[1200px] items-center gap-10 px-4 sm:px-12 max-sm:gap-3">
        <Suspense
          fallback={
            <Link href="/" className="inline-flex min-h-11 items-center font-display text-h3 font-semibold tracking-tight text-ink max-sm:text-h3">
              Dating Stats Atlas
            </Link>
          }
        >
          <BrandLink />
        </Suspense>
        <nav aria-label="Main" className="ml-auto flex h-full gap-7 max-sm:hidden">
          <Suspense fallback={null}>
            <NavLinks labels={labels} />
          </Suspense>
        </nav>
        <div className="hidden desk:block">
          <Suspense fallback={<div className="h-10 w-[240px]" />}>
            <SearchBox clearLabel={labels.clear} />
          </Suspense>
        </div>
        <div className="flex items-center gap-1 max-sm:ml-auto desk:hidden">
          <Suspense fallback={<div className="h-11 w-11" />}>
            <HeaderSearchToggle label="Find a city" closeLabel={labels.close} />
          </Suspense>
          <div className="sm:hidden">
            <Suspense fallback={<div className="h-11 w-11" />}>
              <MenuButton labels={labels} menuLabel="Menu" closeLabel={labels.close} />
            </Suspense>
          </div>
        </div>
      </div>
    </header>
  );
}

/** Phase 5: the footer on every page — the brand and five links (How it
 * works, What we measure, Privacy, Terms, Data sources). */
export function SiteFooter() {
  const labels = CHROME;
  return (
    <footer className="border-t border-rule max-desk:pb-24">
      <div className="mx-auto flex max-w-[1200px] flex-wrap items-center gap-x-6 gap-y-1 px-4 py-7 text-body-sm text-ink-3 sm:px-12">
        <span className="mr-auto font-display text-body font-semibold text-ink">Dating Stats Atlas</span>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-6">
          {FOOTER_LINKS.map((f) => (
            <Link key={f.key} href={f.href} className="inline-flex min-h-11 min-w-11 items-center justify-center hover:text-ink">
              {labels[f.key]}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  );
}
