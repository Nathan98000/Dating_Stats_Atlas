# Phase 3b — Part A settles Phase 3 (m3.1.0); Part B sharpens the kernel (m3.2.0)

Part A: build **ae1efbef9f0e**, model **m3.1.0** (ADR 0009 amended §2, §4,
§8). Suites at close of Part A: **49 pytest, 52 vitest, 77 Playwright**.
Validation battery: **nine of nine hard gates pass**, rank stability among
them (finding 2 of PHASE3.md, settled below). Every number here is read
from `results/phase3b/` (or the validation report it names); nothing was
recomputed for this document. Part B follows in its own sections and its
own commit (m3.2.0).

## 1. The half-life table (A1)

Nathan's decision on finding 2: widen the window and decay by time, the
half-life chosen **by the standing rank-stability gate, shortest first**.
The machinery and the fitted samples were Phase 3's; the sweep
(`stability_sweep.py`) refits the national kernel on each candidate with
its Phase 3 bandwidth and shrunk dials, loads it into the m3.0.0 build
in memory in place of the shipped kernel, and runs the validation
suite's own `rank_stability()` over all eighteen personas
(`results/phase3b/stability_sweep.json`). Recent-only is the baseline
that failed and never ships; five years was tried first and every
persona reached the bar, so ten and twenty years were not fitted — the
rule stops at the first pass.

| Candidate | Half-life | Kish couple-sides | Allocated sides | Race cells empty / < 30 effective | Replicate sd of the index, median / p90 (median over personas) | Personas below 0.80 | Minimum share | Gate | Pew corrected median (not the criterion) |
|---|---|---|---|---|---|---|---|---|---|
| recent | recent unions only (m3.0.0) | 535,834 | 986,770 | 2 / 31 | 2.86 / 4.57 | 3 (D_man41_women_50k, slider_all_match, slider_alias_pool_vs_balance) | 0.700 | FAILS | 2.63 |
| **decay_h5 — ships** | 5 years | 974,834 | 1,385,259 | 0 / 19 | 2.82 / 4.59 | 0 | 0.950 | passes | 2.48 |

**The Pew number was not the selection criterion.** Phase 3 established
that the Pew sweep is confounded — Pew's newlyweds are unions of
2011–2015, exactly what longer half-lives add back — so the 2.48 for the
shipped sample is reported here beside the 2.63 it replaces and nothing
was chosen by it (§2 has the re-run).

**The root-cause metric did not move, and the report says so.** The
index's replicate standard deviation — Phase 3's diagnosis of the
failure — is 2.82 index points at the median across personas under the
five-year kernel against 2.86 under recent-only; for the persona that
failed worst it is 4.05 against 4.1, and at the slider's match end 2.01
against 2.0. That is what the number is: survey noise in the metro's
own pool under a fixed kernel (the replicate weights move, the kernel
does not), which no fitting sample can reduce. The gate passes because
the five-year kernel changes *where* the index gaps fall: the scores at
ranks 7–14 span 3.6 points at the match end instead of 2.0, so the
top-10 boundary is less bunched and the same noise flips it less often.
A pass under the stated rule, recorded with the mechanism rather than
the diagnosis it was expected to confirm.

The eighteen personas, m3.0.0 beside m3.1.0 (the three failures in bold):

