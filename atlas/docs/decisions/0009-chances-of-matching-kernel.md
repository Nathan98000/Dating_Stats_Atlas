# ADR 0009 — Chances of matching: an assortative kernel replaces balance as the slider's second pole

Date: 2026-09-23 (Phase 3, model m3.0.0, build 59fd352c5c2f)
Status: accepted; amended 2026-09-23 (Phase 3b Part A, model m3.1.0, build
ae1efbef9f0e — §2 fitting sample, §4 the Pew bar, §8 the display cap; the
Phase 3 text stands where it is not marked as amended)

## 1. The served quantity, stated once

`match_propensity` is a **similarity index over observed pairings,
normalised to a national mean**: for the visitor's own search it is

    rate_m  = Σ_c w(seeker, c) · n_{m,c}  ÷  Σ_c n_{m,c}      over the search-masked cube cells c of metro m
    index_m = 100 · rate_m ÷ ( Σ_m Σ_c w · n_{m,c} ÷ Σ_m Σ_c n_{m,c} )

where `n_{m,c}` is the metro's pool in cell c (age × education × race/
ethnicity of the sought sex, under the visitor's marital and income
selection) and `w(seeker, c)` is the kernel weight below. It is a **rate,
not a count** — that is what keeps it trading against pool size on the
slider rather than duplicating it — and it is an **index with 100 the
national average for that same search**: the numerator and denominator
summed over every metro (the cube's universe, all 387) give exactly 100,
so a city at 110 has a matched pool 10% more like the people who pair
with someone like the visitor than the country's does. It is a
description of observed pairing patterns, not a prediction about an
individual. Its margin is the delta-method variance of the ratio from the
cube's sum of squared record weights, Var(R) = Σ_c s2_c (w_c − R)² / D²,
computed and returned, never rendered (ADR 0004 stands). **Suppression is
unchanged**: the gate is `min(n_alloc, kish) < 100` on the unweighted
pool; the kernel can neither rescue nor condemn a cell.

## 2. The kernel: form and estimation

    w = exp( f_age(age_c − age_s ; sex_s) + f_edu(edu_s, edu_c) + f_race(race_s, race_c ; sex_s) )

**Fitted on real couples.** `pairing.py`'s Phase 2b linkage (reference
person ↔ spouse or unmarried partner within the household, codes asserted
against the pinned dictionary, multi-partner households excluded and
counted, both sides aggregated, 80 replicates carried) is reused as is;
the grain becomes the national couple table (sex × age × edu4 × race8) ×
(age × edu4 × race8), opposite-sex couples with both members 18–70, plus
the same by metro. The fitting sample in m3.0.0 was **recent unions**: unions formed since 2019 (MARHYP ≥ 2019) plus all unmarried partners — 986,770 allocated couple-sides, Kish 535,834, 246,038 non-empty national cells. Every union weighted by exponential decay (half-lives 5, 10, 20 and 40 years) and the unweighted stock were fitted, tested and reported beside it (PHASE3.md); the recent sample supported a stable fit on the stated criterion (IPF converged, face validity, every education cell and every own-group race cell above 100 effective sides, no metro below 100 Kish sides), so the default shipped.

