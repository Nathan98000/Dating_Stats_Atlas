import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // the e2e stack builds into its own dir so a CI-style run never clobbers
  // a live dev server's .next (learned the hard way)
  distDir: process.env.NEXT_DIST_DIR || ".next",
  // content/*.md is synced verbatim from docs/ by scripts/sync_content.mjs
  // (predev/prebuild); trace the pages' files into server output.
  outputFileTracingIncludes: {
    "/about": ["./content/methodology.md"],
    "/privacy": ["./content/privacy.md"],
    "/about-crime-data": ["./content/crime.md"],
  },
  // m4.0.0 (ADR 0018): no page, route or file of the site sends a
  // referrer onward
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [{ key: "Referrer-Policy", value: "no-referrer" }],
      },
    ];
  },
  // Phase 2g item 1.3: the rent feature was renamed while no public URL
  // exists; the old path keeps working for anything that saved it
  async redirects() {
    return [
      {
        source: "/stats/median_gross_rent",
        destination: "/stats/rent_1br",
        permanent: true,
      },
      // m4.0.0 (Nathan's decision 7): "How it works" became About us
      {
        source: "/how-it-works",
        destination: "/about",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
