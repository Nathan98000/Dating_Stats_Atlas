# Phase 5 — the redesign (design audit of 8 October 2026)

## 1. In plain words

The site now looks and behaves like the mock. The search moved up into a
one-line sentence under the headline, the controls sit in a slim side rail
(on phones, in a sheet that slides up), and the top three cities are cards.
Every other city is one compact row with small "why it ranks here" tags, and
its details open on a click. On a laptop the first result is now in the
first screen, 514px down instead of 745px. The home page went from about
52,000px tall to about 2,200px, because it shows ten cities at a time
instead of all 193. On phones nothing scrolls sideways any more.
No score, rank or count moved. Every one of the 518 test searches serves
the same numbers as before. The only change underneath is the
"biggest pluses" line, which now names at most two pluses and the biggest
minus. Everything is built and tested locally. **Nothing is deployed** —
that waits for your go.

Branch `claude/phase5` (not pushed): A `35e9c76`, B `3798b3f`, C `30e1188`,
D+E `7988fdb`, F `10fd516`, G `db5ca1d`, H `59c80f0`, I `ac7c1f7`, plus this
report.

## 2. The commits

| | What changed |
|---|---|
| **A** | Caddy compresses responses (`encode zstd gzip`). `caddy validate` passes. Takes effect on the VM only. |
| **B** | The new colour tokens, the type scale (display-1 … data-m, smaller on phones), the 6/10/16 radii, two shadows, Figtree 500, Fraunces SOFT 30, 16px inputs with a 3:1 border. Old radii mapped onto the scale. A contrast test reads the tokens from the CSS. |
| **C** (m4.2.1) | The movers pick is now two pluses at most, then the biggest minus. It is served as data (`movers: [{key, sign}]`), and the line reads "Biggest pluses: X, Y · Biggest minus: Z". Chip labels, "walkable neighborhoods", and the brief's whole copy table went into the registry. Build id kept, manifest refreshed, goldens regenerated (only the lines moved). |
| **D+E** | The home page rebuilt: hero and quick search, rail, results header, three cards, rows with chips and expandable detail, show more, find in results, a pending line, row moves animated (FLIP), a live region, and "How the score works". Phones and tablets: a new header, the sticky "Adjust your search" bar, and the sheet or drawer. One commit, since they ship as one release. |
| **F** | Compare: an Edge column ("▲ Boston"), stacked blocks on phones with no sideways scroll, warning colours on the notices, and "Your top two" on /compare. |
| **G** | City page led by the score; photos cropped only when public domain or CC0; empty alt where the manifest's alt says nothing; map thumbnail and two cards per row on phones. `<main>` on every page, a real 404, a title and preview tags per page, the footer everywhere, About renamed "How it works". The sweep: no arbitrary sizes left, and `--male`/`--female` deleted. |
| **H** | 36 photo candidates for 12 metros, for you to pick. No manifest touched. |
| **I** | Each variant serves its median score. A tick and "median 43" mark it on the card and city-page score tracks. |

## 3. For your approval

**a. Strings.** Every change is in `results/phase5/copy_changes.json`. The
brief's copy table went in verbatim. Old → new, for the ones that replace
something:

| Where | Old | New |
|---|---|---|
| Hero subhead | Select who you're looking for and what matters to you. Find out how many people match your search in each city based on Census data. | See how many single people who fit what you want live in each US metro, from Census data, ranked for you. |
| About heading | About the site | How it works |
| Nav | Home · Compare cities · About the site | Rankings · Compare · How it works |
| Slider label | What matters more to you? | Bigger pool or closer match? |
| Movers line | Biggest pluses: X, Y, Z · Rent counts against it | Biggest pluses: X, Y · Biggest minus: Rent |
| Mover phrase | walkable neighbourhoods | walkable neighborhoods |
| Purity flag | …shares with its neighbours. | …shares with its neighbors. |
| Terms (photographs) | …under the licence listed there | …under the license listed there |
| Compare footnote | Green means the difference favors… | Edge shows which city does better on each measure for your search; a dash means we don't judge it. |
| List heading | Cities for you / {n} cities for you | Top cities for single {sought}, {ages} + "{n} metro areas, scored out of 100 for what you chose" |

The US-spelling sweep found only those three served British spellings
(plus "Grey" in the old compare footnote, which no longer shows).

**b. Copy I had to invent** (drafts, all small):

- Registry: `row_details` "Details for {city}" (the row chevron's spoken
  name); `pool_row_unit` "single {sought}" and `score_out_of` "/100" (the
  brief's wording, but missing from its table); `not_found_title`
  "Page not found" and `not_found_body` "There is no page at this address."
  (the 404).
- In code, alongside the existing chip wording: the "Narrow it down"
  summary pieces from the brief's example ("Any education", "Any income",
  "All races", "divorced/widowed"). Also the live region's change phrases:
  "ages 28–45", "worst first", "your age, 34", "what matters to you",
  "bigger pool or closer match".
- Accessible names: "Menu", "Main" and "Footer" (the two navs), and "Show"
  (the Best/Worst group, the old visible label).