**Amended, m3.1.0 (Phase 3b A1).** The recent-only kernel failed the
standing rank-stability gate on three of the eighteen personas (0.70–0.71
against the 0.80 bar; PHASE3.md finding 2). Nathan's decision: the
brief's own fallback applies — widen the window and decay by time — with
the half-life chosen **by the rank-stability gate, shortest first**, never
by the Pew sweep (which is confounded with Pew's period, §4). The
fitting sample is now **every union weighted by exponential decay with a
five-year half-life**, 0.5^((survey year − year last married) / 5),
unmarried partners at weight 1: 1,385,259 allocated couple-sides, Kish
974,834, no empty race cell (recent-only had two) and 19 race cells under
30 effective sides (against 31). Five years was the first candidate
tried and every persona reached the bar (minimum share 0.95; the three
that failed sit at 0.95, 0.96 and 0.96), so ten and twenty years were
not fitted (`results/phase3b/stability_sweep.json`). Recorded as
measured: the index's replicate standard deviation — the root-cause
metric — did not move (4.05 against 4.1 index points for the persona
that failed worst; 2.01 against 2.0 at the slider's match end), because
it is survey noise in the metro's own pool under a fixed kernel and no
fitting sample can reduce it; the gate passes because the five-year
kernel leaves the scores less bunched at the top-10 boundary. The stock
still never ships.
`MARHYP` (year last married) joined the extract for the clock; unmarried
partners carry no formation year in PUMS and enter every sample whole.

**Estimated as odds multipliers relative to random pairing given
availability.** The model is a conditional-logit / log-linear model with
an availability offset: for a seeker of type s the partner distribution is
P(c | s) ∝ A(c) · w(s, c), with A the national single adult population
(18–70, never or previously married, institutional group quarters
excluded) of the sought sex by age × edu4 × race8. Iterative proportional
fitting matches three margins exactly — the age-gap distribution per
seeker sex, the 4×4 education table pooled over sex, the 8×8 race table
per seeker sex — and is the maximum-likelihood fit. Dividing through by
availability is what makes the kernel, applied to a metro's own
composition, describe local pairing rather than re-describe national
demography. Each component is reported in the gauge "availability-
weighted mean multiplier 1 on its own margin under random pairing"; a
per-seeker constant `log_norm` makes the full kernel average exactly 1
over the national single adult population.

**Age** is smoothed (Gaussian kernel on the gap, Nadaraya–Watson on
observed over expected-without-the-age-term, bandwidth chosen per sex by
leave-one-gap-out Poisson deviance — the cross-validation chose the smallest candidate, 0.25 years, for both sexes; the deviance flattens below 0.5, so the data prefer essentially the raw estimate and the smoothing is a nearest-neighbour blend that matters only in the tails); the education and race
terms are refitted around the fixed smoothed age term. Cells with no
observed couples floor at 1e-4 (two race cells — men of another race with Pacific Islander partners and Pacific Islander women with partners of another race — and the twelve age gaps of 50 years or more). The separability test (the
saturated table against the multiplicative fit) is in PHASE3.md; its
headline is race and education pairings interact (7.2% of couples misallocated, 16% of couples in well-populated cells off by more than a quarter), the pooled education matrix hides a real sex asymmetry (3.7%), and the shift-invariant gap term under-fits how tightly 25-year-olds pair in age and over-fits 50-year-olds.

## 3. The metro dimension: partial pooling

Every metro clears the n ≥ 100 gate on its couples (recent unions: allocated couples per metro median 469, min 55; Kish effective sides median 520, min 105; out-group share relative MOE median 16.4%, p90 27.2%, worst 45.9%), but the
same sample split into kernel cells leaves the median metro about 23 couples per marginal kernel cell and the smallest 3 (recent unions; 123 and 34 on the stock the brief counted) — so no metro can carry
its own kernel. **The shape is national; each metro carries one dial per
component**, θ_k(m), a power on that component's log multipliers (θ = 1 is
the national kernel), fitted by maximum likelihood on the metro's own
couples against its own single population, with precision from the
observed information rescaled to the replicate-measured effective couple
count (the marginals' 80-replicate margins — no new data), shrunk toward 1
by empirical Bayes (DerSimonian–Laird τ²). All three components were
tested identically by leave-one-metro-out on split halves of each metro's
couples: race earns its dial decisively (+5.99 held-out log-likelihood per 1,000 weighted sides over the national kernel, better in 249 of 387 metros), age modestly (+1.52, 243 of 387) and education narrowly (+0.58, 204 of 387; its raw dials are worse than the national kernel out of sample and only shrinkage makes them useful) — all three ship, under the pre-stated rule of better in total and in more than half the metros. Shrinkage per metro is in
`results/phase3/dials_recent unions.csv`; the prior share (the fraction of a dial that is national rather than local) has median 0.27 for race, 0.38 for age and 0.69 for education; no metro is more than 90% prior for race or age and four are for education; New York, Los Angeles and Chicago carry race dials under 1% prior.

## 4. Validation: the Pew gate

Out of sample, per metro: leave it out, refit the national kernel without
it, predict its newlywed intermarriage rate from the kernel plus its own
composition, compare with Pew's 2011–2015 table (124 metros matched).
Three models: national-only, raw per-metro dial, shrunk dial. A level
offset was expected (Pew: married newlyweds 2011–2015; the fit: unions
formed 2019–2024 including cohabiting partners) and measured at
1.49 (the fitting sample's national out-group share 23.85% against Pew's published 16%); it is corrected by that one constant, taken from Pew's national
row and never from the metro test set. Corrected median absolute errors:
random pairing 19.7, national-only 3.38, raw per-metro dial 2.52, shrunk dial 2.63, the metro's own observed 2020–24 rate 2.47 (p90: 29.0 / 9.78 / 7.08 / 7.21 / 7.85). The shrunk kernel beats national-only materially (87 metros better, 37 worse, sign test p < 0.001) and beats the brief's crude national-multiplier baseline (3.94); against raw per-metro it is a statistical tie (raw ahead in 71 metros, shrunk in 53, median paired difference 0.02 points, p = 0.13), because Pew covers only the large, precisely-measured metros where the prior share is near zero. A strict reading of the bar's second clause is not met; the split-half test over all 387 metros, where shrinkage has work to do, has the shrunk dial beating raw for every component.

**Amended, m3.1.0 (Phase 3b A2): the tie clears the bar — Nathan's
decision, with its evidence.** (1) The shrunk kernel beats national-only
decisively: 2.63 against 3.38 points at the median on the recent sample,
87 metros better and 37 worse, sign test p < 0.001. (2) Pew publishes only
the 124 large metros — those with 200 or more newlyweds in sample — where
a dial's prior share is near zero (New York 0.4%, Los Angeles 0.7%,
Chicago 0.8%) and shrinkage has nothing to do, so the raw and shrunk dials
are the same dial there and can only tie. (3) Where shrinkage does have
work, the site's own split-half leave-one-metro-out test across all 387
metros has the shrunk dial beating raw in 246 metros for race, 237 for
age and 256 for education. **Re-run on the shipped five-year sample**
(`results/phase3b/pew_rerun_decay_h5.json`, the same leave-one-metro-out
code path, 124 metros, level offset 1.38): corrected median absolute
error 2.48 for the shrunk dial, 2.48 for the raw dial, 3.33 for
national-only (p90 7.11 / 7.05 / 9.65); shrunk against national-only
91–33, p < 0.001; shrunk against raw 54–70, median paired difference
0.01 points, p = 0.18 — the same tie, beside the m3.0.0 figures above.
The Pew number was not the criterion for the half-life (§2) and is
reported for the record. The composition check behind the design was
re-derived: the random-pairing expectation explains R² = 0.196 of Pew's variation, the availability-adjusted ratio spans 0.156–1.049 across metros, and one national multiplier on local composition misses Pew by a median 3.94 points (p90 9.58, max 20.3), off by more than 1.5× in 25% of metros.

## 5. The two optional inputs

The kernel needs the seeker's own education and race/ethnicity; the panel
asks for both, optional, under "about you", with a registry note saying
why they are asked and that they are optional. Neither is ever required.
An unset field drops its component to the **population-average
marginal**: the mixture over that attribute's levels weighted by the
national single population of the seeker's sex and age (each mixed-in
kernel normalised to mean 1), both unset leaving the age term alone. All
four combinations answer and suppress identically (tested). Consequence,
measured in PHASE3.md: two visitors differing only in what they disclosed
can see different figures for the same city (disclosing education alone moves the median metro by 7.8 index points, race or ethnicity alone by 25.1, both by 26.8; single-metro gaps reach the hundreds for small groups in the metros that concentrate them).

