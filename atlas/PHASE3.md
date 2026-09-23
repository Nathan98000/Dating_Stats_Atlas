# Phase 3 — Chances of matching: the assortative kernel replaces balance as the slider's second pole

Build **59fd352c5c2f**, model **m3.0.0** (ADR 0009). Suites at close: **48
pytest, 52 vitest, 75 Playwright**. Validation battery on the new build:
**8 of 9 hard gates pass; rank stability fails** on three of the eighteen
personas (below, finding 2). The three data cubes and metros.json are
byte-identical to 5d0e3ca2f708's — the re-extract reproduced them
exactly — and every features column matches to nine decimals. axe zero
serious/critical across the ten page shapes, banned-vocabulary sweep zero
across eleven. Every number below is read from `results/phase3/` (or the
validation report it names); nothing was recomputed for this document.

**The served quantity, stated once.** `match_propensity` is a similarity
index over observed pairings, normalised to a national mean: for the
visitor's search, the kernel-weighted share of the metro's own matched
pool, Σ_c w(seeker, c)·n_c ÷ Σ_c n_c over the search-masked cube cells,
divided by the same ratio over the cube summed across all 387 metros and
multiplied by 100 — so 100 is the national average for that exact search,
by construction, and the pool-weighted mean of the index across every
metro is exactly 100 (asserted in `test_seeker_weights_four_disclosure_combinations`).
It is a rate, not a count, so it trades against pool size on the slider
rather than duplicating it; it describes observed pairing patterns in
recent unions and is not a prediction about any individual. Suppression
is unchanged and gates on the unweighted n.

## Read this first: two findings for Nathan's decision

**Finding 1 — the Pew gate is passed against national-only and tied
against raw per-metro.** Out of sample on the 124 Pew metros the site
covers, the shrunk kernel's corrected median absolute error is **2.63
points** against **3.38** for national-only (87 metros better, 37 worse,
sign test p < 0.001) and against **3.94** for the brief's crude
national-multiplier baseline (re-derived: 3.94 / p90 9.58 / max 20.3
against the brief's 4.1 / 9.7 / 21.7). Against the raw per-metro dial it
is **2.63 vs 2.52** — raw ahead in 71 metros, shrunk in 53, median paired
difference **0.02 points, p = 0.13**: a statistical tie. Against the
metro's own observed 2020–24 rate (the rawest per-metro figure) it is
2.63 vs 2.47 at the median and **7.21 vs 7.85 at p90**. A strict reading
of the bar's second clause ("beat raw per-metro") is therefore **not
met**; the reason is structural, not a defect: Pew publishes only metros
with 200+ newlyweds in sample, i.e. the large, precisely-measured metros
where a dial's prior share is near zero (New York 0.4%, Los Angeles
0.7%, Chicago 0.8%) and shrinkage has nothing to do. Where it does have
work — the 263 metros Pew omits — the split-half leave-one-metro-out test
over all 387 metros has the shrunk dial beating raw in **246 of 387
metros for race, 237 for age, 256 for education**, and beating the
national kernel in total held-out likelihood for every component (§3).
The read on whether the kernel is good enough to score with: as a
predictor of who pairs with whom it is materially better than anything
the site had (correlation with Pew 0.80 against 0.67 for national-only
and 0.44 for random pairing); shrinkage neither helps nor hurts on the
metros Pew can see. Whether a tie with raw per-metro clears the bar as
written is Nathan's call. The serving change is isolated in one commit
(`1452a18`), so reverting the pole while keeping the measurement is a
single revert.

**Finding 2 — the match index is noisier than balance was, and the
standing rank-stability gate fails at the slider's match end.** Under
m2.4.0 every persona had a top-10 that survived ≥ 8-of-10 in ≥ 91% of
the 80 replicate draws; under m3.0.0 fifteen of eighteen personas are at
0.975–1.0, but the man of 41 seeking women 32–45 earning 50k+ drops to
**0.71**, and the two personas with the slider fully on chances of
matching sit at **0.70** (bar 0.80). The diagnostics are in the
validation report: for that persona the index's replicate sd is 4.1
points at the median (p90 6.8; the served margin says 7.3 at 90%, so the
delta-method margin is honest), the index spreads 26 points p10–p90, and
the scores at ranks 7–14 lie within 1.2 points of each other — survey
noise on a percentile-ranked, bunched quantity churns the top-10
boundary. Balance's two whole age-by-sex counts were far more precise.
Nothing was tuned: the gate stands and the build fails it. The
alternatives are Nathan's: accept the churn at the match end, change the
intensive normalisation for per-request features, or keep balance as the
pole for another phase.

## 1. The per-level sensitivity table

Every level of every component, one format. For each level: seekers at
that level (both sexes, the site's default window relative to the
seeker's age — a woman of 30 seeking men 28–40 is the stated default, so
[age−2, age+10] — never or previously married, no other filter, the
UNFILTERED view almost everyone sees), the median absolute change in
`match_propensity` across the ranked metros when the kernel is refitted
WITHOUT that component (IPF with the term held at zero, the other two
absorbing what they can, the shipped dials kept for the other
components), the Kendall τ between the two index vectors, the top city
by the index before → after, and the top-10 overlap of the full score at
default weights.

