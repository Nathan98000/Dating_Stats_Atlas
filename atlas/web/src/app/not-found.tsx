import Link from "next/link";
import { SiteFooter, SiteHeader } from "@/components/chrome";
import { CHROME } from "@/lib/chrome";

/** Phase 5: the 404 has the site's header, footer and main landmark, so
 * the skip link has a target here too. */
export default function NotFound() {
  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto flex max-w-3xl flex-col gap-4 px-4 pb-24 pt-16 sm:px-12">
        <h1 className="font-display text-display-1">{CHROME.not_found_title}</h1>
        <p className="text-body-lg text-ink-2">{CHROME.not_found_body}</p>
        <Link href="/" className="inline-flex min-h-11 items-center self-start text-body font-semibold text-accent hover:text-accent-hover">
          {CHROME.nav_rankings} →
        </Link>
      </main>
      <SiteFooter />
    </>
  );
}
