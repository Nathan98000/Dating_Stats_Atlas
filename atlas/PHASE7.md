# Phase 7 — the round-4 review, built

## 1. In plain words

Everything you asked for from the round-4 review is built. **Nothing is deployed or pushed.**

- **Keyboards work again on phones and tablets.** Pressing Tab after "Their age" now lands on
  "Refine your search", which slides into view. Before, Tab walked straight past it.
- **A card's details no longer open out of sight.** On a 1440×900 laptop, clicking San
  Francisco's card showed 17 pixels of its details. The page now glides down to show the whole
  panel.
- **On a phone, the search bar waits for #1's score.** It still appears on the first flick of a
  thumb (from 54px of scroll), but never on top of "77/100".
- **Every score says what it's out of.** All 190 rows and Compare's two score cells now read
  "/100".
- **"What moved the score" agrees with the tags.** Cost of living and Social life now show their
  parts underneath them. After "Cost of living: A lot", Austin reads Everyday prices +4.6 and
  Rent −2.6 under Cost of living +2.0, so its "▼ Rent" tag sits over a red Rent bar. Before,
  36 of 193 cities had a tag pointing the opposite way to its bar; now none do, in any of the
  three test searches. The API does the adding, not the browser.
- **City pages say when they show the starting search.** A visitor arriving cold sees Compare's
  note and "← See the rankings", not "Back to your results".
- **Compare is clearer.** A tie reads "Same", and population reads "Denver, by 600,000".
- **The city page has one filled button**, "Compare cities" at the foot. The top button is
  outlined.
- **The site has its own icon**, a white Fraunces "D" on the berry colour. The framework's starter
  files and the unused hero photo are gone.
- **Search engines get a map.** There is now a `robots.txt` and a sitemap of 401 pages, and every
  page names its one address.
- **The server will send security headers**, including a Content-Security-Policy that lets pages
  load only the site's own files. These are in the repository only, for the next deploy.
- **San Jose's card shows the Cathedral Basilica of St. Joseph** with downtown's towers, in place
  of a hotel front.

No score, rank, pool, balance, compatibility figure, band or suppression moved for any of the 518
test searches. The model stays **m4.3.0** on build **d62202fd0280**. The build keeps its id; only
its manifest was refreshed, for the seven new or changed strings.

Branch `claude/phase7` off `main` at `e34aa55`, unpushed.

## 2. The commits

| | Commit | What changed |
|---|---|---|
| **R** | `b0645fc` | The review committed as it was (`docs/design/review-2026-10-12/`, plus a `.gitignore` for its `node_modules` link). The hand Tab sequence became `web/scripts/review/keyboard_bar.mjs`, and `results/phase7/served_numbers_check.py` is Phase 6's check with `unit_contributions` masked. Baseline at `e34aa55` in `results/phase7/before/`: `numbers_check` (36/193 chips against their pillar bar), `m10_geometry`, `m5_keyboard`, `keyboard_bar` (forward Tab reaches the bar 0 times). |
| **A** | `710cf40` | **R01:** the bar is never `display:none`. While hidden it waits below the window (`translate-y-full`, no clicks); when shown, or while focus is inside it, it slides up (200ms, instant under reduced motion). **R03:** an opened card or row detail whose bottom is below the window scrolls into view (`block: "nearest"`; smooth, or instant under reduced motion). **R08:** the bar shows after 8px of scroll *and* once #1's score is above its top edge, both read from the layout once a frame. **R09:** "/100" (`score_out_of`) after every row score, hidden from screen readers (who already hear "out of 100"), and after both Compare scores. |
| **B** | `714c0ce` | **R05:** the API serves `unit_contributions` on each ranked row: one entry per lifestyle item, with everyday prices as one entry. The detail draws Cost of living's and Social life's items as indented sub-rows: the chip words, largest first, one scale, bars about two-thirds the pillar's height, and a nested list for screen readers. `col_city` is now "City · lifestyle pluses and minus". ADR 0003 has a DRAFT amendment. |
| **C** | `cb51618` | **R04:** the city page's starting-search note and "← See the rankings". **R14:** "Same", and "{city}, by {diff}" (ADR 0007 DRAFT). The outlined "Compare with another city" button. **R02:** `scripts/make_icons.mjs` writes `icon.png`, `apple-icon.png` and a hand-written `favicon.ico`. The five starter SVGs, `hero.jpg` and `hero.json` are deleted, and the photo review no longer reads a hero. Six new registry strings, in the approved wording. |
| **D** | `ff0ba84` | **R07:** `robots.ts`, `sitemap.ts`, and one canonical rule in `pageMetadata`. **R12:** the Caddyfile's security headers, validated with `caddy:2` 2.11.7. `csp_proxy.mjs` and `csp_check.mjs` show 0 CSP violations. `docs/deploy.md` gains a deploy note: recreate Caddy, then the checks listed there. |
| **E** | `20023aa` | **R20:** San Jose's photograph is replaced, pinned by its bytes. Its focal point is set to `50% 0%` so the band keeps the bell towers whole. ADR 0012 DRAFT (San Jose, and the hero's credit as it leaves). |
| report | (this commit) | `PHASE7.md`; after-run results in `results/phase7/after/` and `screens/`; `string_changes.json`; validation report; one e2e timing fix (§5). |

