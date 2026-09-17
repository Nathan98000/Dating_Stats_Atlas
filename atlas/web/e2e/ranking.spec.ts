import { expect, test } from "@playwright/test";

/** Home/results behavior against the pinned fixture (v3 boards):
 * server-rendered results, the two-handle age control by keyboard alone,
 * sort reversal, the count-only-when-excluded rule, importance controls
 * moving the order, and a hydration-clean load. */

test("first results are server-rendered, with the hero slot", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  await page.goto("/");
  await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
  await expect(page.getByTestId("hero-placeholder")).toBeVisible();
  // scores are whole numbers out of 100 with a meter, not a decimal
  const score = await page.getByTestId("score").first().textContent();
  expect(score).toMatch(/^\d{1,3}$/);
  expect(errors.filter((e) => e.includes("hydrat"))).toEqual([]);
});

test("the two-handle age control works by keyboard only", async ({ page }) => {
  await page.goto("/");
  const younger = page.getByLabel("Youngest age");
  const older = page.getByLabel("Oldest age");
  await expect(younger).toHaveCount(1);
  await expect(older).toHaveCount(1);
  await younger.focus();
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("ArrowLeft");
  await expect(page.getByTestId("age-output")).toContainText("26 – 40");
  await expect(page).toHaveURL(/age=26-40/);
  await older.focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByTestId("age-output")).toContainText("26 – 41");
  // handles can meet but not cross
  for (let i = 0; i < 60; i++) await page.keyboard.press("ArrowDown");
  const out = (await page.getByTestId("age-output").textContent()) ?? "";
  expect(out).toContain("26 – 26");
});

test("sort reverses the order without changing membership or ranks", async ({ page }) => {
  await page.goto("/");
  const rows = page.getByTestId("ranked-list").locator("li");
  await expect(rows.first()).toBeVisible();
  const before = await rows.evaluateAll((els) =>
    els.map((e) => `${e.getAttribute("data-cbsa")}:${e.getAttribute("data-rank")}`),
  );
  await page.getByTestId("sort").selectOption("worst_first");
  await expect(page).toHaveURL(/sort=worst_first/);
  await expect
    .poll(async () =>
      (await rows.evaluateAll((els) => els.map((e) => e.getAttribute("data-cbsa"))))[0],
    )
    .toBe(before[before.length - 1].split(":")[0]);
  const after = await rows.evaluateAll((els) =>
    els.map((e) => `${e.getAttribute("data-cbsa")}:${e.getAttribute("data-rank")}`),
  );
  expect(after).toEqual([...before].reverse()); // same cities, same earned ranks
});

test("the city count appears only when something is excluded", async ({ page }) => {
  await page.goto("/");
  // the fixture's default profile ranks every city: heading carries no number
  await expect(page.getByTestId("list-heading")).toHaveText("Cities for you");
  await expect(page.getByTestId("excluded-note")).toHaveCount(0);
  // narrow it until cities drop out: count appears with the approved sentence
  await page.goto("/?self_sex=female&self_age=32&age=30-40&marital=never&edu=graduate&inc=100000");
  await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
  const heading = await page.getByTestId("list-heading").textContent();
  expect(heading).toMatch(/^\d+ cities for you$/);
  await expect(page.getByTestId("excluded-note")).toContainText(
    /don’t have enough people matching this search/,
  );
  await expect(page.getByTestId("excluded-note")).not.toContainText(/\b0\b/);
});

test("each importance control changes the order", async ({ page }) => {
  await page.goto("/");
  const rows = page.getByTestId("ranked-list").locator("li");
  await expect(rows.first()).toBeVisible();
  const order = () =>
    rows.evaluateAll((els) => els.map((e) => e.getAttribute("data-cbsa")));
  let prev = await order();
  for (const row of ["Cost of living", "Going out & getting around", "Weather & local life"]) {
    const group = page.getByRole("radiogroup", { name: `${row} importance` });
    await group.getByRole("radio", { name: "A lot" }).click();
    await expect.poll(async () => JSON.stringify(await order()), { timeout: 10_000 })
      .not.toBe(JSON.stringify(prev));
    prev = await order();
  }
});

test("the slider moves weight between pool size and balance", async ({ page }) => {
  await page.goto("/");
  const rows = page.getByTestId("ranked-list").locator("li");
  await expect(rows.first()).toBeVisible();
  const order = () =>
    rows.evaluateAll((els) => els.map((e) => e.getAttribute("data-cbsa")));
  const slider = page.locator("input.svo").first();
  await slider.focus();
  await page.keyboard.press("Home");
  await expect(page).toHaveURL(/[?&]s=0/);
  await page.waitForTimeout(400);
  const atSize = await order();
  await page.keyboard.press("End");
  await expect(page).toHaveURL(/[?&]s=1/);
  await expect
    .poll(async () => JSON.stringify(await order()), { timeout: 10_000 })
    .not.toBe(JSON.stringify(atSize));
});

test("unticking every race group means everyone, not the leftovers", async ({ page }) => {
  await page.goto("/");
  const rows = page.getByTestId("ranked-list").locator("li");
  await expect(rows.first()).toBeVisible();
  const baseline = await rows.evaluateAll((els) =>
    els.map((e) => e.getAttribute("data-cbsa")),
  );
  const panel = page.getByTestId("race-panel");
  await expect(panel).toContainText("are always counted");
  const boxes = panel.locator("input.check");
  const n = await boxes.count();
  // plain clicks: unticking the LAST box snaps every box back on (zero
  // ticked means all six, per the panel's own sentence), so a strict
  // uncheck() would rightly complain that the state re-flipped
  for (let i = 0; i < n; i++) await boxes.nth(i).click();
  await expect(boxes.first()).toBeChecked(); // all back on
  await expect
    .poll(() => page.url(), { timeout: 5_000 })
    .not.toMatch(/[?&]race=/);
  await page.waitForTimeout(400);
  const after = await rows.evaluateAll((els) =>
    els.map((e) => e.getAttribute("data-cbsa")),
  );
  expect(after).toEqual(baseline);
});
