# Phase 6 — the round-3 review, built

## 1. In plain words

Everything the round-3 review asked for is built, except the two items you
set aside (margins on matches, and deploying). Phones now get photographs sized
for the screen instead of the full originals. The first big picture on a
typical phone connection appears in about **2.4 seconds instead of 11**.
Same-sex searches now say plainly that "matches" counts everyone of that sex
and age, not only the people looking for men or women. Numbers that read
against themselves now read straight. Compare says "▲ Abilene, by $526"
instead of "+$526". "Who lives here" rounds both of its figures the same way,
so Abilene reads "180,000 people, of whom 120,000 are adults". No unranked city
claims to have 250,000 people. The cautions the API has always sent for 15
cities now show. On a phone, "Show results" lands you on the results, and a
line names the new top three. The top three cards open their details like
every other row. The chips now give lifestyle reasons, so the top ten tell
apart: five different sets where there were two (half the ten still read
"Walkability · Places to go out · Rent": big cities share those traits).
City pages lead with the score, and their HTML is about **eight times
smaller** (281 KB to 36 KB). Eleven photographs changed,
including Los Angeles: the downtown skyline under the snowy San Gabriels
replaces the Hollywood Sign.

No score, rank, count, balance or compatibility figure moved for any of the
518 test searches. The model is **m4.3.0** on a **new build id,
d62202fd0280**: you accepted that when the regenerated city descriptions
moved it (only the description text differs). **Nothing is deployed or
pushed.**

Branch `claude/phase6` off `claude/phase5` at `f18a810`, unpushed.

## 2. The commits

| | Commit | What changed |
|---|---|---|
| **R** | `21880fe` | The review committed as it was (`docs/design/review-2026-10-08/`). Its scripts are copied to `web/scripts/review/` and run on this Mac: bare imports, Playwright's own Chromium, paths relative to `atlas/web`, `BASE` from the environment. Baseline on this machine in `results/phase6/before/`. |
| **A** | `720c03b` | Photographs at the size they're shown (F03). `scripts/photo_sizes.mjs` (sharp 0.35.4, now an explicit devDependency) writes WebP copies (480–2048px, q72), 1200×630 link previews, and `src/data/photo-sizes.json`. Cards, band and stat photo carry `srcset`/`sizes`/`width`/`height`. Card #1 and the band are high priority; cards #2–#3 are lazy. The Caddyfile caches `/cities/*`, `/stats/*`, `/og/*` for a week (validated, not deployed). `deploy.md` names the new folders. |
| **B** | `8f6df87` | m4.3.0. `lifestyle_movers` is served on every explanation (F12). One spoken-figure rule, `model/spoken.py`: 2 significant figures, and the floor guard (F09). The registry gets `population_floor: 250000` and the approved copy table. A new hard gate, `spoken_figures`. ADR drafts 0003, 0004, 0007 and 0018. Build kept, manifest refreshed. |
| **B2** | `6a7174c` | The stop condition, and your answer. The descriptions are regenerated with the same rule, so the build id moved to **d62202fd0280**. Only `description` differs, in `metros.json` and `features.parquet`; every response is the same bytes but for the id. `launch.json`, the fixture, the variant cases and the deploy notes follow. |
| **C** | `5e2b770` | 44×44 targets below 1120px (F02). Sliders get a 44px hit area with a 28px visible thumb. The age popover gets exact "From / to" fields. City names, secondary links, footer, brand, summaries and credit links are all 44px targets. Adds the Phase 6 Playwright projects and the target audit test. |
| **D** | `e4293c1` | Home results. The cards get a Details chevron and the same three tiles (one panel from 768px, inside the card below) (F06). Lifestyle chips (F12). Caution captions (F08). The same-sex note and balance caption (F01). "Matches" on phone rows. Chip words on the bars ("Cost of living · rent") (F21). The yardstick shown (F22). "Even" in the tile (F25). Screen-reader score labels and named ⓘs (F26). On phones, Best/Worst moves under the cards and photos are 16:7, so #1's score is in the first screen (F15). |
| **E** | `f07976d` | Changing the search. "Show results" focuses the results heading, the bar shows the pending line, and moved rows tint while a "New top three" line shows (F05). About-you changes are announced (F13). The sheet's summary row (F19). The sex flip only while "Looking for" is untouched (F20). The place is kept on the way back (F18). Info boxes no longer open on focus and keep clear of their tile (F17). Focus never hides under the bar (F27). The phone menu closes on Escape or outside (F28). The site's own Clear (F35). The age token's name (F37). No lone labels (F34). |
| **F** | `e24f26e` | Trust. An ⓘ beside "Optional" (F10b). The Privacy sentence (F10a). How it works takes the registry's `match_how` (F11). |
| **G** | `c665c4f` | Compare. Edge "▲ Denver" over "by 31,802" (F07). A neutral starting-search note (F23). "Not ranked: under 250,000 people" (F24). The same-sex note on the Matches row (F01). The row is named "Matches" (F21). |
| **H** | `794808e` | The city page leads with the score (F16). Its score card gets cautions and the same-sex note. The floor is stated (F24). Crime ⓘ names (F26). Place captions under the band (F29). The locator is a static `/map/<cbsa>.svg` with only the metro's own data sent (F32). Stat pages use the segmented sort and the photo's own shape (F33). Sharing: results titles, own `og:url`, large previews, and a home preview image (F31). The footer sits at the bottom (F36). |
| **I** | `15f3074` | Photographs (F30). Los Angeles, ten weak photographs replaced, two kept with reasons, focal points for five crops, Kalamazoo's alt text, contact sheets, and ADR 0012's draft. |