| Component | Level | Seekers | Median change (index pts) | p90 | Max | τ of the index, with vs without | Top city by the index, with → without | Top-10 score overlap |
|---|---|---|---|---|---|---|---|---|
| age | 18-24 | men | 5.5 | 18.6 | 56.3 | 0.46 | Provo, UT → Yakima, WA | 2/10 |
| age | 25-34 | men | 3.3 | 9.4 | 32.3 | 0.71 | Fort Collins, CO → San Jose, CA | 10/10 |
| age | 35-44 | men | 4.7 | 12.4 | 35.4 | 0.62 | Fargo, ND → McAllen, TX | 7/10 |
| age | 45-54 | men | 3.8 | 10.8 | 37.0 | 0.68 | Provo, UT → Boulder, CO | 7/10 |
| age | 55-70 | men | 3.0 | 7.8 | 26.4 | 0.77 | Duluth, MN → Portland, ME | 5/10 |
| edu | High school or less | men | 6.7 | 15.7 | 34.1 | 0.56 | Yakima, WA → McAllen, TX | 6/10 |
| edu | Some college | men | 2.4 | 6.0 | 15.3 | 0.82 | Provo, UT | 7/10 |
| edu | Bachelor's | men | 9.3 | 21.3 | 40.7 | 0.63 | Boulder, CO → Provo, UT | 8/10 |
| edu | Graduate | men | 14.1 | 31.5 | 63.1 | 0.55 | San Jose, CA | 8/10 |
| race | Hispanic | men | 36.1 | 72.0 | 243.0 | 0.20 | McAllen, TX → Provo, UT | 4/10 |
| race | White | men | 22.1 | 45.0 | 73.5 | 0.25 | Fargo, ND → Ann Arbor, MI | 4/10 |
| race | Black | men | 31.5 | 62.1 | 159.9 | -0.16 | Memphis, TN → Provo, UT | 5/10 |
| race | Asian | men | 33.7 | 58.3 | 386.9 | 0.41 | San Jose, CA → Ann Arbor, MI | 8/10 |
| race | Native American | men | 22.1 | 71.5 | 579.4 | 0.26 | Anchorage, AK → Provo, UT | 6/10 |
| race | Pacific Islander | men | 31.1 | 84.9 | 2652.1 | 0.23 | Fayetteville, AR → Provo, UT | 2/10 |
| race | Two or more races | men | 12.0 | 27.1 | 93.0 | 0.35 | Fayetteville, AR → Ann Arbor, MI | 7/10 |
| race | Another race | men | 24.3 | 58.6 | 681.5 | 0.14 | Fargo, ND → Ann Arbor, MI | 5/10 |
| age | 18-24 | women | 3.2 | 8.6 | 31.5 | 0.13 | College Station, TX → McAllen, TX | 4/10 |
| age | 25-34 | women | 2.5 | 6.4 | 15.6 | 0.73 | Ann Arbor, MI → Washington, DC | 8/10 |
| age | 35-44 | women | 3.0 | 7.8 | 27.0 | 0.61 | Montgomery, AL → Washington, DC | 8/10 |
| age | 45-54 | women | 2.5 | 6.9 | 23.3 | 0.62 | Raleigh, NC → Jackson, MS | 9/10 |
| age | 55-70 | women | 2.7 | 7.2 | 24.3 | 0.64 | Ann Arbor, MI | 8/10 |
| edu | High school or less | women | 5.5 | 14.0 | 29.6 | 0.49 | Yakima, WA → McAllen, TX | 9/10 |
| edu | Some college | women | 1.6 | 4.4 | 16.9 | 0.76 | Jackson, MS → Montgomery, AL | 8/10 |
| edu | Bachelor's | women | 9.8 | 22.0 | 35.4 | 0.44 | Boulder, CO → Duluth, MN | 6/10 |
| edu | Graduate | women | 15.1 | 31.5 | 61.0 | 0.41 | Ann Arbor, MI | 6/10 |
| race | Hispanic | women | 31.7 | 60.4 | 222.5 | 0.06 | McAllen, TX → College Station, TX | 6/10 |
| race | White | women | 18.3 | 34.7 | 56.2 | 0.31 | Duluth, MN → Ann Arbor, MI | 3/10 |
| race | Black | women | 38.2 | 82.1 | 249.2 | -0.04 | Jackson, MS → Ann Arbor, MI | 3/10 |
| race | Asian | women | 21.4 | 39.8 | 301.3 | 0.53 | San Jose, CA → Ann Arbor, MI | 8/10 |
| race | Native American | women | 17.0 | 50.3 | 501.1 | 0.23 | Yakima, WA → Provo, UT | 5/10 |
| race | Pacific Islander | women | 31.4 | 75.5 | 1138.6 | 0.14 | Fayetteville, AR → Provo, UT | 2/10 |
| race | Two or more races | women | 7.1 | 16.9 | 97.1 | 0.49 | Fayetteville, AR → Ann Arbor, MI | 6/10 |
| race | Another race | women | 18.2 | 51.7 | 516.1 | 0.15 | Lafayette, LA → Ann Arbor, MI | 6/10 |

**The read.** In the unfiltered view the three components are not equal
in effect, and the table says by how much. **Race/ethnicity does most of
the work**: removing it moves a disclosed seeker's index by a median of
23 points across the sixteen sex × group levels (largest: Black women,
38.2; Hispanic men 36.1; Asian men 33.7), changes the top city by the
index at every one of the sixteen levels, and leaves the with/without
index vectors barely correlated (τ from −0.16 to 0.53). **Education is
second**: a median of 8 points across its eight levels, 15.1 for women
with graduate degrees and 14.1 for men, small for "some college" (1.6 /
2.4) because that level's row of the education matrix is the flattest;
the top city changes at five of eight levels. **Age is third in size but
not in rank effect**: a median of 3 points (5.5 for men of 18–24, the
tightest-pairing cohort), yet the top city by the index changes at nine
of ten levels — the age term separates metros by small margins, so the
very top of a ranking on the index alone is fragile to it. The full
score's top-10 (default weights) keeps 2–10 of its cities in every case;
the three 2/10s are men of 18–24 (age) and Pacific Islander seekers of
both sexes (race, where the few metros with any concentration swing by
hundreds of points).
The largest single-metro effects are all small-group race levels in the
metros that concentrate them (Pacific Islander seekers: 2,652 points in
one metro), which is what an availability-relative multiplier does when a
group is under 1% of the population.