## 3. For your approval

**a. Strings.** All seven are the 13 October table, verbatim (`results/phase7/string_changes.json`):
`col_city` changed; `city_default_note`, `make_it_your_search`, `back_to_rankings`,
`back_to_results`, `compare_same` and `compare_unjudged_by` added. **I invented no copy.** The item
sub-rows use each item's existing `chip_label` ("Rent", "Everyday prices", "Walkability", "Places
to go out").

**b. San Jose's photograph.** It is *2012-07-15 San Jose 021 Downtown, Cathedral Basilica of St.
Joseph*, by Allie_Caulfield, **CC BY 2.0**, as its Commons page states it. The original is 6000px
wide; the 1920px rendition is applied. It shows the basilica's portico and two domed bell towers
between palm trees and downtown office towers, at noon in July. A row of newspaper boxes and three
parked cars sit along the bottom edge: outside the band's crop, and small on the card. CC BY 2.0
is on the licence list, so nothing joins the permission record. It is the brief's second
preference: no skyline I found was as good.

- *Draft alt text:* "The white Cathedral Basilica of St. Joseph in downtown San Jose, its two domed
  bell towers between palm trees and office towers under a clear blue sky."
- *Alternative 1:* *Downtown Skyline from Oak Hill* (CC BY 2.0, HarshLight, 3036px). The skyline,
  but seen from Oak Hill to the south: a thin band of towers above autumn trees, under a grey-blue
  December sky.
- *Alternative 2:* *Plaza de César Chávez, San Jose, California 01* (CC BY-SA 4.0, GualdimG,
  4000px). The plaza's fountain with downtown's towers behind, under a clear sky. The towers are
  plain, so it reads less surely as San Jose.
- None of the downtown skylines I found were taken from Guadalupe River Park or over Plaza de César
  Chávez in daylight at 1,600px or more.
- Crops: `screens/san-jose-crops.png`, `card-1440-san-jose.png`, `card-390-san-jose.png`,
  `city-1440-san-jose-band.png`.

**c. The icon** at 16, 32, 180 and 512: `results/phase7/screens/icon.png`. The "D" is drawn in
Chromium from the build's own Fraunces file (weight 600, SOFT 30), white on #9E3B57. Its ink
height is 56% of the side, and it is centred on its ink. The corners are 22% of the side; the
180px Apple icon is square, since iOS rounds it.

**d. ADR drafts** (each at the end of its file):

- **0003:** per-item contributions are served, and the detail shows cost of living and social
  life by item.
- **0007:** "Same", and naming the larger city "by" the gap.
- **0012:** San Jose's photograph, and the hero photograph leaving the repository.

