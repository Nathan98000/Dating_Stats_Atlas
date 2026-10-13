import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/chrome";

/** Phase 7 (R07): crawlers may read every page but the same-origin API
 * proxy and the permalinks (/r/…, a results page under a second address;
 * ADR 0004 keeps them out of the interface), and are pointed at the
 * sitemap. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/api/", "/r/"] },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