| Persona | m3.0.0 recent: share | sd median / p90 | span of scores, ranks 7–14 | 5-year: share | sd median / p90 | span 7–14 |
|---|---|---|---|---|---|---|
| A_woman32_ba_men_75k | 1.0000 | 2.73 / 4.21 | 4.4 | 0.9875 | 2.69 / 4.18 | 4.1 |
| B_man28_women_never | 1.0000 | 2.12 / 3.34 | 6.1 | 1.0000 | 2.1 / 3.35 | 6.3 |
| C_woman38_grad_men_100k | 1.0000 | 3.51 / 5.38 | 7.4 | 0.9750 | 3.37 / 5.35 | 8.3 |
| D_man41_women_50k | **0.7125** | 4.1 / 6.76 | 1.2 | 0.9500 | 4.05 / 6.7 | 1.3 |
| E_black_woman29_stress | only 4 ranked | — | — | only 4 ranked | — | — |
| race_asian_nh_men | 1.0000 | 2.8 / 4.59 | 8.3 | 1.0000 | 2.79 / 4.63 | 8.3 |
| race_hispanic_women | 0.9750 | 2.92 / 4.67 | 5.3 | 0.9875 | 2.93 / 4.71 | 4.8 |
| race_white_nh_grad_multi | 1.0000 | 4.12 / 6.06 | 10.9 | 0.9625 | 4.1 / 5.95 | 10.4 |
| below_bar_nhpi_250k | only 0 ranked | — | — | only 0 ranked | — | — |
| race_two_or_more_and_other | 1.0000 | 4.54 / 6.91 | 9.4 | 1.0000 | 4.59 / 7.08 | 10.1 |
| broad_any | 1.0000 | 2.76 / 4.06 | 4.2 | 1.0000 | 2.75 / 4.13 | 4.9 |
| slider_all_match | **0.7000** | 2.0 / 3.1 | 2.0 | 0.9625 | 2.01 / 3.14 | 3.6 |
| slider_alias_pool_vs_balance | **0.7000** | 2.0 / 3.1 | 2.0 | 0.9625 | 2.01 / 3.14 | 3.6 |
| self_edu_and_race | 1.0000 | 7.1 / 15.56 | 3.8 | 1.0000 | 7.64 / 16.97 | 3.8 |
| self_edu_only_hs | 1.0000 | 2.88 / 4.35 | 3.4 | 1.0000 | 2.85 / 4.39 | 3.3 |
| importance_controls | 1.0000 | 2.71 / 3.97 | 4.4 | 0.9875 | 2.76 / 4.05 | 4.5 |
| importance_lifestyle_alias | 1.0000 | 2.84 / 4.55 | 6.4 | 1.0000 | 2.79 / 4.55 | 6.8 |
| same_sex_pool | 1.0000 | 3.42 / 5.11 | 6.1 | 1.0000 | 3.49 / 5.18 | 4.7 |

The baseline row reproduces the m3.0.0 validation report exactly (0.7125
/ 0.70 / 0.70 on the same three personas), which is the check that the
sweep runs the gate and not a copy of it. Two personas are skipped by
the gate's own rule (fewer than twelve ranked metros), as in m3.0.0.

**The shipped sample.** Every union weighted 0.5^((survey year − year
last married) / 5), unmarried partners at weight 1 (they carry no
formation year in PUMS): 1,385,259 allocated couple-sides, Kish 974,834,
national out-group share 22.0% (recent-only: 23.9%), the smallest
metro's Kish sides 162 (recent-only: 105), no empty race cell and 19
race cells under 30 effective sides (recent-only: 2 and 31). The IPF
converged (7 raw iterations plus 2 after the age term was fixed, final
change 1e-7), the cross-validated bandwidth is again 0.25 years for
both sexes, face validity passes, and all three components keep their
dials under the Phase 3 rule (held-out gain over the national kernel
+2.03 / +0.64 / +5.64 per 1,000 weighted sides for age / education /
race, better in 258 / 204 / 254 of 387 metros; shrinkage centre 0.997 /
0.967 / 0.915; the most heavily shrunk component is still education,
prior share median 0.56).

## 2. The battery (nine of nine) and the Pew re-run (A2)

`validate.py` on build ae1efbef9f0e (`results/phase3b/validation_report_m3_1_0.json`):

| Hard gate | m3.0.0 (59fd352c5c2f) | m3.1.0 (ae1efbef9f0e) |
|---|---|---|
| Interval calibration | pass | pass — coverage 0.975, median overstatement 0.234 |
| Suppression reasons and intervals | pass | pass |
| Cube-vs-SQL differential (40 shapes, kernel-weighted sum both ways) | pass, worst 2e-7 | pass, worst relative error 1.98e-7 |
| **Rank stability** | **FAIL** — 0.7125, 0.70, 0.70 on three personas | **pass** — minimum 0.95 (D_man41 0.95; the two slider personas 0.9625; every other persona ≥ 0.9625) |
| Explanation invariants | pass | pass — 2,065 explanations, zero banned terms, lead phrase position-unique |
| Kernel face validity | pass | pass — the 30-year-old's multiplier peaks at 30 for both sexes, education diagonal-dominant, every own-group race multiplier above its off-diagonals |
| Adversarial artifacts | pass | pass — no watchlist metro in any top-10 |
| Pleasant-days sanity | pass | pass — maximum 336.2 days, coldest metro 373rd of 387 |
| Crime consistency | pass | pass — 386 metros with figures, 372 above the floor, never scored |

