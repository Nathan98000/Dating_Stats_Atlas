# Phase 2e — eight equal groups, one-bedroom rent, photographs with their licences

Builds `98dcbb161236` · models `m2.2.0` then `m2.3.0` · schema `cube-v1`
(unchanged). Reproduce: `bridge.city_points` → `build.descriptions` →
`build.features` → `build.cube` → `build.city_images` →
`tests/golden/make_fixture.py <build>` → `pytest atlas` →
`build.validate <build>` → `cd atlas/web && npm ci && npm run
build:index && npm run build:stats && node scripts/build_us_map.mjs
<build> && npm test && npx playwright test`.

## For Nathan first

**The photographs need the counsel packet.** They are the site's first
shipped third-party assets. A drafted row is already in the packet's
Part-B source table (Wikipedia/Wikimedia Commons contributors; displayed
unmodified; licences restricted to PD/CC0/CC-BY/CC-BY-SA read from the
Commons API; per-image manifest with source, author, licence, deed link,
retrieval date and hash) — it needs counsel's read before launch, and
the stale Climate Normals row was corrected to GHCN-Daily while I was
there. **And the human pass is yours:** 365 thumbnails that are
technically fine may still be visually wrong (a montage where a skyline
would serve, a painting where a photo was meant — the nice-days stat
page currently opens on Thomas Cole's *The Picnic*, public domain and
lovely, but yours to veto). The manifest CSV is the worklist.

## The race change (m2.2.0) — the section a careful reader gets first

Nathan's decision on Phase 2d's open question: **"Two or more races" and
"Another race" are ordinary checkboxes.** Eight groups, one rule, no
special casing — the always-counted OR left `resolve_race_levels`, and a
selection now filters to exactly the ticked groups. `balance_masks` is
untouched: the sex ratio stays race-blind as m2.0.0 made it.

**Proof the default view did not move** — asserted against the pinned
m2.1.0 snapshot, not eyeballed: every race-free persona reproduces its
unrounded scores to **0.00e+00, literally bit-identical**
(`results/phase2e/race_change_report.json`). All-eight ticked is the
same universe none-ticked always was, at the API and round-tripped
through URLs and permalinks.

**What a narrowed selection now drops**, the three worked searches:

| search | old rule | new rule | drop |
|---|---:|---:|---:|
| asian_nh, women seeking men 28–40, Los Angeles | 132,312 | 99,728 | **−24.6%** |
| black_nh + hispanic, same search, Chicago | 204,625 | 190,519 | **−6.9%** |
| asian_nh, same search, Urban Honolulu | 26,792 | 15,943 | **−40.5%** |

