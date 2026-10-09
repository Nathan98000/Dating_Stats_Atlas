# ADR 0004 — Balance is the sex ratio; race selects who's counted; margins keep working and stop rendering

**Status:** decided 2026-09-17 by Nathan (v3 boards + Phase 2c brief), implemented in
`m2.0.0`. Amends §5.3, §7.3, §10.4, D02 and D08; supersedes the v3 boards' own
"like for like" balance panel (StatesV3) and caption (HomeV3), which described an
intermediate definition the brief replaced. Second breaking contract change after
ADR 0003. **Amended 2026-09-29 (Phase 4c, Nathan's decision), implemented in
`m4.1.0`:** balance's second count is the other sex — the opposite of the sought
sex — not the seeker's own, and a same-sex search shows it (the last section).

## 1. Dating pool balance is the plain sex ratio

*[AMENDED in m4.1.0 (Phase 4c, the last section): the second count is the other
sex — the opposite of the sought sex — whoever is searching, and the same-sex
finding below no longer holds. Balance left the score in m3.0.0 (ADR 0009). The
text below stands as the m2.0.0 record.]*

    balance = count(sought sex, seeking.age range, marital selection)
            / count(seeker sex,  same age range,   same marital selection)

displayed as men per 100 women (or the mirror), **not** filtered by race, education
or income — deliberately. The `balance` pillar scores this same number, higher
better for the seeker; the UI displays it: one quantity, computed once, in
`scoring.rank`.

**Why.** The previous figure was pool ÷ rivals after every filter, which a reader
inevitably took as the city's sex ratio when it was nothing of the kind (the v2
board review said so in its own sticky note). Making it the actual sex ratio means
the name is true, the number is stable as filters move (asserted by test), and no
assumption about who competes with whom is baked in. The symmetric-rivals
apparatus — `rivals`, `ratio`, `ratio_moe`, the rival mask — leaves the serving
path entirely. Phase 1's rival code and findings stay in the pipeline and PHASE1.md
as history: they are how we know the crude ratio was biased.

**Age range:** `seeking.age` for both sexes — the simple, explainable choice. A
union with the seeker's own ±5 window was considered and rejected: it would make
the figure move when the seeker's age moves, which is exactly the instability the
redefinition removes.

**Separate gate.** Balance's two counts are whole age-by-sex slices, so they clear
the 100-effective-respondent bar almost everywhere even when the filtered pool does
not. Each quantity is gated on its own: the city page and the narrow-search state
still show balance when the pool has nothing to say.

