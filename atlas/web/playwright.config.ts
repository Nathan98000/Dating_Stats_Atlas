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
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
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
      url: "http://127.0.0.1:3100/how-it-works",
      env: {
        ATLAS_API_URL: "http://127.0.0.1:8600",
        NEXT_DIST_DIR: ".next-e2e",
      },
      reuseExistingServer: !process.env.CI,
      timeout: 300_000,
    },
  ],
});