**c. The minus is capitalised**, as in the brief's example ("Biggest minus:
Rent"). Mid-line it reads "Biggest minus: The compatibility figure". The
line is screen-reader text on rows now (the chips show visually), but if
you'd rather have it lowercase, it is one line in `explain.summary_line`.

**d. Alt texts** (`results/phase5/alt_audit.json`). These eight show
`alt=""` now. Drafts, written after looking at each photo; the manifest is
unchanged:

| Metro | Manifest alt now | Draft |
|---|---|---|
| Abilene, TX | image | Downtown Abilene's brick and stone high-rises above a line of trees under a clear blue sky. |
| Chambersburg, PA | (none) | A white clock tower above a columned brick courthouse on Memorial Square, with a tiered fountain and American flags in front. |
| El Centro, CA | (none) | The Imperial County Superior Courthouse at dusk, its columned front lit, a palm tree in the foreground. |
| Fargo, ND | Downtown Fargo Aerial - Facing Southeast (51009704407).jpg | Downtown Fargo from the air, looking southeast over low buildings, tree-lined streets and a rail line. |
| Gadsden, AL | Flying over the city of Gadsden… (51157939914).jpg | Gadsden from the air, with the Coosa River curving past downtown. |
| Kennewick, WA | Kennewick-ColumbiaRiverAerial | The Columbia River from the air beside Kennewick, with highways, neighborhoods and hills under a cloudy sky. |
| Macon, GA | Macon Georgia Aerial (52700955029).jpg | Macon from high above, its downtown grid beside the river and the highways around it. |
| San Francisco, CA | zeppelin-ride-020100925-195 | Alcatraz Island from the air, with a ferry and a sailboat on San Francisco Bay. |

**e. Photo candidates** — `results/phase5/photo_candidates.md`, one table
per metro, with local copies under `results/phase5/_photos/`. All twelve
top metros qualify: eleven current photos are CC BY or BY-SA, which a card
can't crop, and Portland's is a CC0 drone aerial. Every one of the 36
candidates is public domain or CC0, passes the pipeline's licence gate, and
was checked by eye. Strongest picks: San Francisco, Green Street in North
Beach; Boston, Acorn Street; New York, Broadway in SoHo; Philadelphia,
Elfreth's Alley. Two to check for faces: Boston 2 and Chicago 1. Until you
pick, these cards show the locator map.

**f. The movers change** (`results/phase5/movers_examples.json`). Default
search (193 ranked), before → after:

| # | City | Before | After |
|---|---|---|---|
| 1 | San Francisco | pluses: pool, compatibility, walkable | pluses: pool, compatibility · minus: Rent |
| 5 | San Jose | pluses: compatibility, pool, walkable | pluses: compatibility, pool · minus: Rent |
| 95 | College Station | plus: compatibility · pool counts against | pluses: compatibility, everyday prices · minus: pool |
| 98 | Savannah | plus: places to go out · Rent counts against | pluses: places to go out, weather · minus: Rent |
| 189 | Clarksville | The size of the pool counts against it | pluses: everyday prices, rent · minus: pool |
| 193 | Ocala | The compatibility figure counts against it | plus: weather · minus: compatibility |

