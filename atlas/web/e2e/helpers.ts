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
