// Phase 7 (R12): every page, and the home page's states, at 1440 and 390,
// through csp_proxy.mjs (the Caddyfile's security headers on a local
// production build): any Content-Security-Policy violation (the browser's
// securitypolicyviolation event) and every console error. The pages and
// states are the round-4 review's (its measure/common.mjs and states.mjs,
// which need its node_modules link: see its README).
//
//   node scripts/review/csp_proxy.mjs &      (:3402 -> :3400)
//   cd atlas/results/phase7/after && BASE=http://127.0.0.1:3402 node ../../../web/scripts/review/csp_check.mjs
import { writeFileSync } from "fs";
import { PAGES, VIEWPORTS, launch, settle } from "../../../docs/design/review-2026-10-12/measure/common.mjs";
import { HOME_STATES } from "../../../docs/design/review-2026-10-12/measure/states.mjs";

const BASE = process.env.BASE || "http://127.0.0.1:3402";
const WIDTHS = [1440, 390];

const browser = await launch();
const runs = [];

async function visit(width, label, path, act) {
  const ctx = await browser.newContext(VIEWPORTS[width]);
  await ctx.addInitScript(() => {
    window.__csp = [];
    document.addEventListener("securitypolicyviolation", (e) => {
      window.__csp.push({ directive: e.violatedDirective, blocked: e.blockedURI, source: e.sourceFile, line: e.lineNumber });
    });
  });
  const page = await ctx.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", (e) => errors.push(String(e)));
  const res = await page.goto(BASE + path);
  const csp = res?.headers()["content-security-policy"] ?? null;
  await settle(page, 300);
  if (act) await act(page);
  await page.waitForTimeout(300);
  const violations = await page.evaluate(() => window.__csp);
  runs.push({ width, page: label, path, status: res?.status(), csp_header: Boolean(csp), violations, console_errors: errors });
  await ctx.close();
}

for (const width of WIDTHS) {
  for (const [label, path] of Object.entries(PAGES)) await visit(width, label, path);
  for (const [state, go] of Object.entries(HOME_STATES)) {
    await visit(width, `home:${state}`, "/", (page) => go(page).catch((e) => { runs.push({ width, page: `home:${state}`, step_error: String(e) }); }));
  }
}
await browser.close();

const withViolations = runs.filter((r) => r.violations?.length);
const withErrors = runs.filter((r) => r.console_errors?.length);
const out = {
  base: BASE, widths: WIDTHS, runs: runs.length,
  csp_header_on_every_page: runs.filter((r) => r.csp_header !== undefined).every((r) => r.csp_header),
  violations: withViolations.reduce((n, r) => n + r.violations.length, 0),
  runs_with_console_errors: withErrors.length,
  step_errors: runs.filter((r) => r.step_error).map((r) => `${r.width} ${r.page}: ${r.step_error}`),
  detail: runs,
};
writeFileSync("csp_check.json", JSON.stringify(out, null, 1) + "\n");
console.log(`${out.runs} runs; CSP header on every page: ${out.csp_header_on_every_page}; violations: ${out.violations}; runs with console errors: ${out.runs_with_console_errors}`);
for (const r of withViolations) console.log("VIOLATION", r.width, r.page, JSON.stringify(r.violations));
for (const r of withErrors) console.log("ERROR", r.width, r.page, r.console_errors.join(" | ").slice(0, 300));
