# ADR 0004 — Balance is the sex ratio; race selects who's counted; margins keep working and stop rendering

**Status:** decided 2026-09-17 by Nathan (v3 boards + Phase 2c brief), implemented in
`m2.0.0`. Amends §5.3, §7.3, §10.4, D02 and D08; supersedes the v3 boards' own
"like for like" balance panel (StatesV3) and caption (HomeV3), which described an
intermediate definition the brief replaced. Second breaking contract change after
ADR 0003.

## 1. Dating pool balance is the plain sex ratio

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
