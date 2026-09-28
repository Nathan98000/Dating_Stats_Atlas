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
  { name: "about us", url: "/about" },
  { name: "privacy", url: "/privacy" },
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

/** ADR 0018 (Nathan's decision 4): the visitor's own sex, education and
 * race never leave the browser. A whole session — the home page, setting
 * the details, a city page, the compare page, a shared link opened by
 * someone else — is watched: no request (address, body or header), no
 * cookie, no link on any page and no permalink carries one; every
 * response of the site says Referrer-Policy: no-referrer; the cookie lives
 * 30 days at most; and the recipient of a shared link sees their own
 * figures, not the sender's. */

const LEAK = /self_(sex|edu|race)|\bgraduate\b|black_nh/;

test("no request, cookie, link or permalink carries an about-you detail across a session", async ({ page, context, browser, baseURL }) => {
  const own = new URL(baseURL ?? "http://127.0.0.1:3100").origin;
  const requests: { url: string; body: string; headers: Record<string, string> }[] = [];
  const noPolicy: string[] = [];
  const permalinks: string[] = [];
  const watch = (p: typeof page) => {
    p.on("request", (req) => requests.push(
      { url: req.url(), body: req.postData() ?? "", headers: req.headers() }));
    p.on("response", async (res) => {
      const url = res.url();
      if (url.startsWith("data:") || new URL(url).origin !== own) return;
      if (res.headers()["referrer-policy"] !== "no-referrer") noPolicy.push(`${res.status()} ${url}`);
      if (url.endsWith("/api/rank") && res.ok()) {
        permalinks.push((await res.json()).permalink);
      }
    });
  };
  watch(page);
  const links = new Set<string>();
  const collectLinks = async (p: typeof page) => {
    for (const h of await p.locator("a[href]").evaluateAll(
      (as) => as.map((a) => (a as HTMLAnchorElement).href))) links.add(h);
  };

  await page.goto("/");
  const rows = page.getByTestId("ranked-list").locator("li");
  await expect(rows.first()).toBeVisible();
  // the details: a man with a graduate degree, race switched on
  await page.getByTestId("self-sex").selectOption("male");
  await expect(page.getByTestId("seek-sex")).toHaveValue("female");
  await page.getByTestId("self-edu").selectOption("graduate");
  await page.getByTestId("self-race-switch").check();
  await page.getByTestId("self-race").selectOption("black_nh");
  // and a partner filter, so the page re-asks the API
  await page.getByRole("radiogroup", { name: "Cost of living importance" })
    .getByRole("radio", { name: "A lot" }).click();
  await expect(page).toHaveURL(/ic=a/);
  await page.waitForLoadState("networkidle");
  await collectLinks(page);

  // a city page from the list, then the compare page
  await rows.first().getByRole("link").first().click();
  await expect(page).toHaveURL(/\/city\//);
  await expect(page.getByTestId("ranked-card")).toBeVisible();
  await collectLinks(page);
  const qs = new URL(page.url()).search;
  await page.goto(`/compare/provo-utah/austin-texas${qs}`);
  await expect(page.getByTestId("compare-table")).toBeVisible();
  await collectLinks(page);
  await page.goto(`/${qs}`);
  await expect(rows.first()).toBeVisible();
  const mine = await rows.evaluateAll((els) => els.map((e) => e.textContent));

  // share: someone else opens the address the sender sees
  const shared = page.url();
  const other = await browser.newContext();
  const theirs = await other.newPage();
  watch(theirs);
  await theirs.goto(shared);
  const theirRows = theirs.getByTestId("ranked-list").locator("li");
  await expect(theirRows.first()).toBeVisible();
  await theirs.waitForLoadState("networkidle");
  // the recipient sees their own figures: no details of the sender's
  await expect(theirs.getByTestId("self-edu")).toHaveValue("");
  await expect(theirs.getByTestId("self-race-switch")).not.toBeChecked();
  expect(await theirRows.evaluateAll((els) => els.map((e) => e.textContent))).not.toEqual(mine);
  await collectLinks(theirs);

  for (const r of requests) {
    expect(r.url, "a request address").not.toMatch(LEAK);
    expect(r.body, `a request body to ${r.url}`).not.toMatch(LEAK);
    for (const [k, v] of Object.entries(r.headers)) {
      expect(v, `request header ${k} to ${r.url}`).not.toMatch(LEAK);
    }
    if (r.url.endsWith("/api/rank") && r.body) {
      expect(Object.keys(JSON.parse(r.body).self)).toEqual(["age"]);
    }
  }
  expect(requests.filter((r) => r.url.endsWith("/api/rank")).length).toBeGreaterThan(0);
  for (const h of links) expect(h, "a link on a page").not.toMatch(LEAK);
  for (const c of [...(await context.cookies()), ...(await other.cookies())]) {
    expect(decodeURIComponent(c.value), `cookie ${c.name}`).not.toMatch(LEAK);
  }
  expect(permalinks.length).toBeGreaterThan(0);
  for (const p of permalinks) {
    const tok = p.split("/").pop()!;
    const core = JSON.parse(Buffer.from(tok, "base64url").toString("utf-8"));
    expect(Object.keys(core.self)).toEqual(["age"]);
    expect(JSON.stringify(core)).not.toMatch(LEAK);
  }
  expect(noPolicy, "responses without Referrer-Policy: no-referrer").toEqual([]);
  // the cookie holds the other settings for 30 days at most
  const prefs = (await context.cookies()).find((c) => c.name === "dsa_prefs");
  expect(prefs).toBeTruthy();
  expect(prefs!.expires).toBeLessThanOrEqual(Date.now() / 1000 + 30 * 24 * 3600 + 60);
  // the details live in this browser only
  const stored = await page.evaluate(() => window.localStorage.getItem("dsa_about_you"));
  expect(JSON.parse(stored ?? "{}")).toEqual(
    { sex: "male", edu: "graduate", raceOn: true, race: "black_nh" });
  await other.close();
});

test("an old link's details move into the browser and leave the address", async ({ page }) => {
  const sent: string[] = [];
  page.on("request", (req) => {
    if (req.url().endsWith("/api/rank")) sent.push(req.postData() ?? "");
  });
  // a link made before m4.0.0: the details in the query, no sought sex
  await page.goto("/?self_sex=male&self_age=34&self_edu=bachelors&self_race=hispanic&age=28-40&marital=never");
  await expect(page.getByTestId("ranked-list").locator("li").first()).toBeVisible();
  await expect.poll(() => page.url()).not.toMatch(/self_(sex|edu|race)/);
  // the search it meant — a man seeking women — is kept
  await expect(page).toHaveURL(/sex=female/);
  await expect(page.getByTestId("seek-sex")).toHaveValue("female");
  await expect(page.getByTestId("self-sex")).toHaveValue("male");
  await expect(page.getByTestId("self-edu")).toHaveValue("bachelors");
  await expect(page.getByTestId("self-race")).toHaveValue("hispanic");
  for (const b of sent) expect(Object.keys(JSON.parse(b).self)).toEqual(["age"]);
});

test("the API refuses the details if anything ever sent them", async ({ request }) => {
  for (const extra of [{ sex: "female" }, { education: "graduate" }, { race_ethnicity: "asian_nh" }]) {
    const r = await request.post("/api/rank", {
      data: { self: { age: 30, ...extra },
              seeking: { sex: "male", age: [28, 40], marital: ["never_married"] } },
    });
    expect(r.status(), JSON.stringify(extra)).toBe(422);
  }
});

test("a returning visitor's stored details never show the list in another order first", async ({ page }) => {
  // no reordering flash: the server renders the default variant; the
  // pre-paint script hides what a stored variant changes until the page
  // has selected it. Every frame in which the list is visible shows the
  // final order.
  await page.addInitScript(() => {
    const w = window as unknown as { __frames: { visible: boolean; order: string }[] };
    w.__frames = [];
    const tick = () => {
      const ol = document.querySelector('[data-testid="ranked-list"]');
      if (ol) {
        w.__frames.push({
          visible: getComputedStyle(ol).visibility !== "hidden",
          order: [...ol.querySelectorAll("li")].map((li) => li.getAttribute("data-cbsa")).join(","),
        });
      }
      if (w.__frames.length < 3000) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
  await page.goto("/");
  const rows = page.getByTestId("ranked-list").locator("li");
  await expect(rows.first()).toBeVisible();
  const defaultOrder = (await rows.evaluateAll((els) => els.map((e) => e.getAttribute("data-cbsa")))).join(",");
  // now as a returning visitor whose details select another order
  await page.evaluate(() => window.localStorage.setItem("dsa_about_you",
    JSON.stringify({ sex: "female", edu: "graduate", raceOn: true, race: "asian_nh" })));
  await page.reload();
  await expect(rows.first()).toBeVisible();
  await page.waitForTimeout(400);
  const frames = await page.evaluate(() =>
    (window as unknown as { __frames: { visible: boolean; order: string }[] }).__frames);
  const final = frames[frames.length - 1].order;
  expect(final, "the stored details must select a different order for this test to see a flash")
    .not.toBe(defaultOrder);
  expect(frames.length).toBeGreaterThan(0);
  expect(frames.filter((f) => f.visible && f.order !== final)).toEqual([]);
});
