import statPages from "@/data/stat-pages.json";
import { fill } from "./results";

/** Phase 5: the registry's labels for every page's header and footer and
 * the page-title templates, from the committed stat-pages.json (written by
 * scripts/build_stat_pages.py from the build's manifest) — so the header,
 * the footer and a title render with no API call, which the stat pages,
 * prerendered at build time, need. */
export const CHROME = (statPages as unknown as { chrome: Record<string, string> }).chrome;

/** "{page} · Dating Stats Atlas"; the bare site name when there is no page. */
export function pageTitle(page?: string): string {
  return page ? fill(CHROME.title_template, { page }) : CHROME.title_site;
}

/** The site's description, for pages without one of their own. */
export const SITE_DESCRIPTION =
  "Which city has the best dating scene for you? Estimated from the Census Bureau's own survey, city by city.";

/** The site's public address, for absolute Open Graph URLs. */
export const SITE_URL = process.env.SITE_URL ?? "https://dating-stats-atlas.duckdns.org";

/** A page's <title>, description and Open Graph tags (og:title,
 * og:description, og:url, and og:image where the page has a
 * photograph). */
export function pageMetadata(title: string, description: string, url: string, image?: string) {
  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url,
      siteName: CHROME.title_site,
      type: "website" as const,
      ...(image ? { images: [{ url: image }] } : {}),
    },
  };
}