Largest exactly where the multiracial share is largest, as predicted.
The two newly selectable levels land on their own calibrated interval
strata (inflation 1.25 / 1.226, printed and confirmed), and `other_nh`
alone suppresses through the ordinary gate (191 metros out,
`n_below_100`/`empty_pool`, no special-cased message — Akron shows the
standard screen). The inverted test asserts the three defining
properties: one ticked group masks exactly its cube level, a partial
selection's pool equals the sum of its groups' pools to float tolerance,
and no served figure includes an unticked level. Copy swept: the panel,
the methodology ("the boxes you tick are exactly who gets counted, with
nothing added"), the stale `race_panel` policy string removed, ADR 0004
annotated, the "N of 8 groups" chip. Goldens regenerated with a
pair-only vector; permalink cases cover pair-only and all-eight.

## Item 9: rent, diagnosed in order (m2.3.0)

1. **The number was right.** Austin's build value matched
   data.census.gov to the dollar ($1,726, B25064 2020–2024), and zero
   jam values exist across all 387 metros.
2. **The distribution said high is real.** Ranked-set median $1,275;
   Austin $1,726 = **85th percentile** on the all-units measure.
3. **The measure changed as decided.** Rent is now **B25031's
   one-bedroom median gross rent**, selected from the group metadata by
   label (`B25031_003E`, "Median gross rent --!!Total:!!1 bedroom" —
   asserted to resolve to exactly one variable). Jam scan clean; the
   documented fallback (all-units with a build-report flag) is unneeded
   — **all 387 metros publish the one-bedroom figure**. Cost pillar
   weights unchanged; the unit line now says what the figure is: "a
   month for a typical one-bedroom, utilities included."

   The evidence table — and the honest headline is that **Austin does
   not drop**:

   | metro | all-units (pct) | one-bedroom (pct) |
   |---|---:|---:|
   | Austin | $1,726 (85) | $1,500 (**87**) |
   | Provo | $1,534 (73) | $1,178 (**63**) |
   | Riverside | $1,846 (89) | $1,436 (**83**) |
   | Chicago | $1,430 (63) | $1,246 (69) |
   | Houston | $1,430 (63) | $1,214 (67) |
   | San Francisco | $2,474 (99) | $2,217 (99) |
   | New York | $1,830 (89) | $1,686 (92) |

   Austin's one-bedroom rents are genuinely high — the "priciest" badge
   was true of singles' rents too. What the switch removes is unit-mix
   distortion: Provo (family stock) falls ten percentile points,
   Riverside six, and small-unit metros tick up. Correlation between
   the measures over the ranked set: 0.975. Scores move τ 0.97–0.99 on
   race-free personas (top-10 overlap 9–10/10, median move ≤1) —
   measured against the m2.1.0 snapshot separately from the race
   change, whose own effect is zero at defaults.
4. **The known distortion is disclosed, not corrected**: the rent stat
   page carries the registry's rent-stabilisation sentence naming New
   York.

## Item 5: the search bug, confirmed then fixed structurally

Confirmed exactly as diagnosed: a test running the compare pickers'
verbatim pre-fix logic (unranked `includes()`, truncation in
alphabetical index order) drops New York for "new york" — that failing
case is kept in the suite as the executable record. The fix is ONE
matcher, `lib/search.ts`, used by the header search, both compare
pickers and the city-page launcher: exact > prefix > substring >
subsequence, punctuation-normalised ("st louis" finds "St. Louis"), and
state tokens carried separately in the index and **capped at 30**, so
"washington" ranks the District first and a state name alone can never
outrank a city. The 18-query matrix passes with the intended city in
the top three, plus an e2e regression on the real pickers and header.

**The matrix caught two shipped display-name defects** (a failing check
being a finding): Washington's slug was
`washington-the-district-of-columbia` — the description grammar's "the"
had leaked into the name and slug, silently orphaning the "DC"/"the
DMV" colloquials since Phase 2c (a dead-key assertion now guards the
index) — and the title-split heuristic had shipped **"Winston, NC"**
and **"Louisville/Jefferson County, KY"** as display names. Names now
prefer the TIGERweb place resolution (natural-name candidates first,
150 km sanity guard), with two registry judgments (Lexington, Macon)
where the Census name is consolidated-government legalese. Exactly two
display names changed, both corrections; Provo's approved description
survives verbatim.

## Item 4 and 6: photographs, licence-first

Sourcing is mechanical and recorded: principal city's Wikipedia lead
image → Commons `imageinfo`/`extmetadata` → licence allow-list
(PD/CC0/CC-BY/CC-BY-SA; NC/ND or unreadable terms refuse; CC-BY-family
files with unreadable authors refuse, because attribution would be
impossible). Displayed **unmodified** — scaled to fit, never cropped
(`object-contain`, letterboxed), so no adaptation exists for
share-alike to attach to. Attribution (author · licence linked to its
deed · source) is composed once into the committed manifests
(`results/phase2e/city_images.csv`, `stat_images.csv`) and rendered
from them; **a photo without a manifest row cannot render**, which makes
gate 4 structural. Files are gitignored and re-fetchable; manifest
hashes pin content. Alt text comes from each file's own Commons
description. Coverage:

