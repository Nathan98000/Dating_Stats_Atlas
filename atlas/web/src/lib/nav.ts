/** The header's destinations and the footer's links — shared by the
 * server-rendered header and footer and the client links that carry the
 * visitor's query (Phase 2f item 2). Plain data module: importable from
 * both sides of the boundary. Phase 5 (Nathan's decision 2): Rankings,
 * Compare, How it works — the labels are the registry's (nav_*, footer_*),
 * named here by key. */
export const NAV_DESTINATIONS = [
  { href: "/", key: "nav_rankings" },
  { href: "/compare", key: "nav_compare" },
  { href: "/about", key: "nav_how" },
] as const;

/** Phase 5: the footer on every page (also in the phone menu). Data
 * sources is About's Sources and credits section. */
export const FOOTER_LINKS = [
  { href: "/about", key: "footer_how" },
  { href: "/what-we-measure", key: "footer_measure" },
  { href: "/privacy", key: "footer_privacy" },
  { href: "/terms", key: "footer_terms" },
  { href: "/about#sources-and-credits", key: "footer_sources" },
] as const;

/** Whether a nav destination is the page being shown: Rankings for the
 * home page (and its permalink pages), the others for their own section. */
export function isCurrent(href: string, pathname: string): boolean {
  if (href === "/") return pathname === "/" || pathname.startsWith("/r/");
  return pathname === href || pathname.startsWith(`${href}/`);
}
