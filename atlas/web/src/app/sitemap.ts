import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/chrome";
import cities from "@/data/search-index.json";
import statPages from "@/data/stat-pages.json";

/** Phase 7 (R07): every page a search engine should know, at its one
 * address — the home page, How it works, What we measure, About the crime
 * data, Privacy, Terms, the stat pages and every city page (387, ranked or
 * not) — absolute, from SITE_URL. No compare pairs, no permalinks, no
 * query strings: each of those is another address for a page listed here,
 * and every page names its own canonical address (lib/chrome pageMetadata). */
export default function sitemap(): MetadataRoute.Sitemap {
  const paths = [
    "/",
    "/about",
    "/what-we-measure",
    "/about-crime-data",
    "/privacy",
    "/terms",
    ...(statPages as { order: string[] }).order.map((fid) => `/stats/${fid}`),
    ...(cities as { s: string }[]).map((c) => `/city/${c.s}`),
  ];
  return paths.map((p) => ({ url: `${SITE_URL}${p}` }));
}
