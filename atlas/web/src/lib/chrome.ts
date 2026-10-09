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

/** The home page's link-preview image (Phase 6, F31): the headline on
 * paper, a committed 1200x630 PNG (scripts/og_home.mjs). */
export const HOME_OG_IMAGE = "/og/home.png";

/** A page's <title>, description and Open Graph tags (og:title,
 * og:description, og:url, and og:image where the page has one). Phase 6
 * (F31): every image is a 1200x630 link preview, shown large
 * (twitter:card summary_large_image); without one the card is the plain
 * summary. */
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
      ...(image ? { images: [{ url: image, width: 1200, height: 630 }] } : {}),
    },
    twitter: image
      ? { card: "summary_large_image" as const, title, description, images: [image] }
      : { card: "summary" as const, title, description },
  };
}

/** A results page's title (Phase 6, F31): the registry's title_results
 * around the page's own results heading ("Top cities for single men,
 * 28–40 · Dating Stats Atlas"), without the heading's invisible word
 * joiners. */
export function resultsTitle(policy: Record<string, string>, heading: string): string {
  return fill(policy.title_results, { heading: heading.replace(/\u2060/g, "") });
}
