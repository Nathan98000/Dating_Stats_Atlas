/** The header's destinations — shared by the server-rendered fallback
 * and the client links that carry the visitor's query (Phase 2f item 2).
 * Plain data module: importable from both sides of the boundary. m4.0.0
 * (Nathan's decision 7): Browse cities, Compare cities, About us — What
 * we measure keeps its page, linked from About us. Phase 4e (Nathan):
 * "Browse cities" reads "Home" — Home, Compare cities, About us. Renamed by
 * Nathan on 2026-10-07: the About page is "About the site", here and in
 * its heading (the registry's about_title). */
export const NAV_DESTINATIONS = [
  { href: "/", label: "Home" },
  { href: "/compare", label: "Compare cities" },
  { href: "/about", label: "About the site" },
] as const;