## 3. For your approval

**a. Strings, old → new.** The prompt's copy table went in as written, with
the changes it makes. Each is in the registry, served through `/v1/meta`:

| Key | Old | New |
|---|---|---|
| `pool_short_unit` | single {sought} match | matches |
| `features.pool_size.display_name` | People who match | Matches |
| `features.pool_size.unit` | people match what you're looking for | matches |
| `chip_label` (students) | Students | Student life |
| `compare_edge_note` | Edge shows which city does better on each measure for your search; a dash means we don't judge it. | Edge names the city that does better on each measure for your search, and by how much. A dash means we don't judge that measure. |
| `compare_default_note` | These figures use the stated default search — {search}. Change anything on the home page and they become yours. | This comparison uses the site's starting search: {search}. Set your own on the home page and it follows you here. |
| `crime_card_info` | About this figure | About the {stat} figure |
| `explainer_lifestyle` | Lifestyle: four things you weight — cost of living, … | Lifestyle: Four things you weight: cost of living, social life, student life and weather. |
| `excluded_count` (policy) | {n} cities don’t have enough people matching this search to make a reliable estimate. Widen your search to see more cities. | {n} metro areas don’t have enough people matching this search for a reliable estimate. Widen your search to see more of them. |
| `same_sex_pool_note` (new) | — | On a same-sex search, matches count every single {sought_one} in these ages. The Census doesn't ask who people date, so only some of them are looking for {sought}. (The table had `{sought}` in both places; see 3b.) |
| `balance_caption_same_sex` (new) | — | Balance compares all single men with all single women in the ages you picked. On a same-sex search it describes the city, not your matches. |
| `compare_edge_by` / `compare_edge_places` (new) | — | by {diff} / by {n} places |
| `compare_not_ranked` (new; was the literal "Not covered") | Not covered | Not ranked: under 250,000 people |
| `city_below_floor` (new; was a literal) | {city} sits below the population floor this site ranks, so it never appears in results — its profile is below. | {city} has fewer than 250,000 people, so it isn't ranked; the site ranks metro areas of 250,000 or more. Its profile is below. |
| `results_new_top` (new) | — | New top three: {a}, {b}, {c} |
| `results_change_race` / `results_change_education` (new) | — | your race or ethnicity / your education |
| `sheet_search_summary` (new) | — | {you}, {age} · {sought} {ages} — Change |
| `sought_flipped` (new) | — | Looking for changed to {sought} |
| `balance_info_label` / `moved_info_label` (new) | (the headings named the buttons) | About balance / About these points |
| `score_label_sr` (new) | — | Overall score {n} out of 100 |
| `sharpen_info_label` / `sharpen_info` / `sharpen_info_link` (new) | — | About these details / Optional. These change the compatibility figure only. They stay on this device: the site sends the figures for every combination, and your browser shows yours. / How we handle your details |
| `photo_place_caption` (new) | — | {place}, in the {city} metro area |
| `title_results` (new) | — | {heading} · Dating Stats Atlas |
| `clear` (new) | — | Clear |
| `population_floor` (new, a number) | — | 250000 |
| describeSearch (code) | Men 28–40, never married or divorced or widowed | Single men 28–40 (never married, divorced or widowed) |
| `docs/privacy.md` | Your own browser will keep details about you so the site remembers them for the next time you visit. | Your own sex, education and race or ethnicity never leave your browser. Our server sends the figures for every combination of them, and your browser shows the one that fits you, so we never learn which one that is. Your browser keeps them so the site remembers them next time you visit. |
| `docs/methodology.md` | The compatibility score is built from real couples… racial/ethnic pairing… | the registry's `match_how`, as it stands |

