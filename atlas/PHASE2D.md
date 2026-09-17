# Phase 2d — Nathan's change list: six pillars, real weather, crime with its caution

Build `dd7374675de7` · model `m2.1.0` · schema `cube-v1` (unchanged).
Reproduce: `build.pleasant_days` → `build.crime` → `build.descriptions` →
`build.features` → `build.cube` → `tests/golden/make_fixture.py <build>` →
`pytest atlas` → `build.validate <build>` → `cd atlas/web && npm ci &&
npm run build:index && npm run build:stats && npm test &&
npx playwright test`.

## For Nathan first: the always-counted race groups

Item 3 stripped the explanatory sentence from the race control, so the
rule that "Two or more races" and "Another race" are always counted is
now disclosed **only on How it works and in the methodology** — anyone
who ticks boxes and counts heads on a results page will find the pool a
little larger than their selection explains, and the explanation is one
page away instead of beside the control. The alternative is dropping the
always-on rule for a plain six-group filter: a smaller model change and
a cleaner story, at the cost of quietly excluding people of two or more
races from every filtered search. **Raised, not decided — both the rule
and its relocated disclosure ship as specified until you call it.**

## The two model changes, measured apart

**Item 4, the pillar split (must move nothing):** lifestyle's 0.10
became weather 0.06 + students 0.04 — the proportion its two features
already carried. Against the pinned m2.0.0 snapshot on identical data,
every metro carrying both features reproduces its unrounded score to
**1.4×10⁻¹⁴** across all 11 personas
(`results/phase2d/split_equivalence.json`). The gate found one
principled exception and it is reported, not absorbed: a metro missing
one lifestyle feature used to hand the whole 0.10 to the sibling
feature; under the split it is missing a whole pillar and the registry's
missing-pillar policy redistributes pro-rata (Boulder ≤3.9 pts, Palm Bay
≤2.4). Moot in the shipped build — no metro lacks pleasant days
anymore.

**Item 11, the weather fix (must move things):** rankings shift
**Kendall τ 0.87–0.94, top-10 overlap 8–10 of 10, median absolute move
1–4 places** across the nine evaluable personas
(`results/phase2d/ranking_shift_m2_0_0_to_m2_1_0.json`). On the default
profile the big movers are coastal California and the Space Coast
rising (Santa Maria +36, Palm Bay +34, Oxnard +26) and rain-heavy
Crestview (−25) falling — the fix finding real weather that normals had
averaged away.

## Item 11 in full: nice days, diagnosed and recomputed

San Francisco's 365 was the symptom; the cause was computing on **30-year
daily Normals**, which average away the day-to-day variation the
statistic exists to count — any city whose *average* day sits inside the
thresholds scores every day (SF, Santa Cruz and San Luis Obispo all
served 365). Recomputed on **GHCN-Daily observations, 1991–2020**, with
precipitation joining the definition (a day needs TMAX 55–85°F,
TMIN ≥ 40°F, and ≤ 0.1 in of rain; all three thresholds in the
registry): a year counts with ≥330 valid days, a station with ≥25 years,
each year scaled by 365/valid.

| city | normals | real days |
|---|---:|---:|
| San Francisco | 365 | **302** |
| San Diego | 165 | **336** |
| Los Angeles | 279 | **320** |
| Honolulu | 322 | **182** |
| Portland | 237 | **165** |
| New York | 211 | **147** |
| Chicago | 193 | **119** |
| Miami | 188 | **153** |
| Boulder | — | **97** |

No metro reaches 365 (max: San Diego, 336). Median absolute change **44
days** — the whole feature moved, as expected. San Diego and LA *rise*
because their old stations sat cool and inland; Honolulu falls 140 days
to rain and the 85° ceiling. The four station-less metros all resolve
under GHCN's larger network, so the missing-feature flags are empty for
the first time.

Three findings from building it, each now guarded mechanically:

- **SNOTEL stations excluded**: nine metros first matched mountain
  snow-monitoring sites (Boulder scored 39 from a ridge). COOP, WBAN
  and CRN stations measure where people live.
