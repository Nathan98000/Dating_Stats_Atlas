# Phase 3b — Part A settles Phase 3 (m3.1.0); Part B sharpens the kernel (m3.2.0)

Part A: build **ae1efbef9f0e**, model **m3.1.0** (ADR 0009 amended §2, §4,
§8), committed as 228d4a5. Part B: build **f20cb02c3af8**, model
**m3.2.0** (ADR 0010). Suites at close: **50 pytest, 52 vitest, 78
Playwright**. Validation battery on each build: **nine of nine hard
gates pass**, rank stability among them (finding 2 of PHASE3.md, settled
in §1). Every number here is read from `results/phase3b/` (or the
validation report it names); nothing was recomputed for this document.

**In one paragraph.** The five-year half-life passes the stability gate
that recent-only failed, though not for the reason expected (§1); the
Pew tie is accepted on the record (§2); the display is capped at 250+
(§4). Of Part B's three refinements all three improve held-out
likelihood, the cohort age term by far the most, and **one ships**: the
race × education interaction. The cohort term and the sex-specific
education matrix are held back by the rank-stability gate — the first
fails it outright, the second only in combination — and a same-sex
search now takes its age term from same-sex couples while education and
race fall back, which the page says in one sentence (§3, §5).

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

| Refinement | Held-out gain, shrunk-dial kernel (per 1,000 weighted sides; metros better of 387) | Rank stability (m3.1.0 build; min share, bar 0.80) | Verdict |
|---|---|---|---|
| **B1** — a gap curve per seeker age cohort (17 cohorts per sex, chosen by split-half CV) | **+70.4** (386) | **fails**: 0.675 on the man of 33 seeking Hispanic women, 0.7875 at the slider's match end (twice) | **dropped** — the largest gain of the three, not tuned into passing |
| **B2a** — race × education two-way term, EB-shrunk toward no interaction (τ = 0.18) | **+14.1** (350) | passes at the bar: 0.800 (the man of 41 seeking women earning 50k+) | **ships** |
| **B2b** — a sex-specific education matrix | **+2.8** (344) | passes: 0.825 (the two slider-at-match-end personas) | **ships** |
| **B3** — same-sex pairing terms, per component | age: supported, **+205.7** (374 of 387), face passes → **ships**; education: supported, +4.3 (244), **face fails** (not diagonal-dominant) → falls back; race: unsupported (own-group cells of 5–44 sides), +42.6 (272) → falls back | the one same-sex persona stays at 1.0 | **age ships; education and race fall back, and the page says so** | |
| **Shipped form** (B2a + B2b) | **+14.1** (350) — identical to B2a alone | passes at the bar: 0.800 (with the same-sex age term, `shipped_final`, 0.800) | **ships as m3.2.0** | |

## 5. Part B in full (m3.2.0)