Two structural facts, measured rather than asserted:

- **A filter to a single level of an attribute makes that component
  nearly a constant multiplier for the national shape, so it largely
  drops out of the ranking** — the per-metro dials keep a residual, since
  each metro scales the component by its own dial. Each component does
  most of its work in the unfiltered view. Measured (`filter_fact.json`): for a Black woman of 30 seeking Black men,
the index with the race term and the index refitted without it are
proportional to within a 8.9% coefficient of variation across the ranked
metros (τ 0.548, the same top five); for the same seeker with no race
filter the ratio varies 63% and τ falls to -0.01. An Asian man of 35
seeking Asian women: CV 15.8%, τ 0.646; unfiltered, CV 56%, τ 0.35. A woman
of 32 with a graduate degree seeking graduate men: CV 5.9%, τ 0.698;
unfiltered, CV 20%, τ 0.40. (The residual variation under a
one-level filter comes from the per-metro dials, which scale the
component differently in each metro.)
- **Two visitors differing only in what they disclosed can get different
  figures for the same city.** Measured (`disclosure_gap.csv`, the same city's index with and without
a disclosure, over a grid of seekers of both sexes at ages 25–50): disclosing education alone moves the median metro
by 7.8 points (the largest median gap 18.7, for men of 30 with graduate
degrees; the largest single-metro gap 108); disclosing race or ethnicity alone
moves it by 25.1 points at the median (largest median 39.7, Black men of 35;
single-metro gaps run to 2,649 for Pacific Islander seekers in the metros that
concentrate the group); disclosing both, 26.8 at the median and 47.5 at
most (men of 35 with graduate degrees, Asian). On the live build for the
  default search: undisclosed, the index runs 83 (Salinas) to 115 (Ann
  Arbor); a graduate puts San Jose at 181 and Ann Arbor at 167; a Black
  woman puts Memphis, Jackson and Montgomery at 304; a graduate Asian
  woman puts San Jose at 565 and Jackson at 24. Suppression is identical
  across the four paths (tested), because the gate never sees the
  weights.

The three inputs are modelled on the same footing: none is special-cased
in the registry, the estimation or the serving path, none carries a
switch, gate or caveat the others lack. Race enters exactly as age and
education do — Nathan's decision, taken deliberately and recorded in ADR
0009 — and this table is the standing record of what each component does.

## 2. The Pew result

Out of sample, per metro: leave it out, refit the national kernel without
its couples and its singles, fit its dials on its own couples, shrink them
with the other metros' τ² and centre, then predict its newlywed
intermarriage rate from the kernel plus its own composition (seekers =
its single adults weighted by the national union-formation rate for their
type; partners drawn from its own singles) and compare with Pew's
2011–2015 table. **124** of Pew's 126 metros match the site's CBSA codes.

A level offset was expected and measured: Pew's newlyweds are married
couples of 2011–2015; the fitting sample is unions formed 2019–2024
including cohabiting partners, and its national out-group share is
**23.85%** against Pew's published 16% — a ratio of **1.49**. Every
model's predictions are divided by that one constant, taken from Pew's
national row (an integer percent, so the ratio itself carries about ±3%)
and never from the metro test set; raw errors are reported beside the
corrected ones.

| Model | Median abs error (pts) | p90 | Max | Signed mean |
|---|---|---|---|---|
| Random pairing given availability (corrected) | 19.7 | 29.0 | 34.5 | — |
| National-only kernel (corrected) | **3.38** | 9.78 | 21.58 | −3.04 |
| Raw per-metro dial (corrected) | **2.52** | 7.08 | 13.14 | −1.61 |
| Shrunk dial — the shipped kernel (corrected) | **2.63** | 7.21 | 13.16 | −1.73 |
| The metro's own observed 2020–24 rate (corrected) | 2.47 | 7.85 | 13.51 | — |
| National-only (uncorrected) | 4.58 | 10.02 | — | +3.60 |
| Raw dial (uncorrected) | 5.46 | 10.59 | 16.04 | +5.74 |
| Shrunk dial (uncorrected) | 5.84 | 10.76 | 15.26 | +5.57 |
| Observed 2020–24 (uncorrected) | 6.39 | 11.24 | 18.27 | +6.61 |

Paired, metro by metro: shrunk vs national-only 87–37 (median paired
difference −0.71 points, sign test p < 0.001); shrunk vs raw dial 53–71
(+0.02, p = 0.13); raw vs national 88–36. The shrunk kernel lands within
2 points of Pew in 50 of 124 metros (national-only: 37). Its worst
misses are all under-predictions of high-intermarriage metros — Santa
Maria–Santa Barbara (Pew 30%, predicted 16.8%), Palm Bay (29 → 16.2), El
Paso (22 → 9.6), Ogden (27 → 15.3), Fayetteville NC (29 → 18.9), Miami
(24 → 14.1) — and its largest gains over national-only are the metros
where local composition alone misleads: Honolulu (Pew 42%; national-only
20.4%, shrunk 32.9%), Albuquerque, San Diego, San Francisco, Tucson. The
signed means say the national-row correction slightly over-corrects
(−1.7 points for the shrunk model); it was fixed a priori and not moved.