The full list, generated from the registry at `f18a810` and now, is
`results/phase6/string_changes.json`.

**b. Copy I had to invent** (all small):

- The line under the count joins its two parts with a full stop:
  "Results updated for what matters to you. New top three: Austin, Boston,
  San Francisco". The second part shows only when the top three changed.
- An own-sex change with no request says "Results updated for men" or "…for
  women". The prompt asked for "the existing sex phrase", and the only one
  is the sought sex's word, so the own sex uses the same word.
- The same-sex note's first slot. As the table wrote it, one word filled
  both places, so it read "every single men in these ages". The first is
  now `{sought_one}`, "man" or "woman": "every single man in these ages …
  only some of them are looking for men".
- Compare's Edge cell adds a hidden comma, so a screen reader hears
  "Denver, by 31,802".
- The registry's `clear`, "Clear", which the prompt names. It travels in
  the chrome block, as the header's other labels do.
- The home preview image sets the site's name over the headline, both
  registry strings.

**c. Alt texts for the new photographs** (drafts, written after looking at
each one):

| City | Photograph | Draft alt |
|---|---|---|
| Los Angeles | Los Angeles, Winter 2016 (CC BY-SA 4.0, salewskia) | Downtown Los Angeles's towers in front of the snow-capped San Gabriel Mountains on a clear winter day. |
| Reading | Pagoda (Reading, Pennsylvania) (CC BY-SA 4.0, firoz-ansari) | The red, tiered Pagoda on Mount Penn above Reading under a bright blue sky, framed by tree branches. |
| Davenport | Centennial Bridge (CC BY 3.0, Bohao Zhao) | The arches of the Centennial Bridge spanning the Mississippi River at Davenport, seen from the riverside wall on a sunny day. |
| Bridgeport | Downtown Bridgeport, Connecticut (CC BY 4.0, Quintin Soloviev) | Downtown Bridgeport's towers across the harbor, with a ferry at its dock in the foreground, on a clear winter day. |
| Cape Coral | Cape Coral, Florida (CC BY 2.0, David Wilson) | Cape Coral's grid of canals and streets seen from the air, with open water and the Gulf coast beyond. |
| Toledo | Toledo, Ohio Skyline, July 2022 (CC BY-SA 4.0, MrJacon000) | Downtown Toledo's towers along the Maumee River on a summer day. |
| Spartanburg | Fountain at Morgan Square (CC BY-SA 3.0, Billy Hathorn) | The fountain on Morgan Square in downtown Spartanburg, in front of the arched brick and stone One Morgan Square building on a sunny day. |
| Wilmington | Wilmington Riverwalk and downtown (CC BY-SA 3.0, Jason W. Smith) | The Riverwalk's wooden boardwalk along the Cape Fear River, with downtown Wilmington beyond, under a partly cloudy sky. |
| New Orleans | Jackson Square (CC BY-SA 4.0, Daniel Schwen) | St. Louis Cathedral rising behind the Andrew Jackson statue in Jackson Square, New Orleans, under a deep blue sky. |
| Amarillo | High-rises on Polk Street (CC BY 2.0, Paul Sableman) | Two brick high-rises frame Polk Street in downtown Amarillo in the late-afternoon sun. |
| Hickory | Elliott Carnegie Library (CC BY-SA 3.0, Tylerg) | The red-brick Elliott Carnegie Library in Hickory, with its white columns and arched doorway, under a blue sky. |
| Kalamazoo | (photo unchanged) | Downtown Kalamazoo's brick buildings and glass towers above a green footbridge over Arcadia Creek on a summer day. |

