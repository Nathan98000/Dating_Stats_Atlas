// Home-page states shared by the axe and size audits.
import { BASE, settle } from "./common.mjs";

export const HOME_STATES = {
  default: async (page) => {},
  "row-open": async (page) => {
    const t = page.locator('li[data-rank="4"] [data-testid=row-toggle]').locator("visible=true").first();
    await t.click(); await page.waitForTimeout(300);
  },
  "row-open-info": async (page) => {
    const t = page.locator('li[data-rank="4"] [data-testid=row-toggle]').locator("visible=true").first();
    await t.click(); await page.waitForTimeout(300);
    await page.locator('li[data-rank="4"] [id^=detail-] button[aria-label]').first().click();
    await page.waitForTimeout(300);
  },
  // Phase 6 (F06): a featured card's detail open (the panel from 768px,
  // inside the card below)
  "card-open": async (page) => {
    await page.locator("[data-testid=card-toggle]").first().click(); await page.waitForTimeout(300);
  },
  "age-popover": async (page) => {
    await page.locator("[data-testid=age-token]").click(); await page.waitForTimeout(300);
  },
  "rail-open": async (page) => {
    const w = page.viewportSize().width;
    if (w < 1120) {
      await page.evaluate(() => window.scrollTo(0, 1500)); await page.waitForTimeout(500);
      await page.getByRole("button", { name: "Adjust your search" }).click(); await page.waitForTimeout(500);
    }
    for (const g of ["Narrow it down", "Sharpen compatibility"]) {
      const b = page.locator(w < 1120 ? "dialog[open]" : "[data-testid=search-panel]").getByRole("button", { name: g });
      if ((await b.getAttribute("aria-expanded")) === "false") await b.click();
      await page.waitForTimeout(200);
    }
  },
  "slider-info": async (page) => {
    const w = page.viewportSize().width;
    if (w < 1120) {
      await page.evaluate(() => window.scrollTo(0, 1500)); await page.waitForTimeout(500);
      await page.getByRole("button", { name: "Adjust your search" }).click(); await page.waitForTimeout(500);
    }
    await page.locator((w < 1120 ? "dialog[open] " : "[data-testid=search-panel] ") + "[data-testid=slider-info]").first().click();
    await page.waitForTimeout(300);
  },
  "find-typed": async (page) => {
    await page.locator("input[data-testid=find-in-results]").fill("San");
    await page.waitForTimeout(400);
  },
  "header-search": async (page) => {
    const w = page.viewportSize().width;
    if (w < 1120) { await page.locator("[data-testid=header-search-button]").click(); await page.waitForTimeout(300); }
    await page.locator("header input[type=search]").locator("visible=true").first().fill("Abil"); await page.waitForTimeout(400);
  },
  "menu-open": async (page) => {
    const b = page.locator("[data-testid=menu-button]");
    if (await b.isVisible()) { await b.click(); await page.waitForTimeout(300); }
  },
  narrowed: async (page) => {
    await page.goto(BASE + "/?self_age=30&sex=male&age=28-40&marital=never%2Cpreviously&edu=graduate&inc=250000");
    await settle(page, 600);
  },
  empty: async (page) => {
    await page.goto(BASE + "/?self_age=22&sex=male&age=18-19&marital=previously&edu=graduate&inc=250000&race=nhpi_nh");
    await settle(page, 600);
  },
  "same-sex": async (page) => {
    await page.goto(BASE + "/?self_age=33&sex=male&age=28-38&marital=never%2Cpreviously");
    await settle(page, 300);
    await page.locator("[data-testid=self-sex]").selectOption("male"); await page.waitForTimeout(300);
    await page.locator("[data-testid=seek-sex]").selectOption("male"); await page.waitForTimeout(1500);
  },
};