| outcome | metros |
|---|---:|
| **photographed** | **365 of 387 (94%)** |
| fallback to the Phase 2d artwork | 22 |
| — persistent download failures (Wikimedia CDN 429s across three passes) | 14 |
| — no resolvable article | 4 |
| — article without a lead image | 1 |
| — lead image is an SVG drawing | 1 |
| — CC-BY-SA licence with unreadable author (attribution impossible) | 2 |

Licence families among the 365: CC-BY-SA 187, CC-BY 123, public domain
33, CC0 22 — all four cleared families, nothing else. Every
CC-BY-family image carries a readable author (asserted), every manifest
row has its file on disk, and the excluded-for-licensing count is 3
(the two unreadable-author files and one image under KOGL, a licence
not on the cleared list — the who_lives_here stat page, which therefore
ships without a photo). Stat pages: **6 of 7 photographed** (Apartment,
Supermarket, Nightlife, Sidewalk, Picnic, College town — subjects mine,
flagged for the same review).

The first run also earned its own findings ledger: the REST summary
endpoint 404s on space-encoded titles (every "{City}, {State}"
candidate silently failed; fixed with underscores), Wikimedia refuses
thumbnail upscales (small originals now ship at their own size), and
webp lead images are photographs too.

## The rest, each with its result

1. **Stat pages sort both ways** — positions numbered once at the
   registry-direction-good end; reversing shows the same numbers in
   reverse (asserted: the priciest city keeps its earned number, it
   never becomes #1). The **distribution strip** renders on every page:
   all 193 ranked cities as ticks along the stat's own range, axis
   labelled at both ends — rent's strip shows the bunching under
   ~$1,100 and the long expensive tail at a glance.
2. **Crime is two cards** in the stats grid: rate, unit line, five-band
   position with **deliberately neutral tones** (colouring a low rate
   "good" would perform the exact comparison the caution disclaims — a
   registry `band_direction` decision recorded in ADR 0006), and the
   Phase 2d popover pattern carrying the coverage line, the FBI's
   caution and the explainer link. Nothing about agencies or panels on
   the card face; `context_only`/weight-0 stand; never-scored is
   asserted in the engine tests, the API tests and a validation hard
   gate.
3. **The map is real**: Census cartographic boundary states
   (cb_2023_us_state_20m — TIGERweb's generalized layers refuse
   geometry over their query API, so the boundary file is fetched and
   parsed at build time), projected to Albers USA by d3-geo **in
   `scripts/build_us_map.mjs`**, shipped as 159 KB of static path
   strings. Two fills and a hairline; the dot from the build's Census
   internal point; an e2e gate greps the client chunks and proves no
   mapping library reached the bundle.
7. **Subheading dropped.**
8. **"My age" takes typed input** — draft state validated on blur with
   the registry's range message; the old per-keystroke clamp (typing
   "34" produced 18 then 70) is the reason this item existed, and the
   e2e types "34" to prove it.
