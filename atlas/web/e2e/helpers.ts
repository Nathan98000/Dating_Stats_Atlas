import type { BrowserContext, Page } from "@playwright/test";

/** m4.0.0 (ADR 0018): the visitor's own sex, education and race live in
 * the browser (localStorage, lib/about-you), never in a URL — a test that
 * needs a visitor with details seeds the storage before the first page
 * runs, as a returning visitor's browser would hold them. Seeded once:
 * details the test changes afterwards persist across its navigations. */
export async function seedAboutYou(
  target: Page | BrowserContext,
  about: { sex?: "male" | "female"; edu?: string; raceOn?: boolean; race?: string },
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
