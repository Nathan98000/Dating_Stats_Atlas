import { defineConfig } from "@playwright/test";
import path from "path";
import base from "../../playwright.config";

/** Phase 7 (R12): the whole e2e suite once through csp_proxy.mjs, which
 * adds the Caddyfile's security headers (the Content-Security-Policy
 * among them) to the hermetic production build: the same servers as
 * playwright.config.ts, with the proxy on 3102 in front of 3100.
 *
 *   cd atlas/web && npx playwright test -c scripts/review/playwright.csp.config.ts */
const web = path.resolve(__dirname, "..", "..");
const servers = Array.isArray(base.webServer) ? base.webServer : [base.webServer!];

export default defineConfig({
  ...base,
  testDir: path.join(web, "e2e"),
  use: { ...base.use, baseURL: "http://127.0.0.1:3102" },
  webServer: [
    ...servers.map((s) => ({ ...s, cwd: s.cwd ?? web })),
    {
      command: "node scripts/review/csp_proxy.mjs",
      cwd: web,
      env: { PORT: "3102", TARGET: "3100" },
      url: "http://127.0.0.1:3102/about",
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
