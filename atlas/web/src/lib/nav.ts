/** The header's destinations — shared by the server-rendered fallback
 * and the client links that carry the visitor's query (Phase 2f item 2).
 * Plain data module: importable from both sides of the boundary. m4.0.0
 * (Nathan's decision 7): Browse cities, Compare cities, About us — What
 * we measure keeps its page, linked from About us. */
export const NAV_DESTINATIONS = [
  { href: "/", label: "Browse cities" },
  { href: "/compare", label: "Compare cities" },
  { href: "/about", label: "About us" },
] as const;
