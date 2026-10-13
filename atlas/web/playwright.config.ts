import { defineConfig, devices } from "@playwright/test";
import path from "path";

/** E2E runs hermetically against the PINNED FIXTURE build (the same one the
 * golden tests use): its own FastAPI on 8600 and a production Next build on
 * 3100, so it never collides with a dev stack and CI needs no data
 * artifact. */
const repoRoot = path.resolve(__dirname, "..", "..");
const fixture = path.resolve(
  repoRoot,
  "atlas/model/tests/golden/fixture_build",
);
/** The specs run at three widths (the tag-filtered projects below). */
const WIDTHS = /phase[56]\.spec\.ts/;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["github"]] : [["list"]],
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] }, testIgnore: WIDTHS },
    // Phases 5 and 6: the redesign's three widths — the desk, a laptop
    // below the 1120px breakpoint, and a touch phone. Every test in those
    // files runs at the desk unless tagged @no-desk; it runs at the laptop
    // or the phone only when tagged @laptop or @phone, i.e. only where the
    // layout it checks differs (a width-independent check runs once).
    { name: "desk-1440", testMatch: WIDTHS, grepInvert: /@no-desk/,
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
    { name: "laptop-1024", testMatch: WIDTHS, grep: /@laptop/,
      use: { ...devices["Desktop Chrome"], viewport: { width: 1024, height: 768 } } },
    { name: "phone-390", testMatch: WIDTHS, grep: /@phone/,
      use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 },
             isMobile: true, hasTouch: true } },
  ],
  webServer: [
    {
      command:
        ".venv/bin/python -m uvicorn atlas.api.app:app --host 127.0.0.1 --port 8600 --log-level warning",
      cwd: repoRoot,
      url: "http://127.0.0.1:8600/v1/health",
      env: { BUILD_DIR: fixture },
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: "npm run build && npx next start -p 3100",
      url: "http://127.0.0.1:3100/about",
      env: {
        ATLAS_API_URL: "http://127.0.0.1:8600",
        NEXT_DIST_DIR: ".next-e2e",
      },
      reuseExistingServer: !process.env.CI,
      timeout: 300_000,
    },
  ],
});
