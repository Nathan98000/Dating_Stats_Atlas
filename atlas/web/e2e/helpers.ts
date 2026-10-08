import { existsSync } from "fs";
import path from "path";
import type { APIRequestContext, BrowserContext, Page } from "@playwright/test";
import type { Meta } from "../src/lib/types";

/** The photographs are gitignored and re-fetchable, so a fresh checkout —
 * CI's — has none, and a page shows a photograph, and About us credits it,
 * only while its file is on disk ("no file, no photo"). A test that checks
 * a photograph reads the same disk the server reads (public/, relative to
 * the web app) and checks whichever case it finds. */
export function photoOnDisk(rel: string): boolean {
  return existsSync(path.resolve(__dirname, "..", "public", rel));
}

/** m4.0.0 (ADR 0018): the visitor's own sex, education and race live in
 * the browser (localStorage, lib/about-you), never in a URL — a test that
 * needs a visitor with details seeds the storage before the first page
 * runs, as a returning visitor's browser would hold them. Seeded once:
 * details the test changes afterwards persist across its navigations.
 * Since Phase 4b a stored race means race is on; `raceOn` is m4.0.0's
 * shape, seeded only to test its migration. */
export async function seedAboutYou(
  target: Page | BrowserContext,
  about: { sex?: "male" | "female"; edu?: string; race?: string; raceOn?: boolean },
): Promise<void> {
  await target.addInitScript((a) => {
    try {
      if (!window.localStorage.getItem("dsa_about_you")) {
        window.localStorage.setItem("dsa_about_you", JSON.stringify(a));
      }
    } catch {
      /* storage blocked */
    }
  }, about);
}

/** The e2e API (playwright.config.ts: the pinned fixture build on 8600) —
 * for reading the registry's strings a page is held to, never a page's
 * own request. */
export const E2E_API = "http://127.0.0.1:8600";

export async function fetchMeta(request: APIRequestContext): Promise<Meta> {
  const r = await request.get(`${E2E_API}/v1/meta`);
  if (!r.ok()) throw new Error(`/v1/meta ${r.status()}`);
  return (await r.json()) as Meta;
}

/** Phase 5: the rail's "Narrow it down" and "Sharpen compatibility" groups
 * start collapsed; a test that uses their controls opens the group first
 * (idempotent: an open group stays open). */
export async function openRailGroup(
  page: Page,
  name: "Narrow it down" | "Sharpen compatibility",
): Promise<void> {
  // below 1120px the rail lives in the sheet: open it from the bar
  if (!(await page.getByTestId("rail").count()) && !(await page.locator("dialog[open]").count())) {
    await page.mouse.wheel(0, 1600);
    await page.getByTestId("bottom-bar").getByRole("button", { name: "Adjust your search" }).click();
    await page.locator("dialog[open]").waitFor();
  }
  const btn = page.getByRole("button", { name, exact: true });
  if ((await btn.getAttribute("aria-expanded")) !== "true") await btn.click();
}

/** Phase 5: a row's balance, compatibility figure and contributions sit in
 * its detail, opened by its chevron (rows from the fourth; the top three
 * are cards). Returns the row. */
export async function expandRow(page: Page, rank: number) {
  const row = page.locator(`li[data-rank="${rank}"]`);
  const toggle = row.getByTestId("row-toggle").locator("visible=true");
  if ((await toggle.getAttribute("aria-expanded")) !== "true") await toggle.click();
  await row.getByTestId("row-detail").waitFor();
  return row;
}

/** Phase 5: every ranked row on the page, each row's detail open — the
 * list shows ten at first and a row's compatibility figure and balance sit
 * in its detail. The top three are cards and carry neither. */
export async function revealRows(page: Page): Promise<void> {
  const all = page.getByTestId("show-all");
  if (await all.count()) await all.click();
  const toggles = page.getByTestId("ranked-list").getByTestId("row-toggle").locator("visible=true");
  const n = await toggles.count();
  for (let i = 0; i < n; i++) {
    const t = toggles.nth(i);
    if ((await t.getAttribute("aria-expanded")) !== "true") await t.click();
  }
}