11. **Compare-page crime in plainer words**: two numbers per city side
    by side, one caution banner above ("not reliably comparable between
    cities") with the explainer link, nothing else — asserted to carry
    no coverage percentages and no agency talk outside the banner.
12. **What we measure** joins the nav: every statistic grouped under
    the four importance controls plus "The people", each with its
    plain name, unit, one sentence and its stat-page link; crime has
    its own line with the non-comparability note linking to
    `/about-crime-data`. How it works now links here instead of
    repeating the index. Every word arrives from the registry through
    `/v1/meta`.

## Gates

1. **Pass** — both-ways sort without renumbering + strip on every stat
   page (e2e).
2. **Pass** — crime as two cards with popover detail on city pages, two
   numbers + banner on compare, scored nowhere (three layers of
   assertion).
3. **Pass** — state borders render (51 paths), dots from Census
   internal points, and the bundle grep finds no mapping library.
4. **Pass** — manifest row per shipped photo with licence, deed link
   and source link rendered; no manifest row → no render (structural);
   no cropping (`object-contain` everywhere a photo ships).
5. **Pass** — the 18-query matrix in the top three against the shared
   implementation, from vitest and from the real UI.
6. **Pass** — rent is the one-bedroom figure, zero unhandled jams,
   before/after above.
7. **Pass** — eight equal groups: summable pools, bit-identical
   defaults vs the pinned snapshot, `balance_masks` untouched, inverted
   tests in, no six-groups or always-counted copy anywhere (swept).
8. **Pass** — axe reports **0 serious, 0 critical** across home,
   results, city, compare, compare landing, a stat page, what-we-measure
   and how-it-works (nine shapes); popovers and sort toggles keyboard
   operable; photo alt text from the source descriptions.
9. **Pass** — every new string, threshold and band label in the
   registry (race labels, crime card strings, sort labels, strip label,
   age error, measure-page strings, rent note, display-name
   judgments); banned sweep zero across eleven page shapes.

All eight inherited validation hard gates pass on `98dcbb161236`
(differential 1.98×10⁻⁷ — the SQL mirror follows the eight-group rule
automatically because it calls the same `resolve_race_levels`).

## Timings

| what | measured |
|---|---|
| `/v1/rank`, 400 mixed m2.3.0 queries | p50 **23.5** / p95 31.5 / p99 37.3 ms (target p95 < 60) |
| pytest (41) + vitest (38, incl. the 18-query matrix ×2 suites) | 1.6 s + 0.2 s |
| Playwright e2e, 54 specs, hermetic | 18–56 s |
| full validation suite | ~4 min |
| image sourcing, 387 metros + 7 stat subjects | ~1,200 API calls + 371 downloads across four passes (~75 min wall; cached and resumable — a rerun is minutes) |
| us-map.json | 51 states + 387 dots, 159 KB |

Screenshots: `results/phase2e/01…08` — the rent page with strip and
note, the reversed sort, a photographed city with the real map, the
crime cards with an open popover, the compare banner, What we measure,
the eight-group panel, and the picker finding New York.

## Deviations ledger (with reasons)

- **Two model versions in one phase** (m2.2.0 race, m2.3.0 rent):
  bumped separately so the m2.2.0 note's claim — default outputs
  reproduce m2.1.0 exactly — stays literally true; folding rent into
  the same bump would have falsified it.
- **Crime bands colour nothing** despite item 2 asking for "its
  five-band position": the position renders, the tone is neutral by
  registry decision — a green "safer" label would perform the exact
  cross-city comparison the same card's caution disclaims.
- **The compare banner names agencies once** — item 11 said "no agency
  talk", and the banner is the sanctioned plain-language sentence
  explaining *why* comparison fails; the figures area itself carries
  numbers only, asserted.
- **`build.cube`'s manifest-refresh path carried this phase twice**
  (race_groups, then late registry strings): same-data registry changes
  refresh the manifest in place rather than being silently discarded.
- **Louisville, Lexington and Macon read naturally by registry
  judgment**, not by Census legal name; Winston-Salem reads legally
  because the legal name IS the used name. The rule (place resolution
  first, natural-candidate order, registry override last) is in
  ADR 0006.
- **The stat-page photo subjects are my choices** (Apartment,
  Supermarket, Coffeehouse, Sidewalk, Picnic, Campus, Crowd — config in
  `build.city_images.STAT_SUBJECTS`), flagged for the same human pass
  as the city photos.
- **Old-slug image files from the first sourcing run remain on disk**
  (gitignored, harmless); the manifest is the source of truth.

Inherited and unchanged: deployment waits on the counsel review — now
including the photographs; the hero photo slot stays Nathan's; Phase 3's
premise stays raised in PHASE2C.md.
