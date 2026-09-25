# ADR 0013 — Chances of matching is scored by its value, not its rank, with extreme cities held in

Date: 2026-09-24 (Phase 3d, B1; committed before any candidate was measured —
the commit order is the proof that the rule was not fitted to its results)
Status: accepted (the choice among the candidates, or that none ships, is
recorded in PHASE3D.md and in the amendment below once measured)

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

## The selection rule

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