- **Matching anchors at the principal city** (TIGERweb Places, cached,
  county fallback): the old central-county anchor sat up to 130 km from
  the city in big Western counties — Reno's "nearest station" was
  118 km away; it is now Reno's airport at 8 km. The same fix corrects
  the locator-map dots and drive-time phrases (364 of 387 city_meta
  rows moved; **Provo's approved sentence is unchanged**). A place
  whose own point is degenerate — San Francisco's includes the Farallon
  Islands, 50 km offshore — is caught by having no station within 20 km
  and falls back to the county anchor. Median station distance 8.5 km.
- **"The wettest metro ranks near the bottom" is not how this climate
  works**, and the gate no longer pretends it is. By inches the wettest
  is Daphne, AL — Gulf rain arrives in bursts on warm days, and Daphne
  sits mid-pack, correctly. By rain-days it is Longview, WA — but
  drizzle-belt wet days are mostly cold days already excluded by
  temperature. What must hold, and is asserted on every build, is the
  **mechanism**: the rain term only ever removes days (true for all
  387) and removes most where wet days are mild (Spearman 0.81 against
  rain-days; the Appalachian wet-mild belt loses the most, ~50 days).
  The coldest-metro assertion stands: Fairbanks, 373rd of 387.

## Item 5: crime, built and gated

The adapter rosters **19,636 agencies**, maps **11,750** into metro
counties by each ORI's own county (489 assigned by nearest-county
coordinates: NOT SPECIFIED entries, unmatched names, and Connecticut,
whose CDE counties predate the delineation's planning regions), and
pulls five years of monthly actuals per agency, cached and resumable.

Coverage by year — the share of each metro's population in agencies
that reported a full year:

| year | median coverage | p25 | metros ≥ 0.6 floor |
|---|---:|---:|---:|
| 2021 | 94.2% | 65.4% | 295 |
| 2022 | 98.3% | 92.2% | 353 |
| 2023 | 98.7% | 92.9% | 359 |
| 2024 | 100% | 95.9% | 370 |
| 2025 | 99.7% | 95.3% | **372** |

**2025 serves** (latest complete year, most metros above the floor);
**15 metros show the blank state** — New Orleans clears the floor at
0.61, which is the coverage figure doing its job in public. Rates
divide by the covered population only. The full-year test is 12
non-null months in both offence categories **plus** the
transition-junk rule, which fires on exactly **13 agency-years**, each
named in `crime_report.json` — NYPD's 2021 (twelve "reported" months
summing below 2 violent per 100k for 8.5M people), Orlando's twelve
literal zeros for 2024 and 2025, and ten more of the same shape.

Face validity: zero metros show violent ≥ property; UCR agency
populations reconcile to census metro totals at median ratio 1.017;
NYC 398 violent / 1,622 property per 100k at 91% coverage, Provo
123 / 729 at 100%. One honest wrinkle to know about: the aggregation's
first run had a bug of exactly the class the brief warned about — the
population picker took the *state's* series for every agency, which
flagged two-thirds of agency-years implausible. The differential
symptom (median coverage 0.0) made it undeniable; the fix keys the
population by the agency's own series name, and the commit records it.

Crime renders on city pages and the compare page with the coverage
line and the FBI's caution attached, the compare note sits **between**
the two columns, nothing is ever scored (asserted at registry load, in
the engine tests, and as a validation hard gate), and the explainer at
`/about-crime-data` is the callout made permanent.

## The rest of the list, each with its result

1. **Panel follows the page** — sticky with its own
   `max-height: calc(100vh − 2rem)` and internal scroll, a labelled
   keyboard-reachable region (arrows scroll the panel, never the page);
   normal block above results at phone width. Asserted at 1280×720,
   1280×900 and 375×812. There is no Recalculate button by design
   (results recompute on every change); the reachability requirement is
   met by every control staying reachable inside the panel's own
   scroll, and by the mobile chips-bar's Change search.
2. **Slider explanation** — a real button beside "What matters more to
   you?", registry copy, opens on hover AND focus AND tap, closes on
   Escape and blur, `aria-expanded` + `aria-describedby`. The e2e
   caught hover-open and click-toggle cancelling each other on pointer
   devices, so tap opens and blur/Escape/pointer-exit close.
3. **Race control stripped** — label, six boxes, clear-all; the
   disclosure lives on How it works and in the methodology (see the
   item for Nathan above). Zero-of-six still snaps back to everyone.
