/** The header's destinations — shared by the server-rendered fallback
 * and the client links that carry the visitor's query (Phase 2f item 2).
 * Plain data module: importable from both sides of the boundary. */
export const NAV_DESTINATIONS = [
  { href: "/", label: "Browse cities" },
  { href: "/compare", label: "Compare cities" },
  { href: "/what-we-measure", label: "What we measure" },
  { href: "/how-it-works", label: "How it works" },
] as const;
