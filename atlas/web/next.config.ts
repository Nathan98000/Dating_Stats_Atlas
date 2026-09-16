import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // content/methodology.md is synced verbatim from docs/methodology.md by
  // scripts/sync_content.mjs (predev/prebuild); trace it into server output.
  outputFileTracingIncludes: {
    "/methodology": ["./content/methodology.md"],
  },
};

export default nextConfig;