Soft gates as measured: weight sensitivity Kendall τ 0.92–0.99 for every
±20% (target 0.85); the served-region true CV p99 9.8%, max 11.8%, no
point above 20%; external correlations unchanged in character (score
against living-alone share −0.04).

**The Pew re-run on the shipped sample** (`kernel.py pew decay_h5`: the
same leave-one-metro-out code path, from scratch — national refit, every
metro's dials, 387 refits; `results/phase3b/pew_rerun_decay_h5.json`):
124 metros, level offset 1.38 (the shipped sample's national out-group
share 22.0% over Pew's 16%); corrected median absolute error **3.33** for
national-only, **2.48** for the raw per-metro dial, **2.48** for the
shrunk dial (p90 9.65 / 7.05 / 7.11; max 22.7 / 12.7 / 12.8; the metro's
own observed rate 2.35 / 7.37); random pairing 22.9. Paired, metro by
metro: shrunk against national-only **91–33**, median paired difference
−0.71 points, sign test p < 0.001; shrunk against raw **54–70**, +0.01,
p = 0.18 — the same statistical tie the m3.0.0 kernel showed on the
recent sample (2.63 against 2.52, 53–71, p = 0.13), now with the medians
equal. The refit reproduces the Phase 3 record for this sample to the
second decimal in all three medians (`reproduces_phase3` all true; every
metro's dial within 2e-15 of the Phase 3 file). The split-half dial test
re-run with it: every component keeps its dial (shrunk over national
+2.03 / +0.64 / +5.64 per 1,000 weighted sides for age / education /
race, better in 258 / 204 / 254 of 387 metros; shrunk over raw in 225 /
254 / 243). The composition check re-derived on this sample: one national
multiplier on local composition misses Pew by a median 4.04 points (p90
9.61, max 20.8), off by more than 1.5× in 27% of metros; Jackson,
Mississippi reads Pew 3%, one-multiplier 16.0%, national-only 10.4%,
shrunk 7.8%, the site's own observed 10.7%.

**The tie, accepted on the record (A2).** ADR 0009 §4 is amended with
Nathan's decision and its evidence: the shrunk kernel beats national-only
decisively (2.63 against 3.38 on the recent sample, 87–37, p < 0.001;
2.48 against 3.33 on the shipped sample, 91–33, p < 0.001); Pew
publishes only the 124 large metros where a dial's prior share is near
zero (New York 0.4%, Los Angeles 0.7%, Chicago 0.8%) and shrinkage has
nothing to do, so the raw and shrunk dials are the same dial there and
can only tie; and on the site's own split-half test across all 387
metros the shrunk dial beats raw in 246 metros for race, 237 for age and
256 for education (recent sample; on the shipped sample 243 / 225 / 254).

## 3. Part B, one line each

PART_B_PLACEHOLDER

## 4. What changed for the visitor (Part A)

**Rank shift from m3.0.0**, default search (a woman of 30 seeking men
28–40, never or previously married), build 59fd352c5c2f against
ae1efbef9f0e (`results/phase3b/rank_shift_m3_0_0_to_m3_1_0.json`):
Kendall τ **0.962**, 155 of 193 ranks move, median absolute move **2
places**, p90 6, largest 18 (Provo 164 → 146; Springfield MO 104 → 117,
Erie 51 → 63, Ogden 156 → 144). The top ten go from New York, Boston,
Chicago, San Francisco, Philadelphia, Los Angeles, New Orleans, Austin,
Seattle, Atlanta to New York, Boston, San Francisco, Chicago,
Philadelphia, Los Angeles, Seattle, San Jose, New Orleans, Austin. The
index itself moves by a median 0.58 points (p90 1.61, max 4.68; τ 0.937
between the two index vectors).

**The index's range and margin**, default search: 82.4 (Salinas) to
117.3 (Ann Arbor), p10 / p50 / p90 = 88.2 / 96.1 / 106.9, served margin
4.08 index points at the median (m3.0.0: 83.3–115.1, 89.4 / 96.3 /
106.8, margin 4.03).

**The display cap (A3), before and after.** The registry ceiling is 250,
rendered `250+` with the band label carrying the rest, from one helper
(`scoring.match_display`) that composes the string the API serves to the
result rows, the city page and the compare table; the compare table
computes no difference against a capped figure (its cell shows the dash
a missing figure gets). Scoring is untouched — the engine test asserts
rankings, scores, standings and bands are bit-identical with the ceiling
at 1 and at a million. Measured on the reference searches
(`snapshot_m3_0_0.json` → `snapshot_m3_1_0.json`):

| Search | m3.0.0 top city by the index | m3.1.0 value | m3.1.0 display | Metros above 250, before → after |
|---|---|---|---|---|
| Graduate Asian woman of 30, default window | San Jose 565 | 624 | **250+** | 2 → 2 |
| Graduate Asian man of 34 | San Jose 547 | 592 | **250+** | 2 → 3 |
| Black woman of 30 | Memphis 304 | Jackson 313 | **250+** | 3 → 6 |
| Pacific Islander man of 35 | Fayetteville AR 2,760 | 2,802 | **250+** | 11 → 11 |
| Pacific Islander woman of 35 | Fayetteville AR 996 | 998 | **250+** | 7 → 7 |
| Graduate woman of 30 | San Jose 181 | 193 | 193 | 0 → 0 |
| Man of 31 seeking men 27–38 with a degree | San Jose 127 | 133 | 133 | 0 → 0 |

The cap changes no ranking: every one of these searches ranks exactly as
its uncapped value ranks it, and the value is still returned in the
response.

**Latency.** On the 400-query battery (`api/tests/measure_latency.py`,
single process through the ASGI stack, warm): **p50 41.3 ms, p95 57.4 ms,
p99 69.7 ms, max 104.9 ms** at a load average of 1.97 with the machine
in use for other work (a browser and a video editor open), against the
60 ms budget (m3.0.0, idle machine: 28.2 / 36.4 / 43.2 / 47.8). An
engine-level A/B of the two builds under identical conditions gives the
same p50 for both (60.8 against 60.8 ms under the Pew re-run's eight
workers), so the serving path is not slower than m3.0.0's — the cap adds
one string format per row — and the difference is the machine. The
figure is re-measured at the close of Part B (§4, Part B).

## Deviations (Part A)

1. **The stability sweep loads candidate kernels into the m3.0.0 build in
   memory** rather than rebuilding per candidate; the cubes do not depend
   on the kernel, and the shipped candidate was then rebuilt for real and
   run through the full battery (§2), which reproduces the sweep's 0.95.
2. **Ten and twenty years were never fitted.** The rule stops at the
   first half-life that passes; the Phase 3 sweep's numbers for them
   (Pew 2.44 / 2.28; 15 / 14 thin race cells) stand as fitted then.
3. **The root-cause metric did not move** (§1). Reported as measured;
   the gate is untouched and the pass is by the gate's own arithmetic.
4. **The Pew re-run is the same code path re-run**, so it reproduces the
   Phase 3 numbers for the five-year sample; it is reported beside the
   m3.0.0 figures because the brief asked for it beside them.
5. **The capped flag rides on the match block** (`capped: true`) so the
   compare table can skip the difference without parsing the token out
   of the display string.
6. **The display-cap test compares displays to values at half a point**
   — the display is rounded from the unrounded index and the served
   value to two decimals, so the two can sit 0.5 apart (63.5 vs "63");
   the m3.0.0 assertion that they round the same passed by luck.
7. **Latency was first measured under load** (validation had just
   finished, load average 7.4: p95 57.5 ms) and again at load 1.97 with
   the machine in use for other work (p95 57.4 ms); an engine-level A/B
   of the two builds under identical conditions gave the same p50 for
   both, so the code path is not slower than m3.0.0's. The final figure
   is measured on a quiet machine (§4).
8. **kernel_report.json's `sample_choice` records the new rule**
   (`chosen_by`) beside Phase 3's, so the Phase 3 record of what its own
   rule would have chosen stays readable.
9. **`.claude/launch.json`'s api entry now points at ae1efbef9f0e**;
   59fd352c5c2f stays complete until Part B ships and is then retired
   to manifest + metros.json + kernel.json (the 2g pattern).