The composition check behind the design, re-derived on the 124: the
random-pairing expectation explains **R² = 0.196** of Pew's variation
(brief: ≈ 0.17); the availability-adjusted ratio of observed to random
spans **0.156 to 1.049** across the 387 metros (median 0.485; the brief's
0.05–0.97 came from the m2 stock cells); one national multiplier on local
composition (ρ = 0.42) misses by a median **3.94** points (p90 9.58, max
20.3), off by more than 1.5× in **25%** of metros; Jackson, Mississippi:
Pew 3%, one-multiplier 15.9%, national-only kernel 10.3%, shrunk kernel
8.3%, and the site's own 2020–24 recent-union rate 12.5% (corrected 8.4%)
— the 2020–24 data themselves place Jackson well above Pew's 2011–15
figure, so no model built on them reaches 3%.

Face validity, on the shipped kernel and on every fitting sample: a
30-year-old's age multiplier peaks at 30 for both sexes (the
availability-weighted partner-age distribution peaks at 30 too); the
education matrix is diagonal-dominant in every row; every race group's
own-group multiplier exceeds each of its off-diagonals, for men and for
women. All pass.

## 3. How much of each city is local

The two facts the design rests on, verified on this phase's own tables
(the brief's figures — median effective sample 2,459, min 675, relative
MOE median 9.4% — describe the m2 stock cells; the kernel's universe is
opposite-sex couples with both members 18–70, and its default sample is
recent unions, which is thinner):

- **Every metro clears the n ≥ 100 gate on its couples.** Recent unions:
  allocated couples per metro median **469**, min **55**; Kish effective
  couple-sides median **520**, min **105**; no metro below 100. The
  out-group share's relative MOE is **16.4%** at the median, 27.2% at
  p90, worst 45.9%. The stock: Kish sides median 2,355, min 549 (the
  brief's 2,459 / 675, on a looser universe).
- **The same sample split into kernel cells leaves nothing to fit on.**
  Recent unions per metro spread over the 20 marginal cells the brief
  counted (two sexes × eight race groups plus four education levels) give
  the median metro **23 couples per cell** and the smallest **3** (brief,
  on the stock: 123 and 34); at the (sex × race) grain the median metro's
  median cell holds 14 sides and its smallest non-empty cell 1.

So the shape is national and each metro carries one dial per component —
a power on that component's log multipliers, fitted by maximum likelihood
on the metro's own couples against its own single population, with
precision from the observed information rescaled to the replicate-
measured effective couple count (the marginals table's 80-replicate MOEs;
no new data), shrunk by empirical Bayes toward the precision-weighted
mean dial across metros. That centre is **0.994 for age, 0.957 for
education, 0.900 for race** — the national kernel, fitted against
national availability, over-predicts own-group pairing in the typical
metro by roughly a tenth of the race log-multiplier, and shrinking toward
exactly 1 would have pulled every metro toward that bias (a finding; the
centre is the one deviation from the brief's literal "toward national",
recorded below).

All three components were tested identically: leave one metro out, split
its couples in half by household, fit the component's dial on one half,
score the other half's couples under the national kernel, the raw dial
and the shrunk dial; both directions, all 387 metros.

| Component | τ (between-metro sd of the dial) | Held-out gain, shrunk − national (per 1,000 weighted sides) | Raw − national | Metros shrunk > national | Metros shrunk > raw | Earns a dial |
|---|---|---|---|---|---|---|
| Race / ethnicity | 0.130 | **+5.99** | +5.23 | 249 / 387 | 246 / 387 | yes |
| Age gap | 0.065 | +1.52 | +1.03 | 243 / 387 | 237 / 387 | yes |
| Education | 0.078 | +0.58 | **−0.55** | 204 / 387 | 256 / 387 | yes (narrowly) |

Race earns its dial decisively, as expected. **Age earns one too**, which
the brief did not expect: a modest but consistent gain in 63% of metros.
Education's raw dials overfit (raw is worse than the national kernel
out of sample) and only shrinkage makes them useful — the component
clears the rule (better in total and in 204 of 387 metros) narrowly, and
its dials are the most heavily shrunk. All three ship; the rule is the
pre-stated one (shrunk beats national in total and in more than half the
metros), not a threshold chosen after the fact.

**Shrinkage per metro** (`results/phase3/dials_recent.csv`; prior share =
the fraction of the dial that is national prior rather than local data):

| Component | Prior share p10 / median / p90 | Metros > 90% prior | Metros > 50% prior | Shrunk dial p10 / median / p90 |
|---|---|---|---|---|
| Race / ethnicity | 0.05 / **0.27** / 0.53 | **0** | 50 | 0.73 / 0.89 / 1.05 |
| Age gap | 0.10 / 0.38 / 0.58 | 0 | 107 | 0.92 / 0.99 / 1.06 |
| Education | 0.28 / 0.69 / 0.85 | **4** | 292 | 0.90 / 0.95 / 1.01 |

Four metros run mostly on the national prior, all for education alone;
no metro is more than 90% prior for race or age. The most local race
dials are New York (0.4% prior), Los Angeles (0.7%) and Chicago (0.8%);
the most prior-driven are Lewiston–Auburn, ME (80%: a raw dial of 1.47
shrunk to 1.01), Parkersburg, WV (77%) and Eagle Pass, TX (76%). The
least racially assortative metros given their own availability are
Huntington–Ashland (0.50), Honolulu (0.53) and Bremerton (0.57); the most
are Athens, GA (1.30), Morristown, TN (1.23) and Memphis (1.20).

## 4. What changed for the visitor

