import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // the e2e stack builds into its own dir so a CI-style run never clobbers
  // a live dev server's .next (learned the hard way)
  distDir: process.env.NEXT_DIST_DIR || ".next",
  // content/methodology.md is synced verbatim from docs/methodology.md by
  // scripts/sync_content.mjs (predev/prebuild); trace it into server output.
  outputFileTracingIncludes: {
    "/methodology": ["./content/methodology.md"],
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
    ];
  },
};

export default nextConfig;
