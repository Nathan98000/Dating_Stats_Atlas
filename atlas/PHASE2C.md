# Phase 2c — balance becomes the sex ratio, and the site becomes v3

Build `2c8d7285c720` · model `m2.0.0` · schema `cube-v1` (unchanged).
Reproduce: `build.descriptions` → `build.cube` →
`tests/golden/make_fixture.py <build>` → `pytest atlas` →
`build.validate <build>` → `cd atlas/web && npm ci && npm test &&
npx playwright test`.

**All six acceptance gates hold.** (1) Dating pool balance is the plain
sex ratio of item 1 — computed once in `scoring.rank`, scored by the
`balance` pillar, displayed by the tally rows: one quantity, one place,
asserted end-to-end (its masks carry only sex, the seeking ages and the
marital selection, and a test pins that the displayed figure does not move
when race, education or income filters move). (2) No user-facing string
contains the banned vocabulary — now including "odds" — or a margin, CV,
build id, model version, CBSA code, PUMA count or permalink: the registry
assertion covers policy strings, the legend, descriptions and every
composed line (1,287 checked as a hard gate), and an e2e sweep patrols all
six page shapes (it caught the methodology page printing its own version,
which is exactly the kind of thing it exists to catch). (3) The city count
appears only when at least one city is excluded, with the StatesV3
sentence; sort reverses the same ranked array with membership and earned
ranks intact, asserted through the UI. (4) Every figure on the city page
comes from the API: the one-line description and the standing bands ship
in the artifact, cards arrive with server-composed values, unit lines,
band labels and tones. (5) WCAG 2.1 AA on the new palette: axe reports
**zero serious or critical violations** on home, results, city and
narrow-search, and the two-handle age control is fully keyboard-operable
with separately labelled handles that meet but never cross. (6) Goldens
regenerated under `m2.0.0` with the commit note; the cube-vs-SQL
differential — now three-legged, covering both balance counts — agrees
with SQL to **2.0×10⁻⁷** worst-case, and all six Phase 2b hard gates pass
on this build.

## What moved in the numbers — the headline

