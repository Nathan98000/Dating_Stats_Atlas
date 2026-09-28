# ADR 0013 — Chances of matching is scored by its value, not its rank, with extreme cities held in

Date: 2026-09-24 (Phase 3d, B1; committed before any candidate was measured —
the commit order is the proof that the rule was not fitted to its results)
Status: accepted (the choice among the candidates, or that none ships, is
recorded in PHASE3D.md and in the amendment below once measured); amended
25 September 2026 after Phase 3d — the selection rule's match-end margin,
committed after the measurement and saying so (the last section)

## The finding it answers

Every intensive feature, chances of matching included, enters the score
as a percentile rank across the query's ranked set (`scoring.
score_components`, `_pct_rank`). A percentile rank gives neighbouring
cities the same step — about 0.5 points across 193 cities — whether
their index values are 0.1 or 10 apart. The match index is a survey
estimate whose replicate noise is about as large as the gaps between
cities near tenth place, so small random moves flip their order at full
weight. The searches at the slider's match end are the site's shakiest:
2.49 → 2.88 places of wobble in m3.3.0 (PHASE3C.md §4; Phase 3's finding
2), against a median of 0.46 across the 516 test searches.

## Nathan's decision

Score the figure by its value, so that near-ties get near-equal scores
and a large real lead counts as large, with extreme outlier cities
handled so that no single city can swamp the rest.

## What is measured, not assumed

Value scoring spaces cities by their real gaps. That calms the bunched
middle of the distribution, but it can make the sparser top more
sensitive, and the top 10 lives at the top. The effect could go either
way. The rule below decides by measurement and ships nothing if nothing
helps.

## The candidates

Each candidate works on x = ln(index ÷ 100): 2× and ½× the national
average sit equally far from it, and the log is the first layer of
outlier handling, since it compresses very large values. Each is computed
per request across the ranked set, as today's normalisation is, and then
min-max scaled to 0–100. A one-city set, or cities that are all
identical, get 50. A missing value stays missing.

| Candidate | Outlier handling before the min-max |
|---|---|
| **N0** (control) | Today's percentile rank. Must reproduce the Part A build bit-identically. |
| **V1**, like pool size | Winsorize x at the ranked set's 1st and 99th percentiles (the registry's `winsor_percentiles`). |
| **V2**, fences | Clip x to [Q1 − 1.5·IQR, Q3 + 1.5·IQR] of the ranked set. |
| **V3**, fixed cap | Clip the index to [40, 250] before the log. |

V3's 250 matches the display cap but is its own registry constant
(`normalization.match_value_cap`); the display cap stays presentational
and `test_match_display_cap_is_presentational` passes unchanged. 40 is
250's mirror in log space. Every parameter lives in the registry's
`normalization` block (`match_scoring`, `match_value_cap`,
`match_fence_iqr`, `winsor_percentiles`) and travels in the manifest.

## The outlier condition

On every test search, at both the searches' own slider positions and the
match end, the middle 80% of ranked cities keep at least **40 points** of
match-score spread (10th to 90th percentile of the feature's normalised
value). That is half of what percentile ranking gives, so no outlier can
squeeze the field. A candidate that fails on any search does not qualify;
its worst searches are reported.

## The match-end set

Every ADR 0011 test search that does not send explicit `weights`, re-sent
with `pool_vs_match` = 1.0. Wobble is ADR 0011's definition. This set is
a diagnostic for this choice only; the gate's own test set does not
change.

## The selection rule (as drafted; amended after Phase 3d — the last section)

A candidate qualifies if it meets all three conditions:

1. it passes the ADR 0011 gate against the m3.2.0 reference;
2. it meets the outlier condition;
3. its total wobble over the match-end set is lower than N0's on the
   same kernel.

Of the candidates that qualify, the one with the lowest match-end total
ships; a tie goes to the earlier candidate in the table. If none
qualifies, Part B ships nothing.

**On the gate.** A scoring-only change leaves every search's index and
replicate hashes unchanged, so ADR 0011's rule reads the totals over all
searches ("nothing touched"). That is the gate working as written; it is
not changed. `stability_gate.py` scores through `scoring.score_vector`,
so it picks the candidate up from the same function the engine uses; a
test asserts that rather than keeping a copy.

## What does not change

The served index and its display cap; suppression; bands and standing
(the display percentile); the kernel; every other feature's percentile
rank; the slider default, the pillar weights and the importance levels.
Only the match feature's normalised value changes.

## Consequences

`scoring.match_normalised` (the four candidates, switched by the
registry's `normalization.match_scoring`, N0 the default until a winner
is chosen), the registry block and its manifest copy, `pipeline/build/
match_scoring_candidates.py` (the measurement), the unit tests of the
transform and of N0's bit-identity, ADR 0009 §8 amended (its "the
feature is percentile-ranked" reason), and PHASE3D.md's Part B. Whether
to re-base the ADR 0011 reference after this change is Nathan's call,
recorded in an ADR if he makes it.

## Amended, 25 September 2026 (Phase 3d B2 and B3): measured on m3.4.0, V2 ships as m3.5.0

The four candidates were measured on the m3.4.0 build (1ebeaa2dcad6)
after the rule above was committed (3e21195; the measurement
`results/phase3d/b2_candidates.json`, the per-search records
`b2_gate_<rule>.json` and `b2_matchend_<rule>.json`):

| Candidate | ADR 0011 gate | Match-end wobble, total | Gate-set wobble, total | Outlier condition (worst spread, searches below 40) | Steering τ, median, own slider / match end | Qualifies |
|---|---|---|---|---|---|---|
| N0, the percentile rank | pass 0.970 | 1,100.0 | 306.7 | pass (80.0; 0) | 0.508 / 0.834 | control |
| V1, winsorized 1st/99th | pass 0.754 | 1,011.5 | 238.4 | fails (30.2; 30) | 0.413 / 0.753 | no |
| V2, the Tukey fences | pass 0.775 | 1,025.2 | 245.1 | pass (41.8; 0) | 0.407 / 0.756 | **yes — ships** |
| V3, the index clipped to [40, 250] | pass 0.719 | 999.8 | 227.4 | fails (23.5; 57) | 0.433 / 0.756 | no |

Every value candidate passes the gate and wobbles less than N0 at the
match end; the outlier condition decides. V3 and V1 have the lowest
match-end totals but squeeze the middle 80% of ranked cities below 40
points of match-score spread on searches whose ranked set holds a run of
far-out cities (V3 on fifty-seven searches, the worst 23.5 points, women
of 50 of two or more races; V1 on thirty, the worst 30.2, the American
Indian or Alaska Native woman of 25). V2's fences follow each search's
own quartiles and keep 41.8 points on its worst search (a man of 40 with
high school or less, of two or more races). V2 is the one candidate that
meets all three conditions; the tie clause was not needed. **V2 ships as
m3.5.0**: `normalization.match_scoring: V2` in the registry, the build's
manifest refreshed in place (the data files are unchanged, so the build
keeps its id, 1ebeaa2dcad6), goldens regenerated; ten of ten hard gates,
the ADR 0011 gate 0.775 against the m3.2.0 reference (total wobble 316.2
→ 245.1, the median search 0.457 → 0.364; the old overlap reading 0.7375,
the two match-end personas, would fail at the 0.80 bar and is reported
as the soft reading it is); latency p95 35.3 ms at a one-minute load of
2.46. Against m3.4.0 the served index is unchanged on every search (the
index and replicate hashes match search for search), 342 of 516 test
searches are steadier and 174 shakier (95 rose more than 25%, named in
PHASE3D.md §3); the default search's ranking moves a median 3 places
(Kendall τ 0.938; Washington DC replaces San Jose at 10th) and the
same-sex reference search's 5 (τ 0.867). The match-end searches read
2.90 → 3.37 places of wobble on the gate's own set — they are the
shakiest on the site under either rule, and at their own slider position
the match-end persona is where V2's reordering of the near-tied middle
shows most.

**The reference is not moved.** The new build's total wobble sits far
below m3.2.0's (245.1 against 316.2, 0.775), and below every kernel
build so far (m3.3.0 0.971, m3.4.0 0.970). Whether to re-base the ADR
0011 reference on m3.5.0 is Nathan's call, recorded in an ADR if he
makes it; until then every later change is read against m3.2.0 as the
rule says, with 22.5% of headroom that value scoring, not the kernel,
created.

## Amended after Phase 3d: the match-end margin

25 September 2026, Nathan's call after reading PHASE3D.md. It amends the
selection rule above. The candidates, the outlier condition, the
match-end set and the outcome are unchanged. Every number here is read
from `results/phase3d/b2_selection_with_margin.json`, written by
`results/phase3d/b2_selection_with_margin.py`, except the B3 readings
Nathan cites, which are `b3_ship_check.json`'s. That script reads the
stored B2 records (`b2_candidates.json`) through the same function the
measurement calls and re-measures nothing.

**The rule**, in Nathan's words:

> **A difference in match-end wobble smaller than 5% of N0's total is no
> difference.**
>
> 1. **Qualifies.** A candidate qualifies if it meets all three
>    conditions:
>    1. it passes the ADR 0011 gate (unchanged);
>    2. it meets the outlier condition (unchanged);
>    3. its total wobble over the match-end set is **at least 5% below
>       N0's** on the same kernel.
> 2. **Choosing.** Of the qualifying candidates, find the lowest
>    match-end total. Every qualifying candidate within 5% of N0's total
>    of that lowest one is tied for first. Of those, the one with the lower
>    total wobble over the gate's own set ships. An exact tie goes to the
>    earlier candidate in the table.
> 3. **None qualifies.** If none qualifies, nothing ships.

At exactly 5% the difference counts, as the first sentence says. A
candidate exactly 5% below N0 qualifies, and a qualifying candidate
exactly 5% of N0's total above the lowest is not tied with it.

**When it was set, and what the record can show.** Nathan decided on
the 5% margin before any Part B candidate was measured. The copy of
`PHASE3D_RESUME_PROMPT.md` that reached the repo was missing the section
that set it, because of an error in preparing the brief, not in the
work. That copy named a margin, both in Nathan's decisions and in B1's
place in the commit order ("Part B's rule, including its new margin"),
but gave no rule for it, and its Part B section kept the drafted rule.
ADR 0014, committed before any candidate was measured (f38dc40), also
names the margin without a value: "That selection has its own margin, set
in ADR 0013." So the margin was not in the B1 commit (3e21195), and B2 ran
under the rule as drafted. **Because the margin is committed now, after
the measurement, the commit order cannot prove that it came first.**
Neither of the two earlier mentions names 5%, so they cannot prove it
either. The record of Nathan's decision is the brief as he wrote it, not
the repository.

**Why 5%** (`anchors`):

- **Ordinary movement is about 1% or less.** Changes that leave the
  scoring alone moved wobble totals by that much:
  - finishing the fit (m3.3.0 → m3.4.0) moved the gate-set total by
    0.14% (307.13 → 306.70);
  - it moved the two match-end searches by 0.7% (2.878 → 2.899);
  - the C1 and C3 candidates' gate-set totals differ by 0.6% (306.70
    against 308.50).

  5% is 6.8 times the largest of these.
- **Half the gate's line.** 5% is half the rise the ADR 0011 gate treats
  as material (10%).
- **A third of the problem.** 5% is about a third (0.32) of the
  match-end rise Part B was meant to undo: 2.494 → 2.878 places from
  m3.2.0 to m3.3.0, +15.4%.
- **Visible benefit.** Below 5%, a change to how every search is scored
  would move every ranking for a difference no visitor could see.

**The outcome is unchanged.** The margin is 55.0 places of N0's
match-end total of 1,100.0.

| Candidate | Match-end total | Below N0 | At least 5% below | Gate | Outlier condition | Qualifies |
|---|---|---|---|---|---|---|
| N0, the control | 1,100.0 | — | — | pass | pass | never |
| V1 | 1,011.5 | 8.0% | yes | pass | **fails** (30.2) | no |
| V2 | 1,025.2 | **6.8%** | yes | pass | pass (41.8) | **yes** |
| V3 | 999.8 | 9.1% | yes | pass | **fails** (23.5) | no |

- V2 cuts the match-end total by 6.8% (1,100.0 → 1,025.2), past the
  margin.
- V1 and V3 clear the margin too but still fail the outlier condition.
- One candidate qualifies, so there is no tie band. V2 ships.
- The rule as drafted read the same records the same way: qualifying V2,
  ships V2.

**Nathan keeps V2.** He has read the B2 and B3 results, including:

- the two match-end searches rising from 2.90 to 3.37 places;
- the 95 searches whose wobble rose more than 25%;
- V2's narrow pass of the outlier condition (41.8 points against 40).

m3.5.0 stands as built, and nothing served changes.

**Future re-runs.** The margin governs any future re-run of this
selection:

- `MATCH_END_MARGIN = 0.05` sits beside `OUTLIER_MIN_SPREAD` in
  `pipeline/build/match_scoring_candidates.py`;
- qualification and the winner are one pure function, `select`, which
  `main` calls;
- its unit tests are in `pipeline/tests/test_match_scoring_selection.py`.