**The same-sex finding (measured, then decided).** For a same-sex search the two
counts are the same count: the ratio is 1 by construction. Serving it would hand a
quarter of the model to a constant — caught when the rank-stability gate collapsed
to 0.05 on the same-sex persona, because a flat pillar left the top-10 boundary to
replicate noise. Balance is therefore **not applicable** to same-sex searches:
served unavailable with a plain note ("everyone is on both sides of the
comparison"), its weight redistributed by the existing missing-pillar policy.
Stability returned to 1.0. Never "100 men per 100 men".

**Measured consequence.** Against `m1.2.0` on identical requests (9 personas still
expressible): Kendall τ 0.28–0.86, top-10 overlap 5–9 of 10, median absolute rank
move 2–21 places, single cities moving as far as 94 places (Fort Collins, default
profile, #157→#63). Race-filtered personas move most — the old ratio compared a
race-filtered pool to race-blind rivals, so that is where the distortion was.
Recorded in `results/phase2c/ranking_shift_m1_2_0_to_m2_0_0.json`.

## 2. Race selects who lives in the city and matches — nothing more

A race or ethnicity filter changes the pool count only. It never touches balance,
and it carries no claim about who partners with whom: the interim cross-group
pairing rate is **retired from serving** (`features.yaml` `status: retired` with
the reason). `pairing_cells.parquet` and the couples linkage remain in the pipeline
— they are the foundation of Phase 3's kernel and cost real work — but the site
says nothing about marriage. This narrows §10.4/D02's counterweight decision to
what it protected: no claim without evidence; now, no claim at all.

**Two groups are always counted.** *[SUPERSEDED in m2.2.0 by ADR 0006:
the two groups became ordinary checkboxes — eight equal groups, the
selection is the filter, nothing added. The paragraph below stands as
the m2.0.0 record.]* "Two or more races" and "Another race" are ORed
into every race selection in `preferences.resolve_race_levels` — the model, not a
frontend — so the pool can exceed the sum of the six selectable groups; the panel's
one-line explanation says so and the reconciliation is tested. **Zero-of-six is
all-six**: an unticked panel means no race filter at all, never a pool quietly
shrunk to the two always-on categories. (All-six selected also means no filter —
the same set.)

## 3. Margins: the mechanism stays, the rendering stops

No margin of error, CV, interval, build id, model version, CBSA code, PUMA count or
permalink appears anywhere in the UI. The machinery is untouched: the API returns
`pool_moe` and `cv`, Gate 0's calibrated bound stays in the manifest and its
validation gate still runs, and the wording lives on as `TECHNICAL_STRINGS`
(returned by `/v1/meta`, rendered nowhere). Suppression is the only visible
expression of uncertainty — which is exactly why the n-gate has to keep working,
and why the methodology page keeps a plain-language account: every count comes from
a survey, we know how precise each one is, we leave a city out rather than show a
number we cannot stand behind, and the precise figures are available on request.

## 4. The smaller contract decisions

- **Marital** narrows to `never_married` / `previously_married` at the API ("Never
  married" / "Divorced or widowed" in the UI). The cube keeps its third level; no
  client can request currently-married people.
- **Scores** serve a rounded integer `score_display` beside the exact value; the
  meter fills to score/100, never rescaled to the visible range.
- **Sort** is `best_first` / `worst_first`, applied as a reversal of the same
  ranked array — same cities, same scores, same earned ranks, never widened to
  fill the bottom.
- **The city count** renders only when `counts.suppressed > 0`, with the StatesV3
  sentence; a heading never carries a zero, and nothing anywhere states "0 cities"
  or "0 people" (the NarrowV3/MetroV3 approved copy lives in `POLICY_STRINGS`).
- **Importance controls** (`pool_vs_balance` + Not much/Some/A lot) map to weights
  through registry constants server-side; "Not much" is a ×0.4 floor rather than
  zero (nothing showed zeroing a pillar leaves the ranking sane, and a floor keeps
  every stat's effect explainable). `size_vs_odds` stays accepted-but-deprecated
  for exactly this version.
- **Standing bands and the one-line city description** are computed at build time
  (tertiles across all 387 cities; a formulaic template over population, state,
  student share and the nearest larger metro), with thresholds, labels, tones and
  the template in the registry. The wireframe placed bands by judgement and said
  so; the shipped page reads the build.

## What supersedes what

| This ADR | Supersedes |
|---|---|
| balance = plain sex ratio, rivals retired | §7.3's rival window as a served quantity; §5.3's ratio row; the v3 boards' like-for-like panel |
| race = pool filter only, pairing retired from serving | §10.4's counterweight display; D02's "always show the counterweight" |
| margins hidden, mechanism kept | §5.3's "margin in the row" display rule (the *computation* discipline stands) |
| n-only suppression unchanged | D08 as already amended by ADR 0002 |

Phase 3's premise changed with this record: the assortative kernel was scoped to
replace the crude rival window, and rivals no longer exist in the model. The
couples linkage still has uses; the decision on Phase 3's shape is Nathan's and is
raised, not resolved, in PHASE2C.md.

## Amended in Phase 4c (2026-09-29): the sought sex per 100 of the other sex, on every search

This amendment is **Nathan's decision** (the Phase 4c brief). Dating pool balance
is now

    balance = count(sought sex,     seeking.age range, marital selection)
            / count(the other sex,  same age range,    same marital selection)

where the other sex is the opposite of the sought sex, **whoever is searching**. It
is still shown per 100, still counts single people before any race, education or
income filter, and is still gated on its own two counts: where either falls short
of the 100-effective-respondent bar the row says so (`balance_unavailable`).

- **An opposite-sex search is unchanged.** There the other sex is the visitor's
  own, so the figure is the one §1 defined: every opposite-sex balance block, over
  all 518 ADR 0011 test searches and every "about you" variant, is byte-identical
  to m4.0.0's (`results/phase4c/served_numbers_check.json`).
- **A same-sex search shows the figure an opposite-sex search for the same people
  shows.** A man seeking men 27–38 sees "N men per 100 women" — on the real build,
  124 in San Francisco, 113 in New York. m4.0.0 took the second count from the
  seeker's own sex, so a same-sex search counted the same people twice (a ratio of
  1 by construction) and was served "not applicable" with the note
  `balance_same_sex`. §1's same-sex finding was about a **scored** pillar — a
  constant pillar handed the top-10 boundary to replicate noise — and balance has
  been displayed and not scored since m3.0.0 (ADR 0009); under the new definition
  the two sides are never the same people, so "100 men per 100 men" cannot arise.
  Same-sex visitors can ignore the figure; it shows the gender balance of the
  singles in the ages they picked.
- **Balance no longer depends on the visitor**, so `/v1/rank` sends it once per
  search (`variants.balance`) instead of once per own sex (`variants.by_sex`, ADR
  0018 §4), and the response is smaller for it; `balance_applies` is gone (balance
  applies to every search), and the policy string `balance_same_sex` ("…so balance
  doesn’t apply…") is retired, with every display of it: the note under the
  panel's slider, the home page footnote's same-sex alternative (the footnote is
  always `balance_caption`) and the tally's note.
- **Nothing scored reads it.** Every score and rank is identical for every test
  search, same-sex included, and the ADR 0011 gate reads 1.0 against the m4.0.0
  reference. The golden fixture's same-sex vector gains its balance figures, so
  MODEL_VERSION moves to m4.1.0 (the `versions.py` convention); the build keeps its
  id, 5b780e4f2444, with its manifest refreshed.
- **After the report** (Nathan's calls, 2026-09-29): he confirmed the retirement of
  `balance_same_sex`, and About us loses its sentence "In a same-sex search everyone
  is on both sides of the comparison, so balance doesn't apply." — removed, not
  rewritten, on his decision. The paragraph before it already reads true for both
  kinds of search.

## Amended in Phase 6 (9 October 2026): the same-sex captions, spoken figures and the flags shown again

DRAFT for Nathan's approval (Phase 6; his decisions 2, 3 and 8).

- **Same-sex searches get a note where matches show** (F01). On a same-sex search the count is
  every single person of the sought sex in the ages picked; the Census doesn't ask who people
  date. The registry's `same_sex_pool_note` says so under the results header, under the matches
  line on the city page's score card and under Compare's Matches row, chosen in the browser from
  the stored own sex (nothing about the visitor reaches the server). Balance gets its own caption
  on a same-sex search, `balance_caption_same_sex` ("…it describes the city, not your matches"),
  in the tile's box and the page footnote; `balance_same_sex` stays retired. A same-sex share of
  the pool is a model question for later, not part of this amendment.
- **Spoken figures** (F09). The who-lives-here card rounded the population and the adults to
  different steps, so Abilene read "200,000 people, of whom 100,000 are adults" for 183,310, and
  68 of 387 metros were off by 10% or more. Since m4.3.0 one function (`model/spoken.py`) speaks
  every population figure: 2 significant figures below 950,000, "N.N million" above, and a metro
  outside the ranked set never reads at or above the registry's `population_floor` (250,000) — a
  figure that would round up to it rounds down to the next 2-figure step. The build's validation
  gains a hard gate: every figure within 5% of its value, none at or above the floor for an
  unranked metro, card or description. The city descriptions use the same function, but
  regenerating them changes the build's data files, so that waits on Nathan (PHASE6.md).
- **The caution flags come back** (F08). Phase 2b showed the served `flags` as chips; a later
  commit removed them without a record. The served policy strings (`gq_flag`,
  `low_allocation_purity`) show again as one caption line per flag at the top of a row's or a
  card's detail and under the matches line on the city page. They are the existing strings,
  unchanged; what renders is all that moves.