**Rank before and after across the 193**, under the stated default search
(a woman of 30 seeking men 28–40, never or previously married), the
m2.4.0 engine on build 5d0e3ca2f708 against m3.0.0 on this build
(`results/phase3/rank_shift_default.csv`): **193 of 193 ranks move**,
Kendall τ **0.399**, median absolute move **34 places**, largest **118**.
Swapping a 0.25-weight percentile-ranked feature for an unrelated one is
a broad reshuffle by construction (the Phase 2c balance redefinition moved
cities up to 94 places at τ 0.28–0.86). The ten biggest moves: Durham
167 → 49, Columbia SC 176 → 60, Green Bay 55 → 171, Memphis 149 → 35,
Gainesville 173 → 59, Tallahassee 180 → 69, Baltimore 124 → 21, Salinas
46 → 148, Birmingham 172 → 71, Richmond 146 → 47. The top ten go from
San Francisco, Seattle, Los Angeles, San Diego, San Jose, Austin,
Portland, Phoenix, Denver, New York to **New York, Boston, Chicago, San
Francisco, Philadelphia, Los Angeles, New Orleans, Austin, Seattle,
Atlanta** — the West Coast's favourable sex ratios stop counting and the
East's age composition around a 30-year-old woman's partners starts to.

**The two poles do not say one thing.** Across the ranked set the index
and log pool size correlate at **r = 0.344** (Spearman 0.335) for the
default search; over a 153-seeker battery (both sexes, ages 25–50, every
disclosure combination sampled) the median correlation is **0.04**, the
range −0.43 to +0.43, p90 |r| 0.36, and **no seeker exceeds 0.7** — the
item 4 stop condition never approached. The index itself, for the default
search, runs 83.3 (Salinas) to 115.1 (Ann Arbor), p10/p50/p90 =
89.4 / 96.3 / 106.8, with a served margin of 4.0 index points at the
median; Fort Collins, Raleigh, Tuscaloosa and Boston follow Ann Arbor.

**The four degradation paths.** Both disclosed, education only, race only,
neither: all four answer, all four suppress the same metros (the gate
never sees the weights), each is pinned in the goldens (vectors
`self_edu_and_race`, `self_edu_only_hs`, `E_black_woman29_stress`, and
every other vector), and the undisclosed kernel is asserted equal to the
population-weighted mixture of the disclosed ones
(`test_seeker_weights_four_disclosure_combinations`).

**Latency.** On the same 400-query battery as m2.4.0 (`api/tests/measure_latency.py`, single
process through the ASGI stack, warm), on an idle machine: **p50 28.15 ms,
p95 36.44 ms, p99 43.18 ms, max 47.77 ms** against the 60 ms
budget (m2.4.0: 23.5 / 31.5 / 37.3 / 39.3). The weighted path — the reduced-
cube slice, six einsums over 1,696 cells per metro and the seeker mixture —
costs about five milliseconds at p95; no precomputed partial sums were
needed. (A first reading taken while the kernel run's eight workers held
the machine at a load average of 43 gave p95 234 ms and is kept as
`latency_phase3_under_load.json` for the record; it measures the load, not
the path.)

## The kernel, in full

**Fitting sample.** Six samples were fitted, dialled and tested identically; **recent unions
ship**, and the choice was made by the brief's own rule rather than by
the Pew sweep. The rule: the recent sample ships unless its counts and
margins cannot support a stable fit — the IPF converges (it does, in 7 + 2
iterations), face validity passes (it does), every education cell and
every own-group race cell holds at least 100 effective couple-sides (the
thinnest education cell holds 6,638, the thinnest own-group race cell
178, so 0 own-group cells fall short), and no metro's couples fall below 100
Kish sides (0 do). It supports the fit. Had it not, the time-weighted
sample with the smallest out-of-sample Pew error would have shipped, and
that sweep is reported in full because it says something the brief should
know. Corrected median absolute error of the shrunk kernel against Pew,
by sample: recent unions **2.63** (raw 2.52, national-only 3.38, p90 7.21); decay, half-life 5 y **2.48** (raw 2.48, national-only 3.33, p90 7.11); decay, 10 y **2.44** (raw 2.34, national-only 3.34, p90 6.78); decay, 20 y **2.28** (raw 2.28, national-only 3.32, p90 6.43); decay, 40 y **2.19** (raw 2.16, national-only 3.31, p90 6.33); the stock **2.32** (raw 2.3, national-only 3.32, p90 6.29). **The Pew fit improves almost monotonically as older
unions enter the sample**, and the criterion "half-life chosen by
out-of-sample fit on item 11" would pick a 40-year half-life — a sample
in which a union formed in 1985 carries about half the weight of one
formed in 2023, close to the stock the brief rejects. The reason is a
confound, not a discovery: Pew's newlyweds are unions of 2011–2015,
exactly the unions the longer half-lives add back, so a criterion that
rewards proximity to the test period cannot tell "describes current
pairing better" from "sits closer to 2011–15". The national-only kernel
scores 3.31–3.38 on every sample, so the sweep's movement is all in the
dials. The stock is never shipped (a 1985 marriage voting as loudly as a
2024 one), and the recent sample's price is thinner small-group cells:
two empty race cells against none in the stock, 31 race cells under 30
effective sides against 14.