**The framework, unchanged from Phase 3.** Every refinement is fitted on
the shipped five-year sample and tested by leave-one-metro-out: for each
of the 387 metros the national kernel is refitted without its couples
under the baseline form and under the refined form (warm-started, the
full fit's bandwidths and prior), the three dials are fitted jointly on
each household half of the metro's couples and shrunk with the other
metros' full-sample (μ, τ²) for that form, and the other half is scored
— the split-half held-out log-likelihood, both directions summed over
every metro (`kernel_refine.py lomo`; `results/phase3b/refine_heldout.json`,
per metro `lomo_forms.json`). A refinement ships when its total exceeds
the baseline's under the shrunk-dial kernel; the no-dial comparison and
the metro counts are reported beside it, and every candidate that
improves held-out likelihood then has to pass the standing rank-stability
gate on the m3.1.0 build (`stability_check.py`) and keep p95 latency
under 60 ms. The generalised machinery (`kernel_refine.py`, forms over
kernel.py's data, dials, shrinkage and Pew code) reproduces kernel.py's
fit on the baseline form to 1e-9 in every log multiplier before anything
else ran (`kernel_refine.py check`).

### B1 — a gap curve per seeker age cohort

**The cohort boundaries and how they were chosen.** Seven candidate
partitions were stated up front — one cohort (the m3.1.0 term), three
(18–29, 30–44, 45–70), five (the separability table's 18–24 / 25–34 /
35–44 / 45–54 / 55–70), eight, twelve, seventeen and every single year
of age — and the partition was chosen by **split-half held-out
likelihood**: the national couple table split in half by household (the
metro tables' fold, which sums to the national table exactly), the full
kernel fitted on one half with the bandwidth cross-validated per (sex,
cohort) as before, the other half scored, both directions summed
(`refine_fits.json` → `partition`). The held-out gain over one cohort,
per 1,000 weighted couple-sides: three **+54.3**, five **+63.1**, eight
**+67.6**, twelve **+69.6**, **seventeen +70.2**, single year **+69.0**.
The grid was extended downward once — as the bandwidth grid was in Phase
3 — after twelve won a first pass at the edge of the grid; seventeen
then won with the single-year partition below it (over-fitting), so the
choice is an interior optimum and not the edge of what was offered. The
shipped cohorts: **18–19, 20–21, 22–23, 24–25, 26–27, 28–29, 30–31,
32–33, 34–35, 36–37, 38–39, 40–42, 43–45, 46–49, 50–54, 55–59, 60–70**,
per sex — two-year cohorts through the ages where the tightness of age
pairing changes fastest, widening after 40.

**The fitted curves against raw gaps at 25, 35 and 50**
(`age_curves_B1_age_cohorts.csv` beside `age_curves_baseline.csv`, the
share of a seeker's partners at exactly the seeker's own age, raw /
one-curve fit / cohort fit): men of 25 **26.2% / 16.5% / 26.2%**, women
of 25 19.7% / 15.2% / 19.9%; men of 35 14.1% / 12.9% / 14.3%, women of
35 14.3% / 14.2% / 14.6%; men of 50 **9.2% / 14.4% / 8.0%**, women of 50
10.5% / 13.2% / 9.3%. Summed over partner ages within fifteen years, the
one-curve fit missed the raw distribution by 40.6 percentage points for
men of 25 and 32.6 for men of 50; the cohort fit misses by 2.5 and 5.1
(women: 22.6 → 3.4 at 25, 24.6 → 5.3 at 50). The failure Phase 3
measured — the young pairing far more tightly than one shift-invariant
curve allows, the old more loosely — is what the cohort term removes.

**The effective sample behind each cohort, with the thin cohorts named**
(`refine_fits.json` → `cohort_sample`; Kish couple-sides per sex, and
the gaps within ten years holding fewer than 100 effective sides). Men:
18–19 **750** (thin at −1 and +2 to +9), 20–21 **3,627** (thin at −3
and +4 to +10), 22–23 8,929 (thin at −5, +6 to +10), 24–25 16,188 (thin
at −7, −6, +8 to +10), 26–27 23,907 (thin at −9 to −7, +9, +10), 28–29
29,837 (−10, −9, +10), 30–31 35,352 (−10), then 33,600–47,800 with no
thin gap through 55–59, and 60–70 47,762 (thin at +9, +10). Women: 18–19
**1,436** (thin at −1 and +5 to +10), 20–21 **6,157**, 22–23 13,223,
24–25 22,428, 26–27 30,166, 28–29 36,956, then 32,000–41,200 with the
thin gaps confined to −10 to −7 through 38–39 and none from 40 on. The
cross-validation answered the thinness the way it should: the chosen
bandwidth is 1.0 year for men of 18–19, 0.5 for men of 20–23 and women
of 18–21, 0.35 for men of 24–27, and 0.25 (the Phase 3 value) for every
cohort from the late twenties on (three cohorts of women — 28–29 and
40–42 — take 0.5). The two youngest cohorts of each sex are the thin
ones, and they are also the ones a visitor of 18–21 reads; their curves
are smoothed, not floored, and the smallest, men of 18–19, rests on 750
effective couple-sides (1,413 allocated).

**Separability, with the term in.** The gap-band × seeker-education
G² falls from 550,951 to 449,317 (share off by more than a quarter in
thick cells 6.1% → 5.4%), gap-band × seeker race 294,333 → 277,949, and
the pooled-education × sex table from 208,447 to 153,439 — the cohort
term takes some of the strain the education matrix had been carrying.

**Held-out likelihood.** Leave-one-metro-out, split-half, all 387
metros (`refine_heldout.json`): the cohort kernel beats the one-curve
baseline by **+70.4 log-likelihood per 1,000 weighted couple-sides**
under the shrunk-dial kernel, better in **386 of 387 metros** (+71.0
under the national kernel alone, 385 metros; the dials' own gain over
the national kernel is +7.7 per 1,000 with the term in against +8.3
without — the cohort curves take a little of what the age dial was
doing). It is by far the largest gain of the three refinements. Its
Pew comparison for the record: corrected median absolute error 2.50 for
the shrunk dial (raw 2.47, national-only 3.34), shrunk against
national-only 92–32, p < 0.001; against raw 53–71, p = 0.13 — the term
has nothing to say about who pairs across race lines, so Pew cannot see
it.

**Rank stability, the gate B1 fails.** Loaded into the m3.1.0 build in
place of the shipped kernel (`stability_check.py`, the same harness as
the half-life sweep; `stability_check.json`), the cohort kernel drops
**three personas below the bar**: the man of 33 seeking Hispanic women
falls from 0.9875 to **0.675**, and the two slider-at-match-end
personas from 0.9625 to **0.7875**; the baseline candidate artifact
reproduces the shipped 0.95 exactly, so the harness is the gate. The
mechanism is the one §1 recorded, in reverse: the replicate noise
barely moves (median sd 2.82 → 3.01 across personas; 2.93 → 3.54 for
the Hispanic-women persona), but the sharper young-age curves change
where the index gaps fall, and for those personas the scores at ranks
7–14 bunch (4.8 → 3.4 points; 3.6 → 2.4 at the match end) so the same
survey noise flips the top-10 boundary more often. Four other personas
become *more* stable (the man of 41 who failed in m3.0.0 goes to 1.0).
Under the Part B rule — a refinement ships only if it does not break
rank stability — **B1 is dropped and not tuned**: no cohort partition
was retried for a passing configuration, the gate is untouched, and the
held-out gain above stands as measured. The finding for Nathan: a
percentile-ranked, per-request index whose top-10 boundary sits within
a few index points of survey noise will move across this gate with
every change to the kernel, in either direction; m3.0.0 failed it,
m3.1.0 passed it at 0.95, and the best-fitting age term of the three
refinements fails it at 0.675 on one persona.

### B2 — race × education, and a sex-specific education matrix

**B2a — the two-way term, and how it is shrunk.** The kernel gains
g(race_s, race_c, edu_s, edu_c; sex_s), 2,048 cells (1,952 with
couples), estimated by penalised coordinate ascent: the three main
effects take exact IPF steps as before, the age term stays fixed at its
smoothed value, and each interaction cell takes a Newton step on the
ridge-penalised Poisson objective — a Gaussian prior on the log
interaction centred at **zero, no interaction**, whose variance τ² is
estimated from the data by the method of moments at the separable fit
(each cell's raw log ratio of observed to fitted, with sampling variance
1/n for n its observed couple-sides in allocated units). τ² = **0.0324
(τ = 0.18)** against a raw log-ratio spread of 0.78, so a cell with n
observed sides keeps the share n / (n + 31) of its raw log ratio: a
cell of 30 sides keeps half, a cell of 300 keeps 91%, a cell of 3 keeps
a tenth. Nothing is chosen by hand; the same DerSimonian–Laird logic
sets the dials' shrinkage. The penalised passes stopped at the 200-pass
ceiling with a final change of 0.0009 in a log multiplier (converged to
1e-7 on every main effect), which is immaterial and recorded.

**The interaction table** (`interaction_table_B2a_race_x_edu.csv`; the
multiplier applies on top of the race and education main effects).
Its log standard deviation across all 2,048 cells is 0.156; 791 cells
move a pairing by more than 10%, 25 by more than 65%. Multipliers run
from **0.46** (Asian women with Hispanic partners, both high school or
less; 185 sides) to **2.49** (Asian men with Asian women, both high
school or less; 3,293 sides — and 2.38 in the mirror). Among the thick
cells (over 1,000 allocated sides): Asian own-group pairing at the
lowest education level 2.4–2.5×; Hispanic women with Hispanic men both
at high school or less 1.74× (46,104 sides); white men with Hispanic
women, both high school 0.48× and 0.57× (3,286 and 2,146 sides) against
1.66–1.70× when the man holds a graduate degree; Asian women with white
men who both hold graduate degrees **1.69×**, white men with Asian
women both with graduate degrees 1.40× (the cell Phase 3 named on the
recent sample; on the five-year sample the separable fit's worst thick
cells are Asian seekers with high-school partners across race lines, at
0.34–0.37 of fitted). **Separability before and after** (the race ×
education table): G² **1,157,677 → 35,311**, couples misallocated
**6.6% → 0.25%**, couples in well-measured cells off by more than a
quarter **15.1% → 0.05%**; the worst remaining thick cells sit at 0.54
and 1.39 of fitted (cells of 400–1,100 sides that the prior keeps close
to zero, as intended). The education × seeker-sex G² falls from 208,447
to 98 as a side effect — the per-sex interaction absorbs the sex
asymmetry too — and the same-education × cohort table from 173,002 to
112,336. The age tables do not move (551,599 / 293,058: the term has
nothing to say about gaps).

**B2b — a sex-specific education matrix**, refitted as a 2 × 4 × 4 with
the pooled matrix's margins per seeker sex (odds multipliers relative to
random pairing given availability; seeker's level down the side). Men:
high school or less **1.50** / 0.92 / 0.55 / 0.42; some college 0.67 /
**1.36** / 1.04 / 0.86; bachelor's 0.35 / 0.68 / **2.12** / 2.08;
graduate 0.25 / 0.46 / 1.62 / **4.11**. Women: 1.51 / 0.75 / 0.42 /
0.35; 0.87 / **1.42** / 0.76 / 0.60; 0.45 / 0.96 / **2.09** / 1.86; 0.31
/ 0.72 / 1.88 / **4.37**. The asymmetry Phase 3 measured is in the
matrix now: a woman with a bachelor's degree and a man with a graduate
degree pair at 1.86× against the pooled 1.98× (and 2.08× the other way
round), a man with a graduate degree and a woman with some college at
0.46× against the pooled 0.59×. Separability: the education × sex table
closes exactly (G² 0); the race × education G² falls from 1,157,677 to
941,551 and the same-education × cohort table from 173,002 to 120,656.

**What it does to the served index for the searches it most affects**
(`phase3b_refine_effects.py`: each candidate kernel loaded into the
m3.1.0 build beside the baseline form's candidate, the index compared
over 467 searches — the eighteen personas and a grid of both sexes at
25/30/35/40/50 with every disclosure; `refine_effects.json`,
`refine_effects_B2a_race_x_edu.csv`). **B2a** moves a search's index by
a median of **2.3 points** across the ranked metros (p90 of the
per-search medians 6.1), changes the top city by the index in 53 of 467
searches, and never drops the full score's top-10 overlap below 4; the
searches it most affects are Asian seekers who disclose high school or
less — women of 50 by a median **16.5 points** (largest single-metro
change 209; Honolulu stays top), women of 40 by 14.9 (San Jose gives way
to Honolulu at the top), women of 30 by 12.9 (San Jose → Stockton), men
of 40 by 11.0 (largest change 236 points in one metro) — exactly the
cells where the separable fit was worst (Asian own-group pairing at the
lowest education level, 2.4–2.5× on top of the main effects). The
eighteen personas move by a median 1.1 points. **B2b** moves a search
by a median 0.9 points (largest median 2.3, for seekers with some
college — the row where the pooled matrix hid the most asymmetry — and
Asian women with some college in San Jose by up to 22 points in one
metro); the top city changes in 35 of 467 searches. **B1**, for the
record, moves a search by a median 1.0 points (largest median 2.9, for
seekers of 50 of another race; single-metro changes to 133 points in
Fargo for such seekers) and the top city in 53 of 467.

**Rank stability** (`stability_check.json`, the candidate kernels in
the m3.1.0 build): B2a passes **at the bar exactly** — the man of 41
seeking women 32–45 earning 50k+ (the persona that failed in m3.0.0)
falls from 0.95 to **0.800**; B2b passes at **0.825**, the two slider-
at-match-end personas falling from 0.9625 to 0.825 (their replicate sd
1.95 against 2.01; the scores at ranks 7–14 spread 4.3 points against
3.6, but the boundary sits in a different place). Both clear the gate;
neither clears it comfortably, which is the same story as B1's failure
told from the other side.

**Held-out likelihood.** Under the same test, **B2a gains +14.1 per
1,000 weighted sides** over the baseline form, better in **350 of 387
metros** (+14.6 under the national kernel alone, 340 metros; the
warm-started penalised refit takes a median 28 passes per left-out
metro against 3 for the main effects). **B2b gains +2.8 per 1,000**,
better in **344 of 387** (+2.8 national-only, 341 metros). Both improve
total held-out likelihood; both pass rank stability (above); both ship,
and the shipped form is the combination, fitted and tested in its own
right below. Their Pew comparisons for the record: B2a 2.51 / 2.49 /
3.39 (shrunk / raw / national-only), shrunk against national 90–34 p <
0.001, against raw 55–69 p = 0.24; B2b 2.48 / 2.48 / 3.34, 91–33 and
54–70 — the race margin the Pew test reads is not what either term
changes.

### B3 — same-sex pairing

**The sample.** The 117,522 same-sex couple-sides the Phase 3 linkage
counted and excluded enter a couple table of their own at the kernel
grain (`pairing.py samesex`: the same linkage, the same five-year decay
on married unions, both members 18–70): **65,011 allocated couple-sides,
Kish 39,989**, 1,452,508 weighted — 32,299 allocated sides for men with
men, 32,712 for women with women, 387 metros with at least one couple.
Same-sex marriages date from 2013 onward almost everywhere, so the decay
weights bite harder here than in the opposite-sex table (the allocated
count is 55% of the raw sides against 2.4 million to 4.6 million there).

**Effective sample per cell first** (`samesex_fit.json` → `support`;
Kish couple-sides per seeker sex; the support rule is the Phase 3
stability criterion applied per component — every 4×4 education cell,
every own-group race cell, every gap within ten years at or above 100
effective sides, for both sexes):

| Component | Men with men | Women with women | Supported |
|---|---|---|---|
| Age gap (smallest gap within ±10 years) | 253 | 253 | **yes** |
| Education (smallest of the 16 cells) | 411 (high school → graduate) | 255 (high school → graduate) | **yes** |
| Race / ethnicity (smallest own-group cell) | **4.9** (Pacific Islander); Native American 12.5, another race 43, Asian 264, two or more 197, Black 499, Hispanic 1,755, white 10,580; 6 of 64 cells empty, 30 under 30 | **17.6** (Pacific Islander); Native American 40.5, another race 36.5, Asian 472, two or more 265, Black 1,183, Hispanic 1,913, white 11,298; 2 cells empty, 35 under 30 | **no** |

So race and ethnicity keeps the opposite-sex fallback for same-sex
searches whatever the held-out test says: the three small groups' own-
group cells hold a handful of couples, and a national multiplier for
"Pacific Islander men with Pacific Islander men" from five sides is not
a measurement.

**The same-sex fit** (baseline form — one gap curve per sex, a pooled
4×4, an 8×8 per sex — fitted against the SAME sex's single population;
`multipliers_samesex_samesex.json`, `age_curves_samesex_samesex.csv`).
The IPF's smoothed stage stopped at the 200-iteration ceiling with a
final change of 1.02e-6 against the 1e-6 tolerance (converged for every
practical purpose; recorded). Bandwidths by cross-validation: 0.75 years
for men, 0.25 for women. The age multiplier peaks at the seeker's own
age for both sexes (30 at 30). The education matrix (seeker's level down
the side): high school or less **1.19** / 0.98 / 0.76 / 0.75; some
college 0.57 / **1.42** / 1.11 / 1.17; bachelor's 0.31 / 0.83 / **2.05**
/ **2.44**; graduate 0.20 / 0.61 / 1.71 / **4.55**. **It is not
diagonal-dominant**: same-sex seekers with a bachelor's degree pair with
graduate-degree partners at 2.44× random against 2.05× with partners at
their own level — a well-measured pair of cells (1,505 and 1,746
effective sides for the off-diagonal, 2,619 and 2,595 for the diagonal),
so a pattern rather than noise. The race matrix passes the own-group
check for every group and both sexes (own-group pairing 1.37× for white
men and 1.65× for white women, 3.3× and 4.0× for Black men and women,
4.4× and 8.5× for Asian men and women; the small groups' cells are the
floored and hundred-fold entries the support rule excludes).

**What that means for the education term.** It is supported by sample
size, but the standing kernel face-validity gate — a hard gate of the
battery, "the education matrix is diagonal-dominant" — checks every
education matrix the build serves, and the same-sex one fails it in the
bachelor's row. Under the ground rules a failing check is a finding, not
a bug to hide and not a gate to loosen, so **the education term is not
served from same-sex couples** even where the held-out test below says
it would predict same-sex couples better; it falls back with race, and
the report says why. (The gate as written encodes an opposite-sex
regularity — that people pair most with their own education level —
which the same-sex data contradict at one level; whether the gate should
read differently for same-sex terms is Nathan's call, and nothing was
changed to make it pass.)

**Held-out likelihood, per component** (`samesex_fit.json` →
`heldout`, `lomo_samesex.json`): for each of the 387 metros the
same-sex kernel is refitted without its same-sex couples and the shipped
opposite-sex form without its opposite-sex couples, and the metro's
same-sex couples are scored under the fallback the site served until
now (opposite-sex terms with the metro's dials), under each single
component swapped for its same-sex term, and under all three. Gains over
the fallback per 1,000 weighted same-sex sides: **age alone +205.7**
(better in 374 of 387 metros), education alone +4.3 (244), race alone
+42.6 (272), all three +263.2 (372). The age term's gain is the largest
number in this report and the least surprising: same-sex age gaps are
symmetric around zero by construction (each couple contributes both
gaps), while the opposite-sex curve is not, so a woman of 30 seeking
women was being scored with the curve for a woman seeking men.

**What ships for same-sex searches** — the component rule is support,
held-out improvement and face validity together: **age from same-sex
couples** (all three hold), **education from opposite-sex couples**
(supported and better held out, but its matrix fails the face check
above), **race from opposite-sex couples** (unsupported). The
opposite-sex race × education interaction rides on a same-sex search,
since both the education and the race term it corrects are the
opposite-sex ones; the same-sex age term is served at dial 1 (no metro can carry a same-sex dial) and the fallback components
keep the metro's dials, normalised over the seeker's own sex's singles
(`kernel_v2`: `ss_f_age`, `ss_log_norm`). **On the page**, every row of
a same-sex search carries the registry sentence in its information box
(`match.note`, `strings.match_same_sex_note`: "For a same-sex search the
age gaps come from same-sex couples in the same survey; the education
pairings and the racial and ethnic pairings are borrowed from
opposite-sex couples, because the same-sex couples in the survey do not
support a dependable measure of them on their own."), the response says
which components (`match_inputs.same_sex_components`), the methodology
page carries the same sentence, and the second registry string
(`match_same_sex_note_all_fallback`) stands ready for a kernel with no
same-sex terms at all. A same-sex visitor reads whose patterns their
figure is built from without opening a report.

### The shipped kernel (m3.2.0)

The shipped opposite-sex form is **the baseline plus B2a** (one gap curve
per sex, the pooled 4×4 stored per sex with equal rows, the 8×8 per sex,
the shrunk interaction), refitted and dialled as "shipped"
(`refine_fits.json` → `forms.shipped`, `dials_shipped.csv`): every
component keeps its dial (shrinkage centre 0.997 / 0.968 / 0.914 for age
/ education / race, τ 0.067 / 0.078 / 0.122). Its own leave-one-metro-out
record reproduces B2a's exactly — held-out gain **+14.1 per 1,000
weighted sides, 350 of 387 metros**; Pew corrected median absolute
error **2.51** for the shrunk dial, 2.49 raw, 3.39 national-only (p90
7.05), shrunk against national 90–34 p < 0.001, against raw 55–69 p =
0.24 — and it passes rank stability at **0.800** (`stability_check.json`
→ `shipped`; with the same-sex age term added, `shipped_final`, 0.800
again: the same-sex term touches only the one same-sex persona, which
stays at 1.0). The combination with B2b, for the record, fails at
0.750 (`B2a_plus_B2b`), and B2b's own held-out record stands at +2.8.

Every number below is for build f20cb02c3af8 (m3.2.0).

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

## 6. What changed for the visitor (Part B, m3.2.0)

**Rank shift**, default search, build ae1efbef9f0e (m3.1.0) against
f20cb02c3af8 (m3.2.0) (`rank_shift_m3_1_0_to_m3_2_0.json`): Kendall τ
**0.955**, 169 of 193 ranks move, median absolute move **2 places**, p90
7, largest 18 (El Paso 45 → 63; Erie 63 → 47; McAllen 128 → 144; Santa
Cruz 111 → 126; Brownsville 155 → 167 — the interaction moves the
metros where race and education pairings are most entangled). The top
ten: New York, Boston, Chicago, Philadelphia, San Francisco, Los
Angeles, New Orleans, San Jose, Seattle, Atlanta (m3.1.0 had San
Francisco third and Austin tenth). From m3.0.0 across both parts: τ
0.952, median move 2, largest 15 (`rank_shift_m3_0_0_to_m3_2_0.json`).

**The index's range and margin**, default search: **84.0 (Salinas) to
114.9 (Ann Arbor)**, p10 / p50 / p90 = 90.0 / 96.7 / 107.7, served
margin **3.98** index points at the median (m3.1.0: 82.4–117.3, 88.2 /
96.1 / 106.9, 4.08; m3.0.0: 83.3–115.1, 4.03); the index moves by a
median 1.18 points from m3.1.0 (p90 2.36, max 3.55; τ 0.915 between the
index vectors).

**The reference searches, before and after** (m3.1.0 → m3.2.0; the cap
is unchanged at 250):

| Search | m3.1.0 top city by the index | m3.2.0 | Display | Metros above 250 | Served margin, median |
|---|---|---|---|---|---|
| Graduate Asian woman of 30 | San Jose 624 | San Jose 637 | 250+ | 2 → 2 | 12.1 → 12.5 |
| Graduate Asian man of 34 | San Jose 592 | San Jose 600 | 250+ | 3 → 2 | 13.8 → 14.1 |
| Black woman of 30 | Jackson 313 | Montgomery 316 | 250+ | 6 → 7 | 11.9 → 11.9 |
| Pacific Islander man of 35 | Fayetteville AR 2,802 | 2,767 | 250+ | 11 → 11 | 10.9 → 10.6 |
| Pacific Islander woman of 35 | Fayetteville AR 998 | 1,047 | 250+ | 7 → 8 | 7.3 → 7.2 |
| Graduate woman of 30 | San Jose 193 | San Jose 192 | 192 | 0 → 0 | 6.8 → 6.7 |
| **Man of 31 seeking men 27–38 with a degree** | San Jose 133 | San Jose **117** | 117 | 0 → 0 | **6.06 → 3.11** |

The same-sex search is the one Part B changes on its face: with its
age term measured on same-sex couples the index runs 88.6–116.6 across
the ranked metros instead of 75.3–132.9, and its margin halves — the
opposite-sex curve had been scoring a man seeking men with the curve
for a man seeking women.

**The served effect of the shipped kernel** on the 467-search grid
(`refine_effects.json` → `shipped_final`): a median **2.3 index points** per search across the ranked metros (p90 of the per-search medians 6.1, largest 16.5 — the Asian seekers disclosing high school or less, as under B2a alone), the top city by the index changing in 53 of 467 searches, the eighteen personas moving by a median 1.2 points; the same-sex persona (a man of 31 seeking men 27–38 with a degree) moves by a median **4.1 points** with a largest single-metro change of 20.99, τ 0.547 between its two index vectors — the largest reordering of any search, and the one Part B set out to change (San Jose, CA stays its top city; top-10 overlap of the full score 7 of 10).

**Latency.** On the 400-query battery (`api/tests/measure_latency.py`,
single process through the ASGI stack, warm; `latency_m3_2_0.json`),
measured after the battery had finished and the load average had fallen
to 2.48 with Nathan's own applications still open: **p50 30.7 ms, p95
41.1 ms, p99 47.2 ms, max 50.3 ms** against the 60 ms budget (m3.0.0 on
an idle machine: 28.2 / 36.4 / 43.2 / 47.8). The interaction adds one
396,000-element product per request to the seeker weights (the full
seeker-level × partner-cell tensor, then a sum) and the same-sex path
one array select; the reading is about five milliseconds above m3.0.0's
at p95 on a busier machine, and the engine-level A/B of §4 (Part A) had
already shown the m3.1.0 path no slower than m3.0.0's. This reading
stands for Part A as well: the m3.2.0 path is a superset of the m3.1.0
one.

## 7. The battery on m3.2.0

`validate.py` on build f20cb02c3af8 (`results/phase3b/validation_report_m3_2_0.json`;
the first run, before the soft Pew check was pointed at the shipped
form's record, is kept as `validation_report_m3_2_0_first.json` and has
the same nine hard verdicts):

| Hard gate | m3.1.0 | m3.2.0 |
|---|---|---|
| Interval calibration | pass | pass — coverage 0.975, median overstatement 0.234 |
| Suppression reasons and intervals | pass | pass |
| Cube-vs-SQL differential | pass, 1.98e-7 | pass — worst relative error 1.98e-07 (the kernel-weighted sum with the interaction, both ways) |
| **Rank stability** | pass, minimum 0.95 | **pass — minimum 0.8000** (D_man41_women_50k 0.8000, C_woman38_grad_men_100k 0.9250, slider_all_match 0.9500); the same-sex persona 1.0 |
| Explanation invariants | pass | pass — 2,065 explanations, zero banned terms |
| Kernel face validity | pass | pass — the 30-year-old's multiplier peaks at 30 for both sexes; both per-sex education matrices diagonal-dominant; every own-group race multiplier above its off-diagonals; **and the served same-sex age term peaks at 30 for both sexes** (the gate now reads every term a search can be served) |
| Adversarial artifacts | pass | pass |
| Pleasant-days sanity | pass | pass |
| Crime consistency | pass | pass |

Soft gates: weight sensitivity τ 0.92–0.99 for every ±20%; the
served-region true CV unchanged; the Pew reproduction now reads the
shipped form's own record (2.51 / 2.49 / 3.39 — shrunk / raw /
national-only) with the accepted tie noted beside it.

## Gate check

1. **A half-life of 20 years or less passes rank stability on all
   eighteen personas, and the full battery's nine hard gates pass on the
   shipped build.** Five years: minimum share 0.95 (§1); nine of nine on
   ae1efbef9f0e (§2) and on f20cb02c3af8 (§7). ✓
2. **The half-life was chosen by stability, not by Pew, and the report
   says so beside the Pew number.** §1, the table and the paragraph under
   it. ✓
3. **The display cap renders everywhere the figure appears, from one
   helper, and leaves rankings bit-identical.** `scoring.match_display`;
   rows, the city page and the compare table render its string; the
   difference column skips a capped figure; asserted at ceilings of 1 and
   a million (§4, `test_match_display_cap_is_presentational`,
   `phase3b.spec.ts`). ✓
4. **The Pew comparison is re-run on the shipped sample and ADR 0009 is
   amended with the accepted tie and its evidence.** §2; ADR 0009 §4. ✓
5. **Each Part B refinement reports its held-out gain or loss, and only
   those that improve it ship.** §3: +70.4 / +14.1 / +2.8 for B1 / B2a /
   B2b, +205.7 / +4.3 / +42.6 for the same-sex age / education / race
   terms; B2a and the same-sex age term ship; B1, B2b, and the same-sex
   education and race terms do not, each for a stated gate (stability,
   the combination's stability, face validity, support). ✓
6. **Same-sex searches either use same-sex terms or say which components
   fall back, on the page.** Both: the age term is same-sex, and every
   row's information box carries the registry sentence naming the
   fallbacks (§5 B3; `match.note`; `phase3b.spec.ts`). ✓
7. **Latency p95 under 60 ms on the 400-query battery after all
   changes.** p95 **41.1 ms** on the m3.2.0 build at a load average of 2.48 (§6). ✓
8. **Registry owns every new string; axe zero serious or critical; the
   banned-vocabulary sweep returns zero; Nathan's approved copy is
   unchanged.** Four new strings, all in `features.yaml` and loader-
   asserted (`match_display_cap`, `match_display_cap_token`,
   `match_same_sex_note`, `match_same_sex_note_all_fallback`); the
   Playwright a11y suite passes (axe, all page shapes) and the battery's
   explanation invariants sweep zero banned terms across 2,065
   explanations; `match_info`, `match_how`, `slider_info` and the rest of
   Nathan's copy are byte-identical (the diff touches no existing
   string). ✓

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

## Deviations (Part B)

1. **The held-out likelihood drops the couple's own log-availability
   term** (a constant across the kernels compared, the Phase 3 dial
   convention), so a couple whose partner type has no singles in the
   availability table scores finitely; the first partition pass returned
   −∞ before this was made explicit.
2. **The partition grid was extended downward once** (seventeen cohorts
   and single years) after twelve won at the edge of the first grid — the
   Phase 3 bandwidth precedent — and seventeen won with the single-year
   partition over-fitting below it.
3. **The interaction's penalised passes stopped at the 200-pass ceiling**
   with a final change of 0.0009 in a log multiplier (every main effect
   converged to 1e-7); the same-sex fit's smoothed stage stopped at 200
   iterations with a final change of 1.02e-6 against a 1e-6 tolerance.
   Both recorded, neither material.
4. **τ² for the interaction is estimated around zero, not around the
   precision-weighted mean** (the dials' centre) — "toward no interaction"
   is what the brief asked for, and a non-zero centre would have meant a
   uniform interaction, which is not one.
5. **The interaction is undialled.** A per-metro power on 2,048 cells is
   far beyond any metro's sample; it is a national correction and rides
   at 1 everywhere.
6. **The combination B2a + B2b fails rank stability at 0.750** although
   each passes alone; the refinement with the larger held-out gain ships
   alone, B2b is recorded as shippable on its own and dropped for the
   combination's failure (`refine_fits.json` → `forms.shipped.refinements`,
   `stability_check.json` → `B2a_plus_B2b`). The first chain's `lomo
   --only shipped` ran on the combined form with no forms selected (a bug
   in the form list, fixed before the second chain), so the combination
   has a stability record and no separate held-out record; its
   components' records stand.
7. **B1 is dropped by the stability gate, not by fit** (§5); nothing was
   retried, the code and its record (the partition CV, the curves, the
   cohort samples, the LOMO record) stay so the term can ship the day the
   gate reads differently.
8. **The same-sex education term is dropped by the face-validity gate**
   although supported and better held out (§5 B3); the gate encodes an
   opposite-sex regularity and was not loosened.
9. **Same-sex terms carry no dials** (served at 1) and the same-sex
   kernel uses one cohort; the fallback components keep the metro's
   opposite-sex dials, and the opposite-sex interaction rides on a
   same-sex search because both terms it corrects are opposite-sex.
10. **The same-sex normaliser is computed for the served composition**
    over the seeker's own sex's singles (`ss_log_norm`), so the mixture
    identity for undisclosed inputs holds on same-sex searches too
    (asserted in `test_same_sex_search_says_whose_patterns_it_uses`).
11. **kernel_v1 artifacts still load** (one cohort, the pooled matrix
    stored twice, no interaction, no same-sex block), so the m3.1.0
    fixture ran green through the v2 loader before the m3.2.0 fixture
    replaced it.
12. **The B3 same-sex sentence is one registry string rendered in the
    information box for same-sex searches and repeated on the methodology
    page**; a second string stands ready for a kernel without same-sex
    terms. Nathan's approved copy is unchanged.
13. **The fixture's `kernel.npz` now copies every array the artifact
    ships**, slicing the per-metro ones (dials, both normalisers) to the
    twelve metros.
