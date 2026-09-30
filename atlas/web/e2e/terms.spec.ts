import AxeBuilder from "@axe-core/playwright";
import { readFileSync } from "fs";
import path from "path";
import { expect, test } from "@playwright/test";
import { fetchMeta } from "./helpers";

/** The terms of use (before launch; a draft for Nathan's approval):
 * docs/terms.md rendered at /terms exactly as the privacy page renders
 * docs/privacy.md, linked from About us beside Privacy with the registry's
 * label. The page holds to what every page holds to: no request to another
 * origin, no serious or critical axe finding, nothing from the banned
 * vocabulary, no code or version id. */

const TERMS_MD = readFileSync(path.resolve(__dirname, "..", "..", "docs", "terms.md"), "utf-8");
const BANNED_PAGE_PATTERNS: [RegExp, string][] = [
  [/\b(odds|rivals?|markets?|supply|inventory|competitors?)\b/i, "banned vocabulary"],
  [/margin of error|±/u, "a margin"],
  [/\bCV\b/, "a CV"],
  [/\bCBSA\b|\bPUMA/i, "a geography code"],
  [/\bm\d+\.\d+\.\d+\b/, "a model version"],
  [/\b[0-9a-f]{12}\b/, "a build id"],
  [/permalink/i, "a permalink"],
];

test("the terms of use render docs/terms.md, every section of it", async ({ page }) => {
  await page.goto("/terms");
  const article = page.locator("article.prose-method");
  await expect(article.locator("h1")).toHaveText("Terms of use");
  const headings = [...TERMS_MD.matchAll(/^## (.+)$/gm)].map((m) => m[1].trim());
  expect(headings.length).toBeGreaterThanOrEqual(8);
  await expect(article.locator("h2")).toHaveText(headings);
  // its links lead to the privacy page and the credits on About us
  await article.getByRole("link", { name: "Privacy", exact: true }).click();
  await expect(page).toHaveURL(/\/privacy$/);
  await page.goBack();
  await article.getByRole("link", { name: "About us, Sources and credits" }).click();
  await expect(page).toHaveURL(/\/about#sources-and-credits$/);
  await expect(page.getByTestId("sources-and-credits")).toBeVisible();
});

test("About us links the terms of use beside Privacy, labelled from the registry", async ({ page, request }) => {
  const ps = (await fetchMeta(request)).policy_strings;
  expect(ps.about_terms_link).toBe("Terms of use");
  await page.goto("/about");
  const links = page.getByTestId("about-links");
  const terms = page.getByTestId("about-terms-link");
  await expect(terms).toHaveText(ps.about_terms_link);
  await expect(terms).toHaveAttribute("href", "/terms");
  // right after Privacy
  const labels = await links.getByRole("link").allTextContents();
  expect(labels.indexOf(ps.about_terms_link)).toBe(labels.indexOf(ps.about_privacy_link) + 1);
  await terms.click();
  await expect(page).toHaveURL(/\/terms$/);
});

test("the terms page makes no third-party request and renders no banned string", async ({ page, baseURL }) => {
  const own = new URL(baseURL ?? "http://127.0.0.1:3100").origin;
  const foreign: string[] = [];
  page.on("request", (req) => {
    const url = req.url();
    if (url.startsWith("data:") || url.startsWith("blob:")) return;
    if (new URL(url).origin !== own) foreign.push(url);
  });
  await page.goto("/terms");
  await page.waitForLoadState("networkidle");
  expect(foreign).toEqual([]);
  const text = (await page.locator("body").innerText()) ?? "";
  for (const [re, what] of BANNED_PAGE_PATTERNS) {
    expect(text, `the terms page must not render ${what}`).not.toMatch(re);
  }
});

test("axe: terms of use", async ({ page }) => {
  await page.goto("/terms");
  await page.waitForLoadState("networkidle");
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const serious = results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? ""));
  expect(serious.map((v) => `${v.id}: ${v.nodes.length} nodes — ${v.help}`)).toEqual([]);
});