| Sample | Allocated sides | Kish sides | Non-empty national cells | Race cells: empty / < 30 effective / floored | Gap cells < 30 effective | Edu cell rel. MOE max | Race cell rel. MOE median / p90 | National out-group share | Face validity |
|---|---|---|---|---|---|---|---|---|---|
| **recent** (MARHYP ≥ 2019 + all unmarried partners) | 986,770 | 535,834 | 246,038 | 2 / 31 / 2 | 76 | 2.0% | 10.2% / 40.9% | 23.9% | ✓ |
| decay, half-life 5 y | 1,385,259 | 974,834 | 485,492 | 0 / 19 / 0 | 69 | 1.5% | 8.3% / 43.9% | 22.0% | ✓ |
| decay, half-life 10 y | 2,018,560 | 1,459,108 | 485,492 | 0 / 15 / 0 | 67 | 1.2% | 7.2% / 40.7% | 20.4% | ✓ |
| decay, half-life 20 y | 2,799,230 | 1,926,577 | 485,492 | 0 / 14 / 0 | 66 | 1.1% | 6.4% / 38.5% | 18.8% | ✓ |
| decay, half-life 40 y | 3,495,337 | 2,203,013 | 485,492 | 0 / 14 / 0 | 64 | 1.0% | 5.9% / 38.0% | 17.8% | ✓ |
| stock (every union) | 4,591,004 | 2,410,640 | 485,492 | 0 / 14 / 0 | 63 | 1.0% | 5.7% / 38.5% | 16.7% | ✓ |

The recent sample's thin cells are the small-group off-diagonals — 31 of
the 128 race cells hold fewer than 30 effective couple-sides and two are
empty (men of another race with Pacific Islander partners, Pacific
Islander women with partners of another race; both floored at 1e-4) —
and the twelve age gaps of 50 years or more. Its 4×4 education table is
measured to 2% relative MOE in every cell. The IPF converged in 7 raw
iterations plus 2 after the age term was fixed (final change 6e-7).

**Age.** The gap term is sex-asymmetric and peaks at the seeker's own
age for both sexes: women's multipliers run 3.45 at a partner two years
younger, **6.25 at the same age, 5.98 one year older**, 4.03 three years
older, 1.06 ten years older and 0.20 ten years younger; men's run 4.90
two years younger, **7.32 at the same age**, 4.41 one year older, 1.28
five years younger... the asymmetry the brief expected, in the data. The
smoothing bandwidth was chosen per sex by leave-one-gap-out Poisson
deviance over {0.25, 0.35, 0.5, 0.75, 1, 1.5, 2, 3, 5} years and the
cross-validation chose the **smallest candidate, 0.25 years, for both
sexes** — the deviance flattens below 0.5 (210 / 210 / 212 thousand for
0.25 / 0.35 / 0.5 against 335 at 1 and 4,847 at 5): the gap cells are
measured well enough that the data prefer essentially no smoothing, and
what smoothing remains is a nearest-neighbour blend that only matters in
the tails. The brief asked for the fitted curve against raw gaps at
seeker ages 25, 35 and 50 (`kernel_age_curves_recent.csv`): the fitted
partner-age distribution peaks at the seeker's own age in all six cases,
but the **shift-invariant gap term is the separability failure that
matters most** — 25-year-old men put 26.3% of their partners at exactly
their own age against a fitted 16.6% (women 20.3% vs 15.4%), while
50-year-olds put 8.9% (men) and 10.1% (women) there against fitted
14.3% and 13.2%: the young pair far more tightly in age than a single
gap curve allows, the old more loosely. A gap term that varies with
seeker age is the obvious next refinement; it was not in scope.

**Education** (odds multipliers relative to random pairing given
availability; seeker's level down the side, partner's along the top):

| | High school or less | Some college | Bachelor's | Graduate |
|---|---|---|---|---|
| High school or less | **1.52** | 0.84 | 0.48 | 0.37 |
| Some college | 0.82 | **1.38** | 0.88 | 0.70 |
| Bachelor's | 0.42 | 0.82 | **2.08** | 1.91 |
| Graduate | 0.30 | 0.61 | 1.72 | **4.06** |