4. **Four importance controls** — labels and subtitles from the
   registry through `/v1/meta`; each control reorders the ranking in
   e2e; students and weather move independently (the split's point).
   `size_vs_odds` removed after its one deprecation version;
   `importance.lifestyle` accepted for exactly this version, landing on
   both halves; contradictions 422.
6. **Five bands** — national quintiles, labels positional, tones
   derived from the registry's `band_direction` through one loader
   rule. Population keeps absolute edges (250k/500k/1M/2.5M), and
   everyday prices *gained* absolute edges mid-phase when its
   percentile band called Provo's 98 "Above the US average" — a false
   sentence on real data, caught in the screenshot pass, fixed at the
   registry, and the reason `build.cube` now refreshes a same-data
   manifest instead of silently discarding display changes.
7. **City artwork** — deterministic seeded composition in the site
   palette, `aria-hidden`, abstract by construction (no data, no
   skyline); a photo at `web/public/cities/<slug>.jpg` (~1600×400,
   wide crop) overrides per city. No photographs sourced — that stays
   with the licensing review.
8. **Compare, reachable** — nav link, landing page with two
   index-backed pickers prefilled from the URL, the whole view still
   rendered from ONE ranking response (ADR 0003), and a no-preferences
   visit labelled with the stated default profile one click from the
   visitor's own.
9. **Stat pages** — seven, serving the 193-city ranked set from a
   build-time JSON (257 KB): no API call, values cell-for-cell equal to
   the city pages because they come from the same artifact through the
   same formatting code (asserted through the UI in e2e). Reachable
   from every card and the How it works index. No page for matches,
   balance, or crime — the first two depend on the search, the third
   has the explainer instead.
10. **How it works** — rewritten with an "in a minute" opener,
    question-shaped heads, a sources table, the stat-page index, and
    every required disclosure (survey and cadence, what a match counts,
    what balance compares, race-selects-who-is-counted with the two
    always-counted groups, why cities drop out, why margins don't
    print, why crime never ranks). Rendered with real heading, list and
    table styles — the page had been dumping unstyled prose.

## Gates

1. Sticky panel: **pass** at both viewports and phone width, keyboard
   included (`panel.spec.ts`).
2. Slider explanation + axe: **pass** — hover/focus/tap/Escape all
   asserted; axe reports **0 serious, 0 critical** across home,
   results, city, compare, compare landing, a stat page and How it
   works (eight shapes).
3. Age slider: **pass** — integer snapping, keyboard operation,
   meet-never-cross re-asserted on the new panel.
4. Crime: **pass** — coverage + caution beside every figure, blank
   below the floor, scored nowhere (engine test, API test, validation
   hard gate).
5. Stat pages: **pass** — cell-for-cell agreement asserted through the
   UI; 193-city universe; crime stat page 404s by design.
6. Methodology: **pass** — structure asserted (≥7 headings, a table,
   lists) plus every disclosure string.
7. Nice days: **pass** — no metro at 365 (max 336.2); mechanism
   assertions hold; split reproduces old scores exactly at defaults
   (1.4×10⁻¹⁴); goldens regenerated under m2.1.0 with the bump noted.
8. Registry ownership: **pass** — every new label, threshold, band
   label, subtitle and tooltip lives in `features.yaml` (the one new
   in-code string caught in review was moved); banned-vocabulary sweep
   zero across registry, 1,480 composed lines, and ten page shapes.

All eight Phase 2b/2c-inherited validation hard gates also pass on
`dd7374675de7`: differential 2.0×10⁻⁷ (three SQL legs), rank stability
0.9–1.0 (every evaluable persona incl. the two new golden vectors),
explanation invariants over 1,480 lines, adversarial artifacts clean,
interval calibration intact.

## Timings

| what | measured |
|---|---|
| `/v1/rank`, 400 mixed m2.1.0 queries | p50 **29.1** / p95 40.2 / p99 57.2 ms (target p95 < 60) — after a bisect fix to the five-band lookup; the first measurement showed p50 51 ms because `_band_of` paid a numpy conversion ~3,000× per request |
| first results, production build, 7 distinct queries | median **83 ms** full server-rendered HTML |
| pytest (41) + vitest (15) | 1.6 s + 0.1 s |
| Playwright e2e, 44 specs, hermetic | 16–31 s |
| full validation suite | ~4 min |
| FBI pull | 23,500 requests, ~2.5 h wall, cached and resumable |
| GHCN pull | ~700 station files, ~25 min, cached |
| artifact | 323 MB; stat pages JSON 257 KB; search index 35.6 KB |

Screenshots: `results/phase2d/01…08` — the four-control panel, the open
slider note, the city page with artwork and five-band cards, the crime
block, the compare crime note between columns, a stat page, the
restructured How it works, and the compare landing.

## Deviations ledger (with reasons)

- **The wettest-metro sanity assertion was refined, not passed**: the
  brief's expectation ("wettest ranks near the bottom") is false of the
  actual climate under the approved thresholds, in both wetness
  measures. The shipped gate asserts the rain term's mechanism instead,
  and this ledger is where the original expectation is recorded as
  disproved rather than quietly reworded.
- **Anchor coordinates changed for 364 metros** (principal-city points
  replace county internal points): adopted mid-phase because the
  weather matching surfaced it, but it also moves locator-map dots and
  drive-time phrases. Provo's approved sentence survives; the rest are
  more accurate, not merely different.
- **`everyday_prices` bands by absolute edges** (90/97/103/110), not
  percentile — its labels speak in US-average units and most metros
  price below 100, so the percentile band rendered a false sentence.
  Registry judgment, same precedent as population.
- **`build.cube` now refreshes a same-data manifest in place**: the
  data_version hashes data files only (the manifest can't contain its
  own hash), so a registry display fix used to be silently discarded
  when the data was unchanged. Found because the first everyday-prices
  fix vanished exactly that way.
- **The slider info affordance opens on tap rather than toggling**: a
  toggle fights the hover-open on pointer devices (the click's own
  hover reopens, the toggle re-closes). Escape, blur and pointer-exit
  close; on touch, tapping elsewhere blurs.
- **No Recalculate button exists** (item 1 named one): results
  recompute on every panel change, so the affordance the requirement
  protects is panel-control reachability plus the chips-bar's Change
  search, both asserted.
- **The stress persona is excluded from the shift table** — it ranks
  only 9 metros on the full build, and a τ over 9 items is noise
  presented as measurement.
- **2c8d7285c720's cubes are retired** (manifest and metros.json kept),
  the same treatment dc236 and b4d99 received; `674aa70fc57c` stays
  intact.

Inherited and unchanged: deployment waits on the counsel review; the
hero photo slot waits on Nathan's asset; Phase 3's premise remains
raised in PHASE2C.md; POI union and religion stay deferred.
