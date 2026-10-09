import AxeBuilder from "@axe-core/playwright";
import { expect, test, type APIRequestContext } from "@playwright/test";
import { E2E_API, fetchMeta } from "./helpers";
import type { PoliticalLeanResponse, ProfileResponse } from "../src/lib/types";

/** Every metro has a profile (POST /v1/profile): its stat cards and
 * crime block, which no search changes. A metro below the ranked set's
 * population floor — no search returns it; the pinned fixture's is Eagle
 * Pass — keeps the floor sentence and now shows the profile it promises:
 * the seven stat cards with their bands, political lean beside who lives
 * here, and crime. Compare shows its figures too, where it said "Not
 * enough reliable data available." Every figure is the API's. */

const QS = "?sex=male&self_age=30&age=28-40&marital=never,previously";
const BELOW = "eagle-pass-texas";

async function profileOf(request: APIRequestContext, slug: string): Promise<ProfileResponse> {
  const cbsa = (await fetchMeta(request)).metros.find((m) => m.slug === slug)!.cbsa;
  const r = await request.post(`${E2E_API}/v1/profile`, { data: { cbsa } });
  expect(r.ok()).toBe(true);
  return (await r.json()) as ProfileResponse;
}

test("a city below the ranking floor shows its whole profile under the floor sentence", async ({ page, request }) => {
  const meta = await fetchMeta(request);
  const metro = meta.metros.find((m) => m.slug === BELOW)!;
  expect(metro.ranked_set).toBe(false);
  const profile = await profileOf(request, BELOW);
  const lean = ((await (await request.get(`${E2E_API}/v1/political_lean`)).json()) as PoliticalLeanResponse)
    .metros[metro.cbsa];
  if (!lean.available || !profile.crime.available) throw new Error("fixture metro without a figure");
  await page.goto(`/city/${BELOW}${QS}`);
  // Phase 6 (F24): the registry's sentence, the floor stated
  await expect(page.getByTestId("below-floor")).toHaveText(
    meta.policy_strings.city_below_floor.replace("{city}", metro.display_name_full.split(",")[0]));
  await expect(page.getByTestId("ranked-card")).toHaveCount(0);
  await expect(page.getByTestId("city-narrow-card")).toHaveCount(0);
  // the registry's seven cards, then political lean, then crime
  const order = await page.locator("[data-card]").evaluateAll((els) => els.map((e) => e.getAttribute("data-card")));
  expect(order).toEqual([...meta.city_cards, "political_lean", "violent_crime_rate", "property_crime_rate"]);
  for (const c of profile.cards) {
    const card = page.locator(`[data-card="${c.id}"]`);
    await expect(card).toContainText(c.display!);
    await expect(card).toContainText(c.unit_line!);
    await expect(card.getByTestId("band-label")).toHaveText(c.band!.label);
  }
  await expect(page.locator('[data-card="political_lean"]').getByTestId("lean-text")).toHaveText(lean.text);
  for (const s of profile.crime.stats!) {
    await expect(page.locator(`[data-card="${s.id}"]`)).toContainText(s.display);
  }
  await expect(page.getByText(meta.policy_strings.card_missing)).toHaveCount(0);
});

test("compare shows a city below the floor with its figures and the FBI's caution", async ({ page, request }) => {
  const meta = await fetchMeta(request);
  const profile = await profileOf(request, BELOW);
  await page.goto(`/compare/provo-utah/${BELOW}${QS}`);
  const table = page.getByTestId("compare-table");
  for (const c of profile.cards) {
    const row = table.locator("tr", {
      has: page.getByRole("rowheader", { name: meta.features[c.id].display_name, exact: true }),
    });
    await expect(row.locator("td").nth(1)).toContainText(c.display!);
    await expect(row.locator("td").nth(1)).toContainText(c.band!.label);
  }
  await expect(table).not.toContainText(meta.policy_strings.card_missing);
  // crime: the city below the floor on the left now has its figures (it
  // said "Not covered"), under the caution its own profile carries
  await page.goto(`/compare/${BELOW}/provo-utah${QS}`);
  await expect(page.getByTestId("crime-compare-banner")).toContainText(profile.crime.compare_banner);
  const crime = page.getByTestId("compare-crime");
  for (const s of profile.crime.stats!) {
    await expect(crime.locator("tr", { has: page.getByText(s.label, { exact: true }) }).locator("td").first())
      .toHaveText(s.display);
  }
});

for (const p of [
  { name: "a city page below the ranking floor", url: `/city/${BELOW}${QS}` },
  { name: "compare with a city below the floor", url: `/compare/provo-utah/${BELOW}${QS}` },
]) {
  test(`axe: ${p.name}`, async ({ page }) => {
    await page.goto(p.url);
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const serious = results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? ""));
    expect(serious.map((v) => `${v.id}: ${v.nodes.length} nodes — ${v.help}`)).toEqual([]);
  });
}