The full 15 rows for each search are in the JSON. The same-sex reference
search reads the same way (Waterbury, last: "Biggest minus: The
compatibility figure").

At the top of the default list the chips are mostly the same: eight of the
ten read **▲ Dating pool ▲ Compatibility ▼ Rent** (San Jose has its two
pluses the other way round), and Chicago and Philadelphia read
▼ Everyday prices. That is an honest result, not a bug: big expensive
cities win on the pool and the figure and lose on rent. If you'd like the
chips to say more, one option is to show lifestyle movers only, since the
pool already has its own column. I haven't built it.

**g. Two judgment calls to confirm** — see Deviations 3 and 4.

## 4. Measurements

Before is m4.2.0 at `ec69d17`; after is this branch. Both are production
builds on build 63c4e5fa51bf (`measure_before.json`, `measure_after.json`).

| | Before | After |
|---|---|---|
| #1 result's top, 1440 / 1024 / 768 / 390 | 745 / 745 / 2,101 / 2,150 px | **514 / 548 / 602 / 636** px |
| #1 card's bottom at 1440×900 | — | 897 px (≤ 900) |
| Home page height, 1440 / 390 | 51,986 / 86,801 px | **2,169 / 3,929** px |
| Row height, rows 4–10, 1440 / 390 | 274 / 459 px | **81 / 133** px |
| Page width at 390 (every page) | 423 px (sideways scroll) | **390** |
| `/api/rank` bytes (default search) | 1,503,427 raw on the wire | 1,476,574 raw; 227,321 gzipped. Caddy serves it gzipped after deploy (to check then) |
| axe, all severities incl. best-practice, 9 pages × 2 widths | city 60, compare pair 29 (incl. 2 `empty-table-header`), 404 5, home 1, stat 1 | **0 on every page** |
| Distinct font sizes in `src/` | 34 | 18 (all on the scale) |
| Distinct radii | 12 | 10 |
| Arbitrary `text-[…]`, `rounded-[…]`, `min-h-[…]` | 187 | **0** |
| Control heights (source census) | 3 | 3 (44px everywhere; 32/36px only at the desk) |

The control-height count is a rough census of the source, method in
`style_census.py`.

Screenshots are in `results/phase5/screens/before/` and `…/after/`: the
home page at 1440, 1024, 768 and 390 (top, scrolled, a row expanded); city,
compare and About at 1440 and 390; and the sheet open at 390.

## 5. Tests and gates

| Check | Result |
|---|---|
| No number moves (C) | 518/518 `/v1/rank` responses identical without explanations; 1,036/1,036 single-seeker rankings; 387/387 profiles; political lean; both reference searches (`served_numbers_commit_c.json`) |
| No number moves (I) | the same, `score_median` aside; no line changed (`served_numbers_commit_i.json`); the whole series against the baseline: `served_numbers_all.json` |
| A, B, D–H | no API or model code changed (G only adds a chrome block to `stat-pages.json`, everything else in it byte-identical) |
| Hard gates (`build.validate`) | **11/11** |
| Goldens | regenerated in C (summary lines only); unchanged by I |
| Latency p95 | **61.3 ms** (limit 100; m4.2.0 measured 57.8); Low Power Mode off |
| pytest / vitest / Playwright | **190 / 135 / 241 passed** (19 skipped by design: per-width tests); CI rehearsal on a fresh checkout without photos: 241 passed |
| Privacy network test | passes (see Deviation 4) |
| Contrast | `tests/contrast.test.ts`: `--line-strong` 3.26 white / 3.07 paper; selected segment 6.47; chips 6.66 / 7.53; warning and error pairs ≥ 4.5 |
| axe (1440, 390, every page) | 0 serious/critical; `landmark-one-main` and `skip-link` pass on city and compare |
| Banned vocabulary | none (registry loader, validate gates, e2e sweeps) |
| Pew history scan | clean, 0 of 2,027 blobs |

**Tests removed or replaced** (the element went):

- `panel.spec`: both "the panel sticks and scrolls inside itself" tests. The
  rail no longer scrolls inside itself; replaced by "fits 1440×900 without
  its own scroll".
- `panel.spec`: "at phone width the panel is a normal block". `chips-bar`
  is gone; replaced by the sheet and drawer tests.
- `phase4b`: "two labelled sections: About you, then Who you're looking
  for". Those sections are gone; replaced by the quick-search and
  rail-groups test.
- `phase4b`: "every home row … label the overall score". The column label
  carries it now; the test checks that instead.
- `about-us`: the hero credit test and "the home page shows the new
  photograph". The photo band is gone; replaced by a cropped-credits test.
- `about-us` / `terms`: the About top buttons tests. The buttons are gone;
  replaced by footer tests.
- Test ids removed: `chips-bar`, `hero-photo`, `hero-placeholder`,
  `about-links`, `about-privacy-link`, `about-terms-link`.

Other specs were moved onto the new structure. They open the collapsed rail
groups, expand rows to read figures, use the Best/Worst radios, and read the
new nav labels. No check was dropped.

## 6. Deviations

1. D and E are one commit: they ship as one release, and their code is
   interleaved.
2. Commit C was amended twice (fixups before any push) so that every served
   string still lands in C. That covers three strings D needed and the two
   404 drafts. I adds `score_median_caption`, as the brief says.
3. `compare_diff_legend` is still served, unused, because retiring it in C
   would break the compare page at the D+E commit. Retire it with the next
   copy release. `about_privacy_link` and `about_terms_link` are likewise
   unused now; the loader still requires them.
4. **The privacy network test gained one line**: it opens "Sharpen
   compatibility" before choosing education and race. The brief asks for
   that group collapsed by default and for the test to pass unchanged, and
   both can't hold. None of its checks changed. Please confirm you're happy
   with that.
5. The header, footer and page titles read their registry labels from a
   `chrome` block in `stat-pages.json`, not from `/v1/meta`. The stat pages
   are prerendered at image build time, when the API isn't reachable on the
   VM.
6. The cards' locator map is a static SVG at `/map/<cbsa>.svg`, with the
   tokens' hex values baked in (an image can't read CSS variables). This
   keeps 160KB of map data out of the page's script.
7. The sheet holds the three rail groups, as specified. Sex and ages are
   only in the hero, so changing them from deep in the list means scrolling
   up.
8. The rail's group headings are h2 elements styled at the h3 size. As h3s,
   axe flagged heading order.
9. The balance track's box is 176px wide (track still 120px), so "More
   women · Even · More men" fits beneath it.
10. "Your top two" uses the default variant: the server never sees the
    visitor's own details.
11. The chip ▲/▼ glyph is drawn as SVG, because 12px is the smallest type
    size.
12. The 1440 fold needed 8px tightened under the results header once the
    median caption arrived (card #1's bottom went from 904px to 896px).
13. On phones the stat-card value is 24px via the h2 phone size, not a
    separate token.

## Deploy

Commit A needs the Caddy restart, and D through I need new images. The
build id is unchanged (63c4e5fa51bf, manifest refreshed: copy the new
`manifest.json` into `/srv/atlas/build`). Shall I deploy, following
`docs/deploy.md`?