**d. Los Angeles's alternatives.** I applied the first preference, the
skyline with the San Gabriels. The other two I found:

- *LA Skyline Mountains2.jpg* (CC BY-SA 3.0, 2816px). The same view under a
  darker sky.
- *Griffith Observatory with Downtown Los Angeles In The Background*
  (CC0, 2147px). The observatory on its hill with the towers behind,
  hazier.

**e. Photographs kept for want of a better one:**

- **Palm Bay.** Every cleared candidate at least 1,600px wide is the same
  kind of view as now (river, palms, a park's beach), or a single church,
  shop or business.
- **Rockford.** The current photo already is the Rock River past downtown.
  The one stronger view, the river at Fordham Dam, has a large gear-and-"fL"
  logo on a building near the middle of the crop. A focal point lower in
  the frame, about 50% 75%, would show more river and less sky. **Your
  call.**
- **Fargo's band** still cuts its sign. The sign is taller than a 16:7 band,
  so at the 50% 20% you set it reads "FARG" (it read "ARGO" before). The
  card shows it whole.
- **Amarillo** is a modest view. Its rivals had a bank's name on a tower,
  shop signs or a watermark, or showed only a thin, distant skyline.

**f. Permission list.** Nothing new. All eleven new photographs are public
domain, CC0, CC BY or CC BY-SA, each read from the file's own page. Phase
5's two still wait on you: Lafayette (CC BY-NC-SA 2.0) and Springfield,
Missouri (Free Art License, no named author).

**g. ADR drafts**, each at the end of its ADR:

- 0003: the lifestyle chips.
- 0004: the same-sex captions, spoken figures with the floor guard, and the
  cautions shown again.
- 0007: Edge shows the size of the lead.
- 0012: sized copies and previews, the new photographs, focal points.
- 0018: the ⓘ beside "Optional".

## 4. Measurements

Before is `f18a810` on build 63c4e5fa51bf; after is this branch on
d62202fd0280. Both are production builds measured on this Mac with the
review's own scripts. The raw files are in `results/phase6/before/` and
`…/after/`.

| Measure | Review (Linux) | Before (this Mac) | After | Target |
|---|---|---|---|---|
| Home images at 390 (3× screen) | 1,810 KB | 1,810 KB | **318 KB** | ≤ 250 KB — missed, see Deviation 3 |
| Home images at 1440 | 1,810 KB | 1,810 KB | **71 KB** | — |
| Home page weight at 390 | 2,425 KB | 2,401 KB | **931 KB** | report |
| Phone LCP (review profile, gzip stand-in) | 11.46 s | 10.83 s | **2.38 s** | ≤ 2.5 s |
| Weight change → list settled, phone, gzip stand-in | 1.88 s | 1.54 s | **1.62 s** | report |
| Same, without compression (as served today) | 7.86 s | 7.46 s | 8.05 s | — (commit A of Phase 5 waits for the deploy) |
| #1 score bottom at 390×844 | 927 px | 927 px | **839 px** | ≤ 844 |
| City score heading top at 1440 (San Francisco) | 917 px | — | **427 px** | < 900 |
| City page HTML, compressed (San Francisco) | 281 KB | 281 KB | **36 KB** | ≤ 120 KB |
| Targets under 44×44 below 1120 (outside running text) | brand, names, thumbs, links (§6) | — | **0** | 0 |
| axe violations, every page at 1440 and 390, 12 home states | 0 | — | **0** | 0 |
| Who-lives-here displays off by 10% or more | 68 of 387 | 68 | **0** (worst 4.7%) | 0 (max 5%) |
| Distinct chip sets, default top ten | 2 | 2 | **5** | report |
| API latency p95 | — | 61.3 ms (Phase 5) | **72.5 ms** | ≤ 100 ms |

The home page's HTML grew from 293 to 312 KB, because each explanation now
carries its lifestyle movers too. Every page's script grew 1–3 KB.

Five metros' two "who lives here" figures still imply under 60% adults:
Wildwood and Sebastian (retirement areas), Sierra Vista and Yuma (military
and retirement), and Mansfield, whose prisons sit outside the count. The
adults are people aged 18 to 70 outside institutions, so that is real, not
rounding.

Screenshots are in `results/phase6/screens/` at 1440 and 390: the home
page with a card's detail open, the same-sex search (Los Angeles's new
photo is its #3 card), the sheet with its summary row (390), the "New top
three" line after a change, the city pages (San Francisco, Deltona,
Champaign, Virginia Beach, Los Angeles), Compare (Austin–Denver,
Austin–Abilene) and the rent stat page. Every ranked city's photograph as
cropped is in `results/phase6/photos/sheet-01…10.jpg`.