Re-ranking the m1.2.0 personas under identical requests (9 of 13 still
expressible; the others used currently-married or a now-always-counted
race group): **Kendall τ 0.28–0.86, top-10 overlap 5–9 of 10, median
absolute rank move 2–21 places**. On the default profile (τ 0.79, 8/10
top-10 kept), Fort Collins climbs 94 places (#157→#63), Davenport falls
71, and the Michigan college metros rise 50–70 — cities whose singles
scenes are numerically balanced but whose old pool÷rivals figure was
dragged by the filtered competition definition. **Race-filtered personas
move most** (τ down to 0.28): the old ratio compared a race-filtered pool
to race-blind rivals, so that is exactly where the old figure distorted
most. A reader of the old site will see different lists; that is the
redefinition doing what it says, and the full table is in
`results/phase2c/ranking_shift_m1_2_0_to_m2_0_0.json`.

Rank stability under the new definition is *better* than m1.2.0's: 0.99–
1.0 across all eleven evaluable personas (was 0.875 floor) — whole
age-by-sex slices carry far less replicate noise than the filtered ratio
did.

## The same-sex finding (a gate did its job)

The first m2.0.0 validation run failed rank stability at **0.05** on the
same-sex persona. Diagnosis: for a same-sex search the two balance counts
are the same count — the ratio is 1 by construction — so a quarter of the
model became a constant and the top-10 boundary (scores 0.1–0.5 points
apart) fell to replicate noise. Decision, recorded in ADR 0004: **balance
is not applicable to same-sex searches.** It serves unavailable with a
plain note ("everyone is on both sides of the comparison"), its weight
redistributes by the existing missing-pillar policy, and the slider
carries the note on the panel. Stability: 1.0. The site never says
"100 men per 100 men".

## Race, marital, and what serving stopped saying

Race filters select who lives in a city and matches — the interim
cross-group pairing rate left the response, the UI and the registry's
active set (`status: retired`, reason attached); `pairing_cells.parquet`
and the couples linkage stay in the pipeline for Phase 3. "Two or more
races" and "Another race" are ORed into every selection inside
`preferences.resolve_race_levels` — the model, not the frontend — with
zero-of-six meaning no filter at all; the SQL mirrors in the validation
suite apply the identical rule, and the panel's approved one-liner
explains why a filtered pool can exceed the ticked groups. Marital narrows
to never/previously at the API; the cube keeps its third level untouched.

Margins: **the mechanism stays, the rendering stops.** `pool_moe` and `cv`
are still computed and returned on every ranked row (asserted), Gate 0's
bound and its validation gate are untouched, and the wording lives on
under `technical_strings`. Suppression is the only visible expression of
uncertainty, which is why its gate keeps running; the how-it-works page
says all of this in plain language, including that precise figures are
available on request.

## The v3 site

Four screens to the boards: **home** (hero slot with the labelled
placeholder — the asset is Nathan's to drop at `web/public/hero.jpg`,
~2560×680, wide crop, faces small; the component never sources an image),
the whole scoring model in one panel with no hidden defaults, and results
rows — rank numeral, the pool figure large, the API-composed movers line,
the balance tallies in the male/female hues, a whole-number score over a
meter filled to score/100. **Results states** per StatesV3: "Cities for
you" with no number until something is excluded, then "59 cities for you"
plus the approved sentence; Show: Best first / Worst first as a pure
reversal. **City pages** route by slug, open on the built description
(Provo renders the board's exact line), a locator map whose 387
real-coordinate dots draw the country themselves, the for-your-search
card or the approved hard-to-answer card with one-click wideners — and
balance still rendering underneath on its own gate when the pool has
nothing to say. **Narrow search** is NarrowV3 verbatim from the policy
strings: the shape of the problem, three wideners that each restate the
loosened query, and the plain statement that too few matches in the
survey is not too few people in the country. No zero, no count of people,
anywhere. The compare page (ADR 0003) survives in the new system, still
rendered from one response.

Importance controls send `{pool_vs_balance, importance:{cost,reach,
lifestyle}}`; the registry owns the level table (`not_much: ×0.4, some:
×1.0, a_lot: ×2.0`) and the renormalisation. "Not much" is a floor, not
zero — nothing showed zeroing a pillar leaves the ranking sane, and a
floor keeps every stat's effect explainable. Neutral settings reproduce
the registry defaults exactly (tested); `size_vs_odds` stays accepted-but-
deprecated for exactly this version.

## Deviations ledger (with reasons)

- **The boards' "like for like" balance copy is superseded** (StatesV3's
  explainer panel, HomeV3's caption and tally suffix): the brief's item 1
  post-dates the canvas and defines the plain ratio instead; ADR 0004
  records the supersession, and the shipped captions describe what is
  actually computed.
- **Same-sex searches get "balance doesn't apply"** rather than a
  constant — found by the stability gate, decided in the ADR.
- **Population bands use absolute registry edges (500k/2M), not
  tertiles**: most metros are small, so tertiles called 717k Provo "one
  of the biggest cities"; the board's "mid-sized" instinct was right for
  this one stat. Its card also speaks survey-honest rounding ("700,000
  people, of whom 460,000 are adults"), never person-precision.
- **Provo's rent band reads "Pricier than most cities"** where the board
  mocked "Cheaper" — the board's own sticky said bands were placed by
  judgement and illustrative; the shipped page reads the build, and
  $1,534 genuinely sits in the top tertile of the 387.
- **The board's clay label colour fails AA on white (4.1:1)**: `--poor`
  darkened to `#B0543E` (5.0:1). The students card keeps the board's
  neutral tone in every band (a heavy student presence is a character,
  not a virtue).
- **The income select offers all six survey steps**, not the three the
  wireframe mocked in its closed dropdown — controls offer only what the
  cube can answer, and all six are answerable.
- **"Some college" left the education control** (the boards offer
  Any/College degree/Graduate degree); the API still accepts it.
- **The compare page's difference column** remains the one deliberate
  piece of client arithmetic (ADR 0003), static stats only; population
  and balance never get a difference.
- **The e2e stack builds into its own dist dir** after a CI-style run
  clobbered the live dev server's `.next` mid-session.

## Accessibility audit result

axe-core (WCAG 2.1 A + AA) on home, narrowed results, the city page and
the narrow-search state: **0 serious, 0 critical** (initial run: two real
findings — `ink-3` on the tint surface at 4.35:1 and the clay token at
4.08:1 — both fixed at the token level). The two-handle age control:
each handle separately labelled ("Youngest age" / "Oldest age"), both
tab-reachable in order, arrows move one year, handles meet but never
cross, focus ring visible — all asserted by e2e, plus a keyboard path
through the whole panel. Reduced motion respected; the mobile layout
stacks the panel above results.

## Timings

| what | measured |
|---|---|
| time to first results (production, real artifact, 7 cold runs) | median **237 ms**, max 359 ms (budget 2 s) |
| `/v1/rank`, 400 mixed m2.0.0 queries | p50 29.5 / p95 42.7 / p99 50.4 ms (target p95 < 60) — the two balance masks add ~9 ms of gemv per request |
| pytest (38) + vitest (14) | 1.9 s + 0.2 s |
| Playwright e2e, 24 specs, hermetic | 21 s (+ ~40 s Next build in CI) |
| full validation suite | ~4 min (differential now 3 SQL legs per shape) |
| artifact | 339 MB; search index 35.6 KB |

Screenshots of the four screens (plus the results-with-count state and
the city cards) are in `results/phase2c/*.png`.

## Open item raised, not resolved: Phase 3's premise

Phase 3's assortative kernel was scoped to **replace the crude rival
window — and rivals no longer exist in the model.** The couples linkage
that survives in the pipeline (pairing cells, dictionary-asserted
RELSHIPP links, the Pew reference table) still has real uses: age-gap and
education-gap description on city pages, cross-group pairing content if
the product ever wants it back, and the Pew-reproduction validation that
was to be the phase's gate. But the phase as written no longer has a
serving-path consumer. Whether Phase 3 becomes a descriptive layer
(couples content on city pages), an input to a future balance refinement,
or is re-scoped entirely is Nathan's call; nothing in m2.0.0 blocks any
of the three.

Other inherited items, unchanged: the POI union (registry `deferred`),
the build-time narratives (the formulaic city description is explicitly
their placeholder), religion (Phase 4), and deployment behind the counsel
review — the runbook and configs from Phase 2b remain current, with the
smoke-check routes updated to the v3 paths.
