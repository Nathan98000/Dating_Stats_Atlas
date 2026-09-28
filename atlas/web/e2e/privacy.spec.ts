import { expect, test } from "@playwright/test";

/** ADR 0017 (Nathan's decision): race and sex inputs never feed ads,
 * listings, referrals, or any housing, credit or job use. The build holds
 * it by construction: no page makes ANY request to another origin — no
 * advertising, tracker, analytics or embedded third-party content. */

const PAGE_SHAPES = [
  { name: "home", url: "/" },
  {
    name: "results narrowed",
    url: "/?self_age=32&sex=male&age=30-40&marital=never&edu=graduate&inc=100000",
  },
  { name: "city page", url: "/city/provo-utah" },
  { name: "compare", url: "/compare/provo-utah/austin-texas" },
  { name: "compare landing", url: "/compare" },
  { name: "stat page", url: "/stats/rent_1br" },
  { name: "what we measure", url: "/what-we-measure" },
  { name: "how it works", url: "/how-it-works" },
  { name: "about crime data", url: "/about-crime-data" },
];

for (const p of PAGE_SHAPES) {
  test(`no third-party request: ${p.name}`, async ({ page, baseURL }) => {
    const own = new URL(baseURL ?? "http://127.0.0.1:3100").origin;
    const foreign: string[] = [];
    page.on("request", (req) => {
      const url = req.url();
      if (url.startsWith("data:") || url.startsWith("blob:")) return;
      if (new URL(url).origin !== own) foreign.push(url);
    });
    await page.goto(p.url);
    await page.waitForLoadState("networkidle");
    expect(foreign).toEqual([]);
  });
}