## 5. Tests and gates

| Check | Result |
|---|---|
| No number moves (B) | 518/518 `/v1/rank` responses identical once the allowed fields are masked (explanations, who-lives-here's two strings, the crime box's label); 1,036/1,036 single-seeker rankings; every default-variant line, `top_stats` and `movers` unchanged; 387/387 profiles identical but for who-lives-here (`served_numbers_commit_b.json`) |
| No number moves (B2, the new build) | every response the same bytes but for the build id (`served_numbers_commit_b2.json`); only `description` differs between the two builds (`build_d62202fd0280_vs_63c4e5fa51bf.json`) |
| C–I | every response the same bytes as B2's (`served_numbers_after_b2.json`) |
| Hard gates (`build.validate`) | **12/12**, the new `spoken_figures` included; rank stability 0.999 |
| Goldens | the version line moved (m4.3.0); the fixture follows the new build |
| Latency p95 | **72.5 ms** (Low Power Mode off) |
| pytest / vitest / Playwright | **198 / 145 / 362** passed (50 skipped by design); CI rehearsal on a fresh checkout without photographs: 350 passed, 62 skipped |
| Privacy network test | passes, unchanged |
| Contrast | new pairs: the "New top three" line (ink-2 on paper), a caution caption on an open row (ink-2 on hover), Compare's note (ink-2 on sunken); no threshold lowered |
| axe (1440, 390, every page, 12 home states with the card detail) | **0 violations** in all 62 runs (all rules, best practice included); no experimental finding either (the age token's name mismatch is gone) |
| Banned vocabulary | none (registry loader, validate gates, e2e sweeps) |

**Tests removed:** none. **Test ids removed:** none. New ones include
`card-toggle`, `card-detail`, `flag-captions`, `same-sex-note`,
`results-notice`, `bar-pending-line`, `sheet-summary`, `show-results`,
`back-to-results`, `clear-button`, `age-from`/`age-to`, `sharpen-info`,
`photo-place`, `below-floor`, `stat-photo`.

Older tests changed only where the prompt changed the behaviour or the
copy. Each is noted in its commit:

- the age handles are counted by role, since the exact-age fields share
  their names;
- the visible Best/Worst control (it shows in one of two places);
- the new marital phrase, the same-sex footnote, the screen-reader score
  label, the info buttons' names and the visible yardstick;
- Show results now focuses the heading, and focus alone no longer opens an
  info box (Enter does);
- Compare's "by" line and "Matches", the Privacy and How it works text,
  the map image, the floor sentence;
- the excluded-cities and starting-search copy, and the stat credits'
  "cropped".

Checks that need the real data run against the production build with
`P6_REAL_BASE` and skip in CI: Virginia Beach and Duluth's cautions,
Austin–Denver's "by 31,802" and "by 2 places", Austin–Abilene's "by $526",
and 193 rows restored with #50 in view. All pass. The fixture covers the
rest: Huntington's caution, and the place test on its 11 rows.

## 6. Deviations

1. **B is two commits.** B2 regenerates the descriptions and moves the
   build id. That was the prompt's stop condition, and it went ahead on
   your "Accept the new build id".
2. The card name's 44px target grows into the card's padding (`-my-2.25
   py-2.25`), not its height. The prompt's `block min-h-11` would have
   pushed #1's score to 857px on a 390×844 phone. Rows use the 44px box as
   asked.
3. **Home images at 390 are 318 KB, over the 250 KB target.** A 3×
   phone needs the 1080px copies for a 358px card. The phone card's
   `sizes` is `calc(100vw - 32px)`, its true width; the prompt's `100vw`
   chose the 1600px copies (635 KB). Not tuned to pass. At 2× it is about
   154 KB.
4. The 44px name boxes and secondary links apply below 1120px only, as the
   ground rule says, so the desk's rows stay 81px.
5. The exact-age fields show at every width, not only below 1120px.
6. "New top three" shows only when the top three changed. Otherwise the
   line says just "Results updated for …".
7. An own-sex change with no request uses the sex word, "men" or "women"
   (see 3b).
8. `photo_sizes.mjs` sizes the photographs the manifests list and the disk
   holds, not every file in the folders. Stale files get no copies.
   `photo-sizes.json` groups them under `cities` and `stats`.
9. The Caddyfile was checked with the `caddy:2` Docker image; there is no
   Caddy on this Mac.
10. `excluded_count` keeps the curly apostrophe of the policy strings
    around it.
11. A stat photograph's credit now says "cropped", because its link preview
    is a crop. The stat page itself still shows it uncropped.
12. New Orleans's credit is the photograph's own (Daniel Schwen, CC BY-SA
    4.0). The file's metadata reported the 1856 statue's public domain and
    its sculptor. I've offered a separate task to audit every credit for the
    same slip. It found one more (`results/phase6/credit_audit.json`): the
    pleasant days photograph of Thomas Cole's *The Picnic* was credited to
    the painter, public domain; on your call it is now credited as its page
    states it, Billy Hathorn, CC BY 3.0, on the same file.
13. The review's apply step moved the replaced files to the Trash. Where
    the Trash already held a file of the same name from Phase 5, it was
    overwritten; those were Commons files, re-fetchable from their recorded
    pages.
14. The simplified map drops the District of Columbia's outline, a speck
    at this scale; Washington's dot still shows.
15. Only the city page sends trimmed metadata to the browser. Home and
    Compare send it as before.
16. The accessible-name check allows a space before Compare's hidden
    comma ("Denver , by 31,802"). Speech is the same.
17. The stat source link and the other secondary links are inline-flex at
    every width, so at the desk "Source:" sits on its own line above the
    link.
18. Fargo's focal point is applied as set and still cuts the sign in the
    band (3e).
19. Commits were amended before any push, so each stands on its own:
    - H took a unit test of the new preview metadata.
    - C's credit-list targets moved into one CSS rule. As 750 classed links
      they had doubled How it works' HTML.
    - E's Clear label became a prop. Read from the header's data in three
      browser components, it had added 28 KB of stat data to every page's
      script.
    - B, D, G and H took the same-sex note's `{sought_one}` slot (3b): the
      registry in B, and the home, Compare and city notes in the others.
      The tests, the screenshots and the CI rehearsal were run again after.
20. The same-sex note has two slots where the copy table had one (3b).