**e. The hero photo's credit as it leaves:** *Crew 2016-01-10 (Unsplash xCmvrpzctaQ)*, by Crew
crew, CC0, from Wikimedia Commons
(https://commons.wikimedia.org/wiki/File:Crew_2016-01-10_(Unsplash_xCmvrpzctaQ).jpg), cropped. Its
alt text was "A couple holding hands as they walk along a tree-lined sidewalk, seen from behind".
`photo_credits.json` now lists 376 photographs.

## 4. Measurements

Local production build of this branch (`next start` on :3400 over the API on d62202fd0280 at
:8100), Low Power Mode off. Before: `results/phase7/before/` (at `e34aa55`) and REVIEW.md §7.
After: `results/phase7/after/`.

| Measure | Before | After | Target |
|---|---|---|---|
| Tab reaches "Refine your search" (390, 1024, 1440 at 200% zoom) | never going forward (0 of 145 forward presses) | the next stop after "Their age" at every size (`keyboard_bar.txt`: 3 forward hits in the runs; e2e at all three sizes) | the next stop after "Their age" |
| Card #1's panel visible after opening, 1440×900 | 17 px | the whole panel, 394 px (top 506); 768×1024 whole too (`phase7_measure.json`) | whole panel, or its top in view |
| Chips against their item bar | 36 of 193 rows against the *pillar* bar (default) | **0 of 1,569 chips** across the three searches (`chips_vs_items.json`). The pillar-level count is still 36, as the review's `numbers_check` measures it. | 0 |
| Phone bar over #1's score on the first scroll (390×844, 0–160px in 2px steps) | covers it | **never**; first shows at 54px of scroll (score bottom 767, bar top 768) | never |
| Rows showing "/100" | 0 | 190 of 190 at 1440 and at 390, plus both Compare cells | all |
| `/robots.txt`, `/sitemap.xml` | 404 | 200 `text/plain`, 200 `application/xml` (401 URLs, 387 city pages) | 200 |
| Pages with a canonical link | 0 | 21 of 21 (the 404 names none) | all |
| CSP violations through the proxy | — | **0** (76 runs: 23 pages and 15 home states, at 1440 and 390) | 0 |
| axe violations | 0 | **0** (74 runs, all rules plus experimental; `m3_axe.json`) | 0 |
| Home page weight at 390 | 931 KB local (review) | 938 KB (+7 KB, almost all HTML: the embedded per-item numbers) | report |
| #1's position and row heights, every width | `before/m10_geometry.json` | identical | — |
| API latency p95 (400 requests) | 72.5 ms (Phase 6) | 83.3 ms (p50 50.6) | ≤ 100 ms |

Size and contrast audit (`m4_sizes.json`): no text under 12px and no control boundary under 3:1.
The audit reports 235 low-contrast hits, and every one is the "median N" label: the review's known
false positive, since that label sits below the track, on white. Reduced motion
(`m6_reflow_motion.json`): no transitions or animations.

Screenshots in `results/phase7/screens/`:

- the home page with card #1 open, 1440×900: `home-1440-card-open.png`
- the bar after the first scroll, 390: `home-390-bar-first-scroll.png`
- the bar focused by Tab, 390: `home-390-keyboard-bar.png`
- a detail with the item sub-rows: `detail-1440-austin-items.png`
- a cold city page with the note: `city-1440-virginia-beach-cold.png`, `city-390-…`
- Compare, Austin–Denver: `compare-1440-austin-denver.png`, `compare-390-…`
- the city page's two buttons: `city-1440-austin-buttons.png`
- San Jose's card and band
- the icon sheet: `icon.png`

## 5. Tests and gates

| | Result |
|---|---|
| pytest | **214** passed (210 before; `model/tests/test_phase7.py` adds 4) |
| vitest | **151** passed (145 before: four contrast pins and three Compare cases added, one replaced) |
| Playwright (hermetic fixture) | see the final line below; the suite gains `e2e/phase7.spec.ts` (A–D) |
| Real-build checks (`P7_REAL_BASE`/`P6_REAL_BASE` = :3400) | 14 passed, 2 skipped by design: Austin's items, the top 20's chips, Virginia Beach cold, Austin–Denver "Denver, by 600,000" and "Same", and Phase 6's real-build checks |
| e2e through the CSP proxy | 397 passed, 1 failed only because that test pins port 3100 in its URL (`after/e2e_through_csp_proxy.txt`) |
| Hard gates (`build.validate`) | **12/12** |
| Goldens | byte-identical; MODEL_VERSION m4.3.0 |
| Served numbers | B: 518/518 `/v1/rank` responses identical with `unit_contributions` masked; 1,036/1,036 single-seeker rankings; 387/387 profiles (`served_numbers_commit_b.json`). C (registry strings): the same, 518/518 (`served_numbers_commit_c.json`). A, D and E touch no model, API or registry file. |
| Privacy network test | unchanged, passes |
| Banned vocabulary | none (the registry loader, and every added registry and web line) |
| Contrast pins | added: the city note (`--ink-2` on `--sunken`), and an item's label (`--ink-2`), plus and minus values on the open row's `--hover` |

**Final Playwright run:** **401 passed, 0 failed**, 54 skipped (the real-build checks without `P6_REAL_BASE`/`P7_REAL_BASE`, and the projects that skip by width).

**Removed or replaced tests:**

- vitest "leaves rows the site doesn't judge their plain signed difference" is replaced by
  `noEdgeText`'s three cases: the signed difference is no longer shown, and `signedDiff` left the
  code.

**Changed tests, each because the behaviour it pinned changed:**

- `panel.spec` and `copy-2026-10-12.spec`: "not in the viewport" instead of hidden.
  - `copy-2026-10-12.spec` also scrolls 140px instead of 60 (at 1024×768, #1's score clears the
    bar at about 100px).
  - It also blurs the bar before the top-of-page check, since Escape returns focus to it.
- `phase6.spec`: the bar is "in the viewport". The F21 test reads an item's own row where its
  pillar has items. The F08 test waits for the page to come to rest.
- `phase4b.spec`, `phase5.spec`, `phase2f.spec` and `copy-2026-10-10.spec`: Compare's "/100",
  "Same" and "{city}, by {diff}".
- `phase5.spec`: counts only the pillar rows (`:scope > li`).
- `copy-2026-10-10.spec`: waits for the page to come to rest before measuring. This timing flake
  showed up in the final run and is fixed in the report commit.
- `about-us.spec`: checks for `hero.jpg`'s credit by its file name, since `hero.json` is gone.

**Test ids:** none removed. Added: `card-score`, `row-score`, `score-out-of`, `compare-score`,
`moved-pillar`, `moved-item`, `moved-items`, `moved-bar`, `city-default-note`, and `data-key` on
chips.

## 6. Deviations

1. Committing the review normalised `measure/live_site.txt`'s CRLF line endings to LF
   (`core.autocrlf`). It is otherwise unedited.
2. `keyboard_bar.mjs` names a `<select>` by its chosen option ("Woman", "Men"), where the review's
   hand run printed the first ("Man", "Women"). The sequence is otherwise identical.
3. Each item's value is the sum of its stats' *unrounded* contributions, rounded to 2 decimals.
   Adding the already-rounded stat contributions could miss the pillar by 0.02 (cost has three
   stats). This way a pillar's items add up within 0.01, as asserted.
4. Items sit largest first under their pillar, as the pillars are sorted. The brief listed the
   names in a fixed order.
5. Compare's "/100" is read by screen readers: there is no "out of 100" label there to repeat it.
6. The city page's note shows only where the page shows search figures (ranked or left out). A
   city below the population floor gets "← See the rankings" when cold, but no note.
7. "Same" and "{city}, by {diff}" are set at `text-body-sm`, the size of a judged row's city line,
   in `--ink-2`.
8. The icon keeps Fraunces' optical sizing automatic (`opsz` 144 at icon size). Next reports the
   favicon as `sizes="32x32"`; the file holds 16 and 32.
9. The layout names no canonical address, so the 404 has none. Every other page sets its own
   through `pageMetadata`.
10. The sitemap reads the city list from `search-index.json` (387) and the stat pages from
    `stat-pages.json`, at build time, not from the API.
11. The CSP check covered the review's 23 pages and 15 home states (its 14 plus the default), and
    the 404's own 404 is the only console error.
12. San Jose's 1920px rendition is applied, as Phase 6 did. The apply step re-stamped "retrieved"
    on all 103 pinned rows of `city_images.csv`; only San Jose's row was kept.
13. The fixture build has neither Denver nor Virginia Beach. Those checks run against the real
    build under `P7_REAL_BASE`, skipped in CI, as Phase 6's `P6_REAL_BASE` checks are.
14. Latency p95 rose from Phase 6's 72.5 ms to 83.3 ms, within the 100 ms limit. I didn't measure
    the base commit on the same run, so how much of the rise comes from the new field is not
    isolated.
15. The chips-against-items count is a new script (`results/phase7/chips_vs_items.py`). The
    review's `numbers_check.py` measures chips against their pillar and still reads 36, by
    design.
16. Low Power Mode was on when the work began (`pmset` said 1) and off by the time I measured
    latency (0). I did not change it.
17. The three served-numbers records (`results/phase7/_record_*.json`, 9 MB each) stay out of git
    (`.gitignore`, as Phase 5's are); their comparisons are committed. So are the review scripts'
    first-screen shots (40 MB, regenerable), as the review did with its own.