**Race and ethnicity**, per direction and per seeker sex (the mirror cases
differ measurably, as the brief anticipated — Black women pair within the
group at 5.4× random and Black men at 3.5×; Asian men at 12.6× and Asian
women at 9.1×; a white woman's multiplier for a Black partner is 0.20 and
a white man's for a Black partner 0.06):

Women seeking (rows) → partner's group (columns):

| | Hispanic | White | Black | Asian | Native American | Pacific Islander | Two or more | Another race |
|---|---|---|---|---|---|---|---|---|
| Hispanic | **3.17** | 0.41 | 0.23 | 0.21 | 0.56 | 0.46 | 0.59 | 0.57 |
| White | 0.36 | **1.63** | 0.20 | 0.19 | 1.08 | 0.44 | 0.94 | 0.21 |
| Black | 0.19 | 0.17 | **5.41** | 0.09 | 0.34 | 0.30 | 0.60 | 0.30 |
| Asian | 0.43 | 0.61 | 0.19 | **9.06** | 0.52 | 1.61 | 1.09 | 0.38 |
| Native American | 0.59 | 0.78 | 0.26 | 0.25 | **91.4** | 2.08 | 1.00 | 0.25 |
| Pacific Islander | 0.53 | 0.42 | 0.43 | 0.68 | 0.27 | **272.0** | 1.27 | 0.00 |
| Two or more | 0.55 | 0.95 | 0.74 | 0.44 | 1.15 | 1.55 | **5.76** | 0.66 |
| Another race | 0.64 | 0.41 | 0.45 | 0.23 | 0.38 | 0.24 | 0.66 | **89.5** |

Men seeking (rows) → partner's group (columns):

| | Hispanic | White | Black | Asian | Native American | Pacific Islander | Two or more | Another race |
|---|---|---|---|---|---|---|---|---|
| Hispanic | **3.31** | 0.45 | 0.07 | 0.40 | 0.76 | 0.52 | 0.56 | 0.51 |
| White | 0.36 | **1.73** | 0.06 | 0.49 | 1.04 | 0.33 | 0.90 | 0.28 |
| Black | 0.40 | 0.40 | **3.45** | 0.29 | 0.70 | 0.77 | 1.04 | 0.48 |
| Asian | 0.34 | 0.37 | 0.05 | **12.62** | 0.44 | 0.88 | 0.68 | 0.27 |
| Native American | 0.45 | 0.93 | 0.09 | 0.34 | **92.6** | 0.67 | 0.87 | 0.31 |
| Pacific Islander | 0.51 | 0.52 | 0.14 | 1.57 | 2.31 | **232.7** | 1.74 | 0.24 |
| Two or more | 0.60 | 1.05 | 0.26 | 0.97 | 1.09 | 1.02 | **5.66** | 0.55 |
| Another race | 0.82 | 0.36 | 0.20 | 0.47 | 0.38 | 0.00 | 0.92 | **100.4** |

The very large own-group multipliers for the three small groups are what
"relative to random pairing given availability" means when a group is
under 1% of the single population: pairing within it happens dozens of
times more often than availability alone would produce.

**Separability.** The saturated national table against the multiplicative
fit, on the two-way interactions the separable form does not carry
(`kernel_report.json`; cells thinner than 30 couples in weight units are
not named):

| Interaction the model omits | G² | Share of couples misallocated | Share of couples in thick cells off by > 25% |
|---|---|---|---|
| Education pairing × seeker sex | 194,581 | 3.7% | 0.6% |
| Age gap × seeker education | 363,545 | 4.4% | 6.3% |
| Age gap × seeker race | 146,523 | 2.6% | 3.0% |
| Race pairing × education pairing | 958,858 | **7.2%** | **16.1%** |
| Own-group pairing × seeker age cohort (race) | 164,368 | 2.4% | 2.3% |
| Same-education pairing × seeker age cohort | 176,052 | 3.1% | 3.7% |

Where the multiplicative form fails most: **race and education pairings
interact** — 16% of couples sit in thick cells the separable model
misses by more than a quarter (the worst: white-man × Asian-woman couples
where both hold graduate degrees, observed at 0.36 of the fitted count,
and the mirror). The education matrix pooled over sex (the brief's
specification) misses a real asymmetry — women with a bachelor's degree
partnered to men with graduate degrees are observed at 0.83 of fitted,
men with graduate degrees partnered to women with some college at 0.76.
Age gaps depend on education (men with graduate degrees rarely have
partners more than ten years older: 0.43 of fitted) and, as the age
curves show, on seeker age. Each is a candidate for a later interaction
term; none was added, because the brief's form is the separable one.

## Deviations, findings and judgment calls

1. **The raw PUMS zips were not cached.** The extractor evicts them after
   parsing by design, so item 1's "re-parse" was a re-download plus
   re-parse: 514 s wall-clock, every zip SHA-256- and byte-identical to
   the Phase 1 manifest, 14,396,271 rows both times, zero rows differing
   on any pre-existing column.
2. **The couple clock is the reference person's MARHYP.** Within every
   married couple in the extract the two spouses' MARHYP agree (0
   discordant of 5,924,666 married sides), so the choice never bites.
   Unmarried partners have no formation year in PUMS and enter every
   sample at weight 1 (treated as current unions).
3. **Same-sex couples (117,522 sides, 1.8%) are counted and excluded from
   the fit**; the kernel is applied to same-sex searches unchanged, using
   the seeker's own-sex terms. Recorded as a limitation, not modelled.
4. **The shrinkage centre is the precision-weighted mean dial (0.99 /
   0.96 / 0.90), not exactly 1.** DerSimonian–Laird estimates τ² around
   that mean; shrinking toward 1 while estimating spread around 0.90 is
   internally inconsistent and would bias every metro toward a national
   kernel that over-predicts own-group pairing in the typical metro.
   Measured, then decided; a first run with the centre at 1 gave the same
   Pew medians to 0.01.
5. **The held-out metro's τ² and centre** come from the other metros'
   full-sample dials (fitted against the full national kernel), not from
   dials refitted against each leave-one-out kernel — an approximation
   that saves 387 × 386 dial fits and moves nothing visible.
6. **"Raw per-metro" in the Pew table is the raw-dial kernel**; the
   metro's own observed 2020–24 out-group share (the rawest possible
   per-metro figure) is reported beside it.
7. **The level offset is Pew's national row, an integer percent** (16),
   so the correction ratio 1.49 carries about ±3%; the correction is
   multiplicative, fixed a priori, and over-corrects by 1.7 points on
   average — reported, not moved.
8. **Two of Pew's 126 metros do not match** the site's 2023-delineation
   CBSA codes and are dropped (124 compared).
9. **The smoothed IPF as a fixed-point iteration converged too slowly**
   (200 iterations without meeting tolerance); the age term is smoothed
   once at the raw solution and the other two components refitted around
   it (2 iterations). The cross-validation chose the smallest bandwidth
   offered; the grid was extended downward to 0.25 to show the flattening.
10. **Education is pooled over sex** because the brief specified a single
    4×4; the sex asymmetry it misses is quantified in the separability
    table rather than modelled.
11. **All three components earned a dial** under the pre-stated rule; the
    brief expected age not to. Education's is narrow and its dials are
    mostly prior.