## 6. Race enters on the same footing as age and education

**Nathan's decision, taken deliberately.** Race/ethnicity is modelled,
estimated, served and documented exactly as age and education are: no
separate switch, gate, caveat or disclaimer anywhere. The per-level
sensitivity table (`results/phase3/sensitivity.csv`, one format for every
level of all three components) is the standing record of what each
component does, and the plain-words account (`strings.match_how`, on How
it works and the methodology page, reachable from the stat's information
box) names all three inputs in one sentence and register — what the
figure is built from, what it measures, and that it is an aggregate
pattern rather than a statement about an individual. Documentation, not
disclaimer.

## 7. Balance is demoted, not removed

`pool_balance` keeps its display name, its tally on result rows, city and
compare pages, and its What-we-measure row (its card body is the sentence
the pillar carried); its computation is unchanged (plain sex ratio, ADR
0004, separately gated). It is `context_only`, weight 0, out of the pillar
set, and no copy calls it part of the score. The slider control is
`pool_vs_match`; `pool_vs_balance` is accepted as a deprecated alias for
exactly m3.0.0, as `size_vs_odds` was for m2.0.0.

## 8. The display cap (amended, m3.1.0 — Phase 3b A3)

Disclosed searches drive the index into the hundreds (a graduate Asian
woman of 30 saw San Jose at 565 in m3.0.0; a Pacific Islander seeker
2,652 in one metro), which is what an availability-relative multiplier
does when a group is under 1% of the single population. The **display**
is capped at a registry-owned ceiling of 250 and anything above it
renders as `250+`, the band label carrying the rest. Scoring is
untouched: the feature is percentile-ranked, so no score, rank, standing
or band reads the display, and the engine test asserts rankings are
bit-identical with the ceiling at 1 and at a million. One formatting
helper (`scoring.match_display`) composes the string the API serves;
the result rows, the city page and the compare table render that string
and nothing else, and the compare table computes no difference against
a capped figure (its cell shows the dash a missing figure gets). The
ceiling and the `+` token are registry strings (`match_display_cap`,
`match_display_cap_token`); Nathan's copy is unchanged and the
information box gained nothing.

## Rejected

- **Per-metro kernel fitting** — no sample: the median metro about 23 couples per marginal kernel cell and the smallest 3 (recent unions; 123 and 34 on the stock the brief counted).
- **A national-only race term** — wrong in a patterned way: one national
  multiplier on local composition misses Pew by a median 3.94 points, p90 9.58, max 20.3, off by more than 1.5× in a quarter of metros, and Jackson,
  Mississippi reads 15.9% predicted against Pew's 3% (the national-only kernel 10.3%, the shrunk kernel 8.3%; the site's own 2020–24 recent-union rate there is 12.5%, so no model built on 2020–24 data reaches 3%).
- **The unweighted stock of all unions** — a 1985 marriage voting as
  loudly as a 2024 one; fitted and reported (4,591,004 sides; its shrunk kernel fits Pew's 2011–15 table better at the median (2.32 against 2.63) precisely because Pew's newlyweds are the older unions it adds — the Pew criterion is confounded with period, which is recorded in the report), not shipped.
- **Reintroducing rivals** — ADR 0004 stands; the served quantity is a
  rate over the visitor's own matched pool, never a ratio against anyone.

## Consequences

MODEL_VERSION m3.0.0, then m3.1.0 for the amendments (the five-year
sample, the accepted tie, the display cap; goldens regenerated again and
the before/after is in PHASE3B.md); goldens regenerated (eighteen vectors, the four
disclosure combinations and the deprecated alias among them). The rank
shift across the 193 under the stated default search, the correlation
between the slider's poles (r = 0.34 for the default search, median 0.04 over a 153-seeker battery, none above 0.7) and the latency of the weighted
path (p95 36.44 ms on the 400-query battery against a 60 ms budget, m2.4.0's 31.5 plus about five milliseconds for the weighted path) are in PHASE3.md.