12. **The served index is normalised per search** (100 = the national
    average for the visitor's own search) on top of the kernel's own
    per-seeker mean-1 normalisation; Nathan's definition says "where 100
    is the US average", and only the per-search version makes that
    exactly true for a filtered search. Rankings are unaffected (a
    constant factor per request); levels are.
13. **The undisclosed kernel is a mixture of mean-1 kernels** weighted by
    the national single population of the seeker's own sex and age — the
    "population-average marginal" made concrete; the mixture identity is
    asserted in the engine tests.
14. **The match figure's bands are the stat's position within the query's
    ranked set** (the registry's five standing edges and five labels),
    since a per-request quantity has no national standing column.
15. **The balance pillar's What-we-measure sentence moved to the feature's
    definition**, so the page's card reads exactly as before; the feature
    row is now `context_only` at weight 0 under the context pillar.
16. **The sensitivity reference search** is the site's default window
    relative to the seeker's age, both sexes, all ages within each band —
    a choice the brief left open, recorded in `sensitivity.json`.
17. **Rank stability fails** (finding 2). The gate is untouched.
18. **The Pew bar's second clause is a tie, not a win** (finding 1).
19. **The old build 5d0e3ca2f708 is retired** to manifest + metros.json
    (the 2g pattern); 674aa70fc57c stays complete, as PHASE2D decided.
20. **`build_stat_pages.py` picks the newest complete build** when no path
    is given (it used to hard-code the build id); the name is printed.
21. **Three stale git lock files dated 2026-09-18** (index, HEAD,
    maintenance) blocked the first commit and were removed; no git process
    was running.
22. **The panel's pre-existing labels stay hard-coded** ("I'm a", "My
    age", "Education", "Earning at least"); every string introduced this
    phase is registry-owned, including the pole labels, which the panel
    used to type itself.
23. **The methodology page changed in exactly three places**: the kernel
    section (the registry's account, verbatim), the slider sentence, and
    the balance paragraph's "not part of the score" — the copy the brief
    required and nothing else.
24. **features.parquet is not byte-identical** to 5d0e3ca2f708's: the
    three interim pairing columns differ at the last float digit after
    the rebuild (all 387 rows equal to 1e-9); every other column is
    bit-identical, and the three cubes are.
25. **Two m3.0.0 builds were made.** The kernel run writes a provisional
    artifact after the recent sample so the build chain could start while
    the other five samples ran; the run's own final step shipped the
    Pew-best sample (decay, 40 y) under the rule as first coded, and the
    stated rule was then applied by `kernel.py ship recent`. The final
    artifact equals the provisional one to floating-point noise (log
    multipliers within 1e-15, dials and normalisers identical; only
    `generated_at` and the provisional flag differ), so build
    b7f53afb9997 and the shipped 59fd352c5c2f serve identical figures —
    zero golden expectations differ between them. b7f53afb9997 is retired
    with 5d0e3ca2f708.

## Screenshots (results/phase3/)

01 the panel with the two optional inputs and the renamed poles · 02 a
result row with the figure, its band and the balance tally · 03 the
information box open · 04 the default search with education and race
disclosed · 05 the city ranked card · 06 the compare table's new row ·
07 What we measure's people group · 08 How it works.

## Gate check

1. Kernel fitted on recent unions (the default; the four half-lives and
   the stock fitted, tested and reported beside it), availability-
   adjusted, normalised to 1 per seeker over the national single adult
   population, all three components reported in full, separability test
   run. ✓
2. Every metro carries a dial for each of the three components (all three
   earned one); shrinkage reported per metro in `dials_recent.csv`; no
   metro excluded — the smallest has 55 allocated couples and 105 Kish
   sides. ✓
3. Out-of-sample Pew reproduction: beats national-only materially (2.63
   vs 3.38 median, 87–37, p < 0.001) and the brief's 4.1-point baseline;
   **ties raw per-metro** (2.63 vs 2.52, 53–71, p = 0.13) — the second
   clause of the bar is not met as written; error distributions reported
   for three models plus random pairing and the observed rate; the only
   correction is one constant from Pew's national row. **Nathan's call.**
4. `match_propensity` is a rate over the visitor's own matched pool,
   served as an index with 100 the national average for that search;
   its correlation with pool size is 0.34 on the default search and 0.04
   at the median of a 153-seeker battery, never above 0.7. ✓
5. All four seeker-attribute combinations answer correctly and suppress
   identically on the unweighted n (tested in the engine, the API and the
   goldens). ✓
6. The per-level sensitivity table covers every level of all three
   components in one format; the systematically large effect is named
   (race, a median of 23 index points, the top city changing at every
   level); no component carries a switch, gate or caveat the others lack
   (registry, estimation and serving path all uniform). ✓
7. Latency: p95 36.44 ms on the 400-query battery, under the 60 ms budget. The weighted-path mask-axis test passes, and
   the cube-vs-SQL differential now runs the kernel-weighted sum both
   ways on the same 40 shapes (worst relative error 2e-7). ✓
8. Balance displayed everywhere it was — result rows, the city ranked
   card and the balance-survives card, the compare table, What we measure
   — scored nowhere (`context_only`, weight 0, absent from the scored set
   and the weights; asserted); no copy still calls it part of the score
   (the methodology page's paragraph now says so in words). ✓
9. The kernel's plain-words account naming all three inputs is on How it
   works and the methodology page (one text, the registry's `match_how`)
   and reachable from the stat's information box; the registry owns every
   new string (loader-asserted); axe zero serious/critical across the ten
   page shapes; the banned-vocabulary sweep returns zero across eleven. ✓

And the project's standing battery: **8 of 9 hard gates pass; rank
stability fails** (finding 2) — reported, not tuned.
