# Phase 3d — the kernel fit gets fast and finishes; a photo-finish verdict flips and Nathan's tie rule settles it; m3.4.0 ships the finished fit and m3.5.0 scores chances of matching by value

Every number here is read from a file under `results/phase3d/` (or a
committed record it names); nothing was recomputed for the report.

**In plain words, for Nathan.** The model that turns the Census's couples
into the chances-of-matching figure now fits in about a second instead
of several minutes and gives the same answers as before to more decimal
places than anyone reads (Part A, stage 1). Stage 2 let it run to its
proper finish: the old fit always stopped at a fixed pass count while
still creeping, because part of the model was moving in directions the
data cannot see; those directions are now taken out and the fit
converges in eighteen passes. Re-running the decisions behind the
current site on the finished fit flipped one of them by a hair — two
versions of the age term that had tied to the third decimal swapped
places by 0.007 of a point per 1,000 couples — and the brief made that a
halt. Your rule settled it: a held-out difference smaller than a quarter
of a point per 1,000 couples is a tie, and a tie goes to the simpler form
(ADR 0014). The rule is anchored to what finishing the fit itself moved,
to the survey noise in the comparison and to the smallest margin that has
ever decided a served term; it was written after the flip was seen and
says so; and every decision on the record comes out the same for any
margin between about 0.007 and 2.9, so nothing hangs on the exact number.
Under it the simpler form — C1, the one the site already served — ships
as m3.4.0: the same ten cities in the same order on the default search,
the index moving a median 0.02 points, ten of ten hard gates, and the
site answering in 36 ms at the 95th percentile against a 100 ms budget.
Part B then scored chances of matching by its value instead of its rank,
choosing among four candidates by a rule committed before any of them
was measured. One qualified: the version that clips each search's
far-out cities to fences set by that search's own spread. It makes
rankings 20% steadier across the 516 test searches and 7% steadier at
the slider's match end, keeps the middle of every field about 42
points wide at its narrowest, and lets a real lead count as large while a near-tie no
longer flips a rank at full weight; the two candidates that were steadier
still were disqualified because they squeezed the field on searches with
runs of extreme cities. It ships as m3.5.0. The served index, its display
cap, suppression, bands and the kernel are untouched — only the way the
figure enters the score changed — so rankings move: on the default search
a median of 3 places, with Washington DC replacing San Jose at 10th; 95
test searches got shakier by more than 25% and are named in section 3 as
findings, the two at the slider's match end among them. The stability
reference stays m3.2.0 as the brief says; the new build sits 22% below it,
and whether to re-base is your call. Nothing is deployed.

## 1. The speed-up (Part A)

### A1 — the same fit, computed differently (commit efd93d7)

**What changed.** The sweep keeps one model table between component
updates and moves it in place — a component's change is a per-seeker
factor over the partner axes it keys on, the rows re-normalised — and
takes margins by reshape-sum over the seven-axis view, instead of
regathering the four log-kernel blocks and exponentiating the whole
3,392 × 1,696 table at every step (`kernel_refine.Table`). Two stopping
rules live side by side: m3.3.0's (`stop="cell"`, the largest single
cell change below 1e-6, kept for the reproduction) and the new one
(`stop="couples"`): a stage stops when fewer than one fitted couple-side
in ten million moved between cells over a pass (`COUPLE_TOL` 1e-7), the
interaction stage also waiting for the penalised objective's gain per
pass to fall below 1e-6 per 1,000 couple-sides. The leave-one-metro-out
refits warm-start from the smoothed-stage terms and stop on the same
rule, the 25-sweep cap gone.

**Proof 1 — the refactor reproduces m3.3.0** (`a1_reproduction.json`,
the m3.3.0 fit store as the reference, the old rule kept):

| Fit | Largest difference from the m3.3.0 store | Bandwidths | Passes (raw / smoothed / interaction) |
|---|---|---|---|
| The shipped form (C1) — raw, smoothed and gauged log multipliers, 387 × 3 dials | **6.3e-10** (the dials; every log multiplier within 1.4e-12) | equal | 200 / 4 / 200, as m3.3.0 |
| The same-sex block — smoothed and gauged log multipliers | **4.4e-12** | equal | 200 / 200, as m3.3.0 |

**Why the old rule ran to its cap** (`a1_trajectories.json`, every
pass's largest cell change, couple-weighted move and objective): on the
shipped form's raw stage the table's move per pass fell below 1e-7 at
pass 7 and sat at 7e-12 from pass 11 on, while the largest cell change
stayed at exactly 1.21e-5 for the remaining 190 passes — one near-empty
gap cell crawling, worth 3e-9 per 1,000 couple-sides of objective per
pass. The same-sex fit's smoothed stage did the same at 1.02e-6, a hair
above the 1e-6 tolerance, for 196 passes at no gain at all.

**Proof 2 — the new rule** (`a1_new_rule.json`):

| | Shipped form (C1) | Same-sex block |
|---|---|---|
| Passes, raw / smoothed / interaction | 7 / 4 / 200 (cap) | 7 / 4 |
| Penalised objective against the m3.3.0 fit, per 1,000 couple-sides | **−2.8e-7** (−0.0094 of 5.3e8) | **−5.7e-8** (−8e-5 of 2.4e7) |
| Largest change in any log multiplier | 0.0023 — that one crawling gap cell of the raw age term; every education, race and interaction cell within 8e-10 | 0.0004 (race), 0.0002 (age) |
| Largest change in any dial (θ̂ / θ̃) | 3.4e-8 / 1.1e-8 | — |
| Bandwidth choice at raw tolerances 1e-3 … 1e-8 | identical to m3.3.0's at every one (4 to 8 raw passes) | identical at every one |
| Goldens under the refitted kernel (sliced to the fixture in memory, `a1_goldens_check.json`) | unchanged: largest score difference 0.0, largest index difference 0.0 | — |

The objective is very slightly **lower**, not higher: the whole
difference is the crawling cell, which m3.3.0 moved for 193 more passes.
It is 3,500 times below the precision at which any held-out gain is read
(1e-3 per 1,000 sides) and moves no golden; it is reported as the
finding it is rather than recovered by running the raw stage to the cap
(deviations). The interaction stage still stops on its cap under the new
rule — at pass 200 the table still moves 2e-6 per pass and the objective
still gains 7e-5 per 1,000 sides per pass, the slow directions A2
removes.

**The LOMO re-score** (`a1_rescore.json`; the a1 store's refits under
the new rule, the leave-one-metro-out refits warm-started and
tolerance-stopped):

| Form | Held-out gain over the shipped form, per 1,000 sides (Phase 3c) | Metros better (3c) | Pew corrected median, points (3c) |
|---|---|---|---|
| baseline | −14.107 (−14.134) | 37 (37) | 2.48 (2.48) |
| C1 — the cohort age term | **+69.705** (+69.705) | 386 (386) | 2.51 (2.52) |
| C2 — the sex-specific education matrix | −0.003 (−0.003) | 196 (194) | 2.50 (2.50) |
| C3 — both | +69.705 (+69.704) | 386 (386) | 2.51 (2.52) |

The same-sex education term on what m3.2.0 serves: +9.05 per 1,000
sides with the interaction off (271 of 387 metros better; Phase 3c +6.98,
266) and +15.49 with it on (304; Phase 3c +15.90, 301); the interaction
rides by +6.43 (Phase 3c +8.92). Every Phase 3c verdict re-scores the
same: C1 ships as the larger of the two qualifying gains (C1 leads C3 by
0.0003), C2 does not improve on the shipped form, the same-sex education
term ships with the interaction riding.

**Timing** (`timing_old_code.json`, `a1_reproduction.json`,
`a1_new_rule.json`, `a1_rescore.json`; this machine carried other work
throughout, one-minute load 2.3–3.2 during the single fits and 12–15
during the LOMO runs, so the m3.3.0 code was re-timed here beside the
Phase 3c record):

| | Phase 3c record | m3.3.0 code, this machine | New engine, old rule | New engine, new rule |
|---|---|---|---|---|
| The shipped form's fit | 153.5 s (with its report tables) | 290.9 s | 26.6 s | **13.8 s** |
| The same-sex fit | 113.3 s (with its report tables) | 229.8 s | 21.9 s | **1.3 s** |
| Leave-one-metro-out, 387 metros, 8 workers | 6,772 s for three interaction forms (Phase 3c) | — | — | 7,871 s for five forms |
| Same-sex fit and LOMO | 1,880 s | — | — | 1,566 s |

**Where the time goes** (the shipped form under the new rule, 13.1 s of
fitting): the interaction stage 12.2 s for its 200 capped passes, the raw
stage 0.55 s for 7, the smoothed stage 0.32 s for 4, the bandwidth CV
0.03 s. Inside the table, applying a component's change costs 6.1 s of
the 13, taking margins 4.8 s, copying the table for the move test 1.7 s,
rebuilding it at stage boundaries 0.4 s; the updates themselves 0.02 s.
Ninety-three per cent of the fit is the interaction stage's slow mode,
and every LOMO refit of an interaction form ran that stage to the
200-pass cap (28.5 s each; the raw and smoothed stages stopped on
tolerance at 4–6 and 2–4 passes in every one of the 387 metros). That is
why A1's LOMO is slower than Phase 3c's despite the faster steps, and it
is the profile A2 answers.

### A2 — the interaction projection (measured; shipped as m3.4.0 after Nathan's decision, below)

**What changed.** After every Newton step on the interaction, the
directions the penalised objective cannot see are taken out
(`kernel_refine.Projection`, built once per form from the 2,048 cells ×
208 indicator columns — seeker type 64, education pair 16 (32 when the
matrix is per sex), race pair 128 — an orthonormal basis of rank 188 by
SVD, with the minimum-norm coefficients that write the projection back
onto the three blocks): the seeker-only part is dropped (a per-seeker
constant the row normalisation absorbs; the ridge wants it at zero), the
education-pair and race-pair parts are added to the main effects (where
an unpenalised optimum puts them), and the cells the step forces to zero
stay zero. The table does not move under the projection and the penalty
falls, so the objective is monotone. The switch is
`PROJECT_INTERACTION` (on); off reproduces A1.

**Proofs 1 and 2** (`a2_proofs.json`, the shipped form):

| | Projection off | Projection on |
|---|---|---|
| Largest difference from the A1 fit (every log multiplier, every dial) | **8.2e-15**, bandwidths equal | — |
| Passes, raw / smoothed / interaction | 7 / 4 / 200 (cap) | 7 / 4 / **18** (tolerance) |
| Penalised objective (weight units, up to the constant) | −529,704,015.22 | −529,703,692.98 — **+322.2, +0.0097 per 1,000 couple-sides** |
| Seconds for the fit, same run | 7.0 | **1.4** |
| Held-out record (C1's LOMO total against the shipped form, per 1,000 sides) | +69.705 (A1) | **+69.707** — it does not fall |

What moved when the blind directions came out: the seeker-only part
dropped was up to 0.107 in log units; the parts moved into the main
effects change the smoothed education and race terms by up to 0.128 and
0.131 (gauged: 0.036 and 0.095) and the dials by up to 0.027 (θ̂) and
0.022 (θ̃) against m3.3.0; the interaction's residual keeps its size (log
sd 0.154 against 0.155, 763 cells above 0.1 in absolute log against 767).
The same-sex block has no interaction and is bit-identical on and off.

**Proof 3 — how far the served numbers would move** (the C1 candidate
artifact with the same-sex decision, loaded into the m3.3.0 build in
memory; `rank_shift_m3_3_0_to_m3_4_0_candidate_C1.json`,
`a2/gate_C1_cohorts_plus_shipped.json`):

| Search | Metros | Ranks changed | Kendall τ | Median move | p90 move | Largest move | Top 10 |
|---|---|---|---|---|---|---|---|
| The stated default (a woman of 30 seeking men 28–40) | 193 | 59 | 0.995 | 0 | 1 | 3 (Deltona 105 → 108, Springfield MO 119 → 122, Scranton 148 → 145, Laredo 170 → 167) | the same ten cities in the same order |
| The same-sex reference (a man of 31 seeking men 27–38, never married, with a degree) | 120 | 33 | 0.994 | 0 | 1 | 2 | San Jose still top by index (115.5) |

The default search's index moves a median 0.02 points (p90 0.11, largest
0.55; range 85.2–111.5 → 85.3–111.5). The disclosed reference searches
keep their top city and, but for one, their count of metros above the
250 cap (San Jose 631.6 → 629.6 for the graduate Asian woman of 30 and
583.8 → 582.2 for the graduate Asian man of 34; Montgomery 317.3 → 317.1
for the Black woman of 30; Fayetteville 2,482 → 2,496 and 1,007 → 1,010
for the Pacific Islander man and woman of 35, the woman's count above
250 falling from 8 to 7; the graduate woman of 30 reads San Jose 190 as
before). **The ADR 0011 gate** against the m3.2.0 reference: all 516
searches touched, total wobble 316.209 → **306.703, ratio 0.970, pass**
(m3.3.0 read 0.971; the old rule's soft reading 0.80 exactly). Against
m3.3.0 itself the candidate is steadier in 248 searches, shakier in 247
and unchanged in 21 (total 307.128 → 306.703); five searches' wobble rose
more than 25% (section 3).

**Proof 4 — the decisions that shaped m3.3.0, re-run on the finished
fit** (`a2_decisions.json`, `a2_rescore.json`; every form refitted with
the projection, the leave-one-metro-out test with tolerance-stopped
refits, candidate artifacts as they would ship, the gate on each):

| Decision | Phase 3b / 3c | On the finished fit | Verdict |
|---|---|---|---|
| Race × education ships (improves held-out fit over the baseline; passes the gate) | +14.13 per 1,000 sides, 350 of 387 metros; old gate 0.800 | **+14.07, 348 of 387; gate 1.002, pass** (the Phase 3b candidate, baseline + interaction, no same-sex terms) | **holds** |
| The same-sex education term ships; the interaction rides | +6.98 / +15.90 on what m3.2.0 serves; the interaction by +8.92 | **+12.26 / +15.16** (276 and 301 of 387 metros better); **the interaction by +2.90** | **holds** |
| Of C1, C2, C3, those improving on the shipped form and passing the gate; the largest gain ships | C1 +69.705 (386), C2 −0.003 (194, does not qualify), C3 +69.704 (386); C1 ships | **C1 +69.707** (386; gate 0.970), **C2 +0.007** (209; gate 0.987, now qualifies), **C3 +69.715** (386; gate 0.976); **the rule picks C3** | **flips** |

C3 leads C1 by 0.007 per 1,000 couple-sides where Phase 3c read C1 ahead
by 0.001, and the sex-specific matrix alone (C2) moves from −0.003 to
+0.007: on the finished fit the matrix adds a little rather than nothing.
The C3 candidate would move served numbers slightly more than C1 (default
search: 72 ranks changed, largest move 5, Washington DC replacing San
Jose at 10th; same-sex reference: 54 changed, τ 0.989; gate 0.976 pass;
against m3.3.0 shakier in 276 searches and steadier in 229, 22 risers
above 25%, the match-end searches 2.88 → 2.98). Pew's corrected median
absolute error reads 2.54 for C1 and C3 (Phase 3c 2.51–2.52), 2.52 for
the shipped form and C2, 2.48 for the baseline.

**Stopped here.** The brief made a flipped verdict a stop condition
("halt before Part B"). m3.4.0 was not built: no version bump, no
goldens, no launch-config change; the projected fits, candidate artifacts,
LOMO records and gate records are all under `results/phase3d/speedup/a2/`
and the A2 code is committed with the projection on by default, which
moves no served number until an artifact is rebuilt and shipped. ADR 0010
is amended to say exactly this. **Nathan's decision:** which form the
finished fit ships — C3 by the rule as written, C1 by judging 0.007 per
1,000 sides too small to change a form (the Phase 3c reading), or a tie
rule for the record — in an ADR; then the ship chain
(`results/phase3d/_ship_m3_4_0.sh <form>`) builds m3.4.0 through the
full battery and Part B runs on it.

### Nathan's decision — the held-out tie rule (ADR 0014)

Everything in this subsection is read from `tie_rule.json`, written by
`tie_rule.py` from the stored records of Phase 3b, Phase 3c and the A2
re-run, with no refit. The rule was written after the flip was seen and
committed (2d2c063) before m3.4.0 was built.

**The rule.** A held-out difference smaller than **δ = 0.25 per 1,000
weighted couple-sides** is a tie, and a tie goes to the simpler form. A
candidate improves on a reference only if it beats it by δ (the gate
requirement is unchanged); among the qualifying candidates every one
within δ of the largest gain is tied for first, and the simplest of those
ships — the nested form first, then the fewer free parameters, then the
lower gate ratio, the form already served, the earlier form in the brief's
table; a yes/no choice (whether a term ships, whether the interaction
rides) takes the richer option only if it beats the simpler one. δ applies
to held-out likelihood comparisons of kernel forms, opposite- and
same-sex; not to the stability gate (ADR 0011), not to Part B's selection
(ADR 0013 has its own margin). It is one constant
(`kernel_refine.HELDOUT_TIE_MARGIN_PER_1000`) behind one pair of functions
(`beats`, `select_form`), which every held-out decision now goes through,
and the kernel record carries it beside the form choice.

**Its anchors** (`tie_rule.json`, `anchors`):

| Anchor | Reading | δ against it |
|---|---|---|
| Fitting-method shift — finishing the fit (the same forms, the same data, the same test) moved the race × education margin over the baseline by **0.066** per 1,000 sides (14.134 → 14.068), the C3 − C1 margin by 0.008 (−0.0005 → +0.0073) and the C2 − shipped margin by 0.010 (−0.0033 → +0.0070) | 0.066 at most | δ is **3.8×** the largest |
| Sampling noise — the paired, metro-clustered standard error of the C3 − C1 difference on the finished fit (the per-metro differences of held-out log-likelihood, same metro left out, same halves, as 387 independent draws); C3 is better in **197 of 387** metros | **0.014** | δ is **17×** it |
| Smallest real decision — the smallest margin that has decided a served term: the interaction riding on same-sex searches, in the A2 records | **+2.90** | δ is **11.6×** smaller |

A finding beside the first anchor, not covered by it: the **same-sex**
margins moved far more than δ between the Phase 3c and A2 records — the
interaction's from 8.92 to 2.90, the education term's from 6.98 to 12.26
with the interaction off and 15.90 to 15.16 with it on. That is not the
optimiser's stopping point: the projection moves the education-pair and
race-pair parts of the opposite-sex interaction into opposite-sex main
effects, and a same-sex search takes its education term from same-sex
couples, so the borrowed interaction carries less on same-sex searches
after the projection than before. A change in what the term contains,
recorded in ADR 0014; the same-sex verdicts hold under δ on both fits.

**The δ interval** (`delta_interval`). Every outcome on the record — what
ships or is served — comes out the same for any δ in **(0.0073, 2.898]**:
below the lower end C3 beats C1 on the finished fit and would ship; above
the upper end the interaction ties with the composition without it on
same-sex searches and would stop riding. Every intermediate reading holds
for any δ in (0.0073, 2.828]; above that the Phase 3b reading of the
sex-specific education matrix (+2.83 over the baseline) becomes a tie,
though its outcome (dropped for the combination's gate failure) is the
same either way. The verdicts do not depend on the exact δ.

**Every held-out decision on the record, under both rules** (margins per
1,000 weighted couple-sides, the richer form minus the simpler; SE the
paired, metro-clustered standard error; "better in" the metros where the
richer form scores higher; from `lomo_forms.json` and `lomo_samesex.json`
in Phase 3b, Phase 3c and the A2 store):

| Decision | Margin | SE | Better in | Old rule | ADR 0014 |
|---|---|---|---|---|---|
| 3b: the cohort age term improves on the baseline | +70.42 | 7.33 | 386 / 387 | improves; held back by the old gate (0.675) | same |
| 3b: race × education improves on the baseline | +14.13 | 2.09 | 350 | improves; gate 0.800; ships | same |
| 3b: the sex-specific education matrix improves on the baseline | +2.83 | 0.28 | 344 | improves; dropped, the combination fails the old gate (0.750) | same |
| 3b: same-sex age beats the opposite-sex fallback | +205.7 | 24.1 | 374 | served | same |
| 3b: same-sex education beats the fallback | +4.28 | 1.80 | 244 | improves; the face check fails; not served | same |
| 3b: same-sex race beats the fallback | +42.6 | 7.96 | 272 | improves; unsupported; not served | same |
| 3c: the same-sex education term improves on what m3.2.0 serves | +6.98 off / +15.90 on | 1.74 / 2.41 | 266 / 301 | ships | same |
| 3c: the interaction rides on same-sex searches | +8.92 | 2.47 | 206 | rides | same |
| 3c: C1 / C2 / C3 against the shipped form | +69.705 / −0.003 / +69.704 | 7.27 / 0.015 / 7.27 | 386 / 194 / 386 | C1 and C3 qualify; C1 ships by the larger gain (0.0005) | C1 and C3 qualify and are tied; C1 ships, nested in C3 |
| A2: race × education improves on the baseline (re-run) | +14.07 | 2.09 | 348 | improves; gate 1.002; ships | same |
| A2: same-sex age / education / race beat the fallback (re-run) | +205.7 / +9.54 / +43.5 | 24.1 / 1.90 / 8.02 | 374 / 257 / 276 | age and education served; race unsupported | same |
| A2: the same-sex education term improves on what m3.2.0 serves (re-run) | +12.26 off / +15.16 on | 1.93 / 2.33 | 276 / 301 | ships | same |
| A2: the interaction rides on same-sex searches (re-run) | **+2.90** | **1.75** | **188** | rides | same (+2.90 ≥ δ) |
| A2: C1 / C2 / C3 against the shipped form (re-run) | +69.707 / +0.007 / +69.715 | 7.27 / 0.015 / 7.27 | 386 / 209 / 386 | all three qualify (gates 0.970 / 0.987 / 0.976); **C3 ships** by the larger gain (0.0073) | C2 does not qualify (0.007 < δ); C1 and C3 tied, 0.007 apart; **C1 ships, nested in C3** |

Simplicity is read from the Form: C1 is nested in C3 (C3 only adds the
per-sex matrix), which settles the tie before any count. The counts are
on the record all the same — C1 5,520 free parameters, C2 2,192, C3
5,520, the shipped form 2,192: each main effect's cells less one gauge
per row, plus the interaction's 2,048 cells less the 188 (pooled matrix)
or 200 (per-sex matrix) directions the fit projects out. With the
interaction present the per-sex matrix adds no free direction to the
kernel — it moves twelve directions out from under the ridge — so C2
counts the same as the shipped form and C3 the same as C1, and the
nesting check has to come first.

**Decisions on the record whose margin is under two standard errors**
(`under_two_standard_errors`; findings for Nathan, nothing to act on):
the interaction riding on same-sex searches on the finished fit (+2.90,
SE 1.75, **1.66 standard errors**, better in 188 of 387 metros — Nathan
has seen this and keeps it; the rule keeps it too); C3 against C1 (Phase
3c −0.0005, −0.03 SE, better in 191; A2 +0.0073, 0.51 SE, 197); C2
against the shipped form (Phase 3c −0.0033, −0.22 SE, 194; A2 +0.0070,
0.47 SE, 209). The last two are exactly the comparisons the rule now
reads as ties. Every other margin on the record is above 2.3 standard
errors (the smallest, the Phase 3b same-sex education term, 2.37).

**Under the rule, the finished fit ships C1** — the form m3.3.0 serves,
refitted to its optimum — as m3.4.0, build 1ebeaa2dcad6 (the built
build's readings in §3 and the gate check; the ship chain
`_ship_m3_4_0.sh`, `ship_m3_4_0_run.log`, `a2_ship_check.json`).

**Timing after A2** (`a2/refine_fits.json`, `a2_rescore.json`,
`a2_chain_resume_run.log`):

| | Phase 3c | A1 | A2 |
|---|---|---|---|
| The shipped form's fit | 153.5 s (with report tables); 290.9 s re-timed here | 13.8 s | **1.1 s** (1.7 s with its report tables) |
| Leave-one-metro-out, 387 metros, 8 workers | 6,772 s for three forms | 7,871 s for five | **2,020 s for six** (about 17 min for three); an interaction refit 3.0–3.3 s at 12 passes (max 15), none on the cap |
| Same-sex fit and LOMO | 1,880 s | 1,566 s | **308 s** |

**Where the time goes now** (the shipped form, 1.08 s of fitting): the
raw stage 0.28 s for 7 passes, the bandwidth CV 0.02 s, the smoothed stage
0.16 s for 4, the interaction stage 0.62 s for 18 (0.67 s for 19 on the
per-sex forms). Nothing dominates any more; the fit step's wall time is
now the per-metro dial fits (about 45 s per form for 387 metros), which
Part A did not touch.

### A3 — skipped

The profile after A2 leaves the cohort forms' raw stage at 0.28 s and
seven passes — a quarter of a 1.1-second fit — so a fixed-point
accelerator over the sweep has nothing left to buy; the interaction stage
it would also have sped up stops on tolerance at 18 passes. Not
implemented, per the brief.

## 2. Scoring by value (Part B)

**The rule came first.** B1 — the four candidates behind one registry
switch (`normalization.match_scoring`, N0 the default, with
`match_value_floor` 40, `match_value_cap` 250 and `match_fence_iqr` 1.5
as registry constants carried in the manifest), the gate's diagnostics
(the match-score spread over the middle 80% of ranked cities and the
steering τ, on the record and never in the verdict), the unit tests of
the transform and of N0's bit-identity, the assertion that the gate
scores through the engine's function, ADR 0013, the ADR 0009 §8 amendment
and the measurement script — was applied from the drafts exactly as
written and committed (4bab576) before `match_scoring_candidates` ran;
the one mechanical change is a test fixture (deviations). Under N0
goldens.json is byte-identical to the m3.4.0 goldens. ADR 0014's δ does
not apply here: Part B's selection keeps its own rule and its own tie
clause.

**B2 — the four candidates measured on m3.4.0** (`b2_candidates.json`,
`b2_gate_<rule>.json`, `b2_matchend_<rule>.json`; the build's manifest
switched in memory, nothing on disk changed; 397 s). The gate is ADR
0011's against the m3.2.0 reference over the 516 scored searches (every
search reads as touched, because m3.4.0's kernel differs from the
reference's, so the totals run over all of them either way); the
match-end set is every ADR 0011 test search re-sent with the slider at
its match end (518 searches, 516 scored); the outlier condition asks for
at least 40 points of match-score spread between the 10th and 90th
percentile of ranked cities on every search of both sets; the steering τ
is Kendall's τ between each search's ranking and its match-index order:

| Candidate | ADR 0011 gate (ratio) | Match-end wobble, total | Gate-set wobble, total | Outlier condition | Steering τ, median (own slider / match end) | Below N0 at the match end | Verdict |
|---|---|---|---|---|---|---|---|
| N0 — the percentile rank (control) | pass 0.970 | 1,100.0 (median 1.63, max 9.5) | 306.7 (median 0.457) | pass: worst 80.0 points (0 searches below 40) | 0.508 / 0.834 (min 0.27 / 0.74) | — | control |
| V1 — winsorized at the 1st/99th percentiles | pass 0.754 | 1,011.5 (median 1.36, max 9.6) | 238.4 (median 0.360) | **fails**: worst 30.2 points (30 searches below 40) | 0.413 / 0.753 (min 0.08 / 0.61) | lower | no |
| V2 — clipped to the Tukey fences (1.5 IQR) | pass 0.775 | 1,025.2 (median 1.40, max 10.1) | 245.1 (median 0.364) | pass: worst 41.8 points (0 below 40) | 0.407 / 0.756 (min 0.10 / 0.62) | lower | **qualifies — ships** |
| V3 — the index clipped to [40, 250] | pass 0.719 | 999.8 (median 1.30, max 10.1) | 227.4 (median 0.324) | **fails**: worst 23.5 points (57 searches below 40) | 0.433 / 0.756 (min −0.00 / 0.52) | lower | no |

**V2 ships, and why.** Every value candidate passes the gate by a wide
margin and wobbles less than N0 at the match end; the outlier condition
is what decides. V3 has the lowest match-end total (999.8) and V1 the
next (1,011.5), but both squeeze the field on the searches whose ranked
set holds a run of far-out cities: under V3 fifty-seven searches keep
fewer than 40 points of spread over their middle 80% (the worst, women of
50 of two or more races, 23.5 points; the five worst are all seekers of
two or more races), under V1 thirty (the worst, the American Indian or
Alaska Native woman of 25, 30.2; the five worst are all American Indian
or Alaska Native seekers). V2's fences move with each search's own
quartiles, so its worst search keeps 41.8 points (a man of 40 with high
school or less, of two or more races), its median search 52.7 against
N0's 80.0, and it is the one candidate that meets all three conditions.
The rule's tie clause was not needed. **On the gate's own set V2 reads
0.775 against the m3.2.0 reference — total wobble 316.2 → 245.1, the
median search 0.457 → 0.364 — far below the reference and below every
kernel build so far**; the reference is not moved (the brief), and
whether to re-base it is Nathan's call in an ADR if he makes it.

**How much matching still steers** (reported, not gated): at the
searches' own slider positions the median τ between the ranking and the
match-index order falls from 0.508 under N0 to 0.407 under V2 (p10 0.37
→ 0.23, p90 0.61 → 0.53); at the match end from 0.834 to 0.756 (p10 0.82
→ 0.73). The slider still means something: at its match end three
quarters of the pairwise order follows the index, and the drop is what
value scoring does — a near-tie in the index no longer flips a rank at
full weight.

**The disclosed reference searches under each candidate** (the face
check on the outlier handling; the top city and top five at the search's
own slider position, and the top city at the match end):

| Search | N0 | V1 | V2 (ships) | V3 |
|---|---|---|---|---|
| the graduate Asian woman of 30 | Los Angeles (Los Angeles, New York, San Francisco, Boston, Seattle); match end San Jose | San Francisco (San Francisco, Los Angeles, New York, Seattle, Boston); match end San Francisco | San Francisco (San Francisco, Los Angeles, New York, Seattle, Boston); match end San Francisco | San Francisco (San Francisco, Los Angeles, New York, Seattle, Boston); match end San Francisco |
| the graduate Asian man of 34 | Los Angeles (Los Angeles, New York, San Francisco, Boston, Chicago); match end San Jose | Los Angeles (Los Angeles, New York, San Francisco, Seattle, Boston); match end San Francisco | Los Angeles (Los Angeles, New York, San Francisco, Boston, Seattle); match end San Francisco | Los Angeles (Los Angeles, San Francisco, New York, Seattle, Boston); match end San Francisco |
| the Black woman of 30 | New York (New York, New Orleans, Miami, Philadelphia, Houston); match end New Orleans | the same; match end New Orleans | the same; match end New Orleans | New Orleans (New Orleans, New York, Atlanta, Philadelphia, Miami); match end New Orleans |
| the Pacific Islander man of 35 | Los Angeles (Los Angeles, San Francisco, Seattle, Las Vegas, Portland); match end Las Vegas | Los Angeles (Los Angeles, Seattle, San Francisco, Las Vegas, Sacramento); match end Honolulu | Los Angeles (Los Angeles, Seattle, San Francisco, Las Vegas, Portland); match end Seattle | Los Angeles (Los Angeles, Seattle, San Francisco, Las Vegas, Portland); match end Santa Rosa |
| the Pacific Islander woman of 35 | Los Angeles (Los Angeles, San Francisco, Seattle, Portland, Las Vegas); match end Davenport | Los Angeles (Los Angeles, San Francisco, Seattle, Portland, Sacramento); match end Davenport | Los Angeles (Los Angeles, San Francisco, Seattle, Portland, Sacramento); match end Davenport | San Francisco (San Francisco, Seattle, Los Angeles, Portland, Las Vegas); match end Davenport |

What the face check shows: the far-out city no longer wins by a mile.
For the graduate Asian seekers San Jose's index (630 and 582, displayed
250+) sits above V2's upper fence with San Francisco's, so the two share
the top of the match scale and San Francisco, stronger on the other
pillars, takes the top at the match end where N0 gave it to San Jose;
at the searches' own slider positions the top five are the same five
cities in a slightly different order. The Black woman of 30 reads the
same top five under V2 as under N0. The Pacific Islander searches keep
Los Angeles on top and Davenport — a tiny single population of the
sought group, the index in the thousands, capped in the display — on top
at the match end under every candidate; what changes is the second city
at the match end for the man of 35 (Las Vegas → Seattle). None of this
moved a served index; only the match feature's normalised value did.

**B3 — the ship.** `MODEL_VERSION` m3.5.0 (its note in `versions.py`),
`normalization.match_scoring: V2` in the registry, the manifest
regenerated — the data files are unchanged, so `cube.build` refreshed
1ebeaa2dcad6's manifest in place and **m3.5.0 is build 1ebeaa2dcad6**
(deviations) — then the fixture, the goldens (18 vectors, regenerated:
the served index is unchanged on every search, the scores move), the
permalink cases and the stat pages (`_ship_m3_5_0.sh`,
`ship_m3_5_0_run.log`). The build serves what B2 measured
(`b3_ship_check.json`): the ADR 0011 gate on the build reads exactly V2's
ratio and total (0.775033; 245.073 against 316.209), the index, its
margin, every display and every band are identical to m3.4.0's on the
default and same-sex reference searches, the index and replicate hashes
match search for search across all 516, and **ten of ten hard gates
pass** (`validation_report_m3_5_0.json`; the old overlap reading beside
the gate, 0.7375 on the two match-end personas, would fail the retired
0.80 bar and is reported as the soft reading it is). Tests: `pytest
atlas` 78 passed — the transform's unit tests, N0's bit-identity, the
rule switch with the display cap feeding none of the rules, the
attribution identity under every rule, the manifest block, the gate
scoring through the engine's function; Playwright 78 passed on the
fixture with axe clean on ten page shapes, the city page, compare and
the stats-that-moved-this-score reading the new normalised values
through the same API (`e2e_m3_5_0_run.log`). Latency p95 **35.32 ms**
(p50 26.8, p99 41.5, max 44.4) at a one-minute load of 2.46. Weight
sensitivity τ 0.91–0.98 for every ±20%. `.claude/launch.json` already
pointed at 1ebeaa2dcad6; ee4f08cf33e1 (m3.3.0) is retired to its
manifest, metros and kernel record (kernel.npz kept; deviations);
f20cb02c3af8 (m3.2.0) stays complete as the gate's reference. **The
reference is not moved**: the new build's total wobble on the gate's set
is 245.1 against the reference's 316.2, far below it and below every
kernel build so far (m3.3.0 0.971, m3.4.0 0.970); whether to re-base it
on m3.5.0 is Nathan's call, in an ADR if he makes it.

## 3. What changed for the visitor

**At A2 — the built m3.4.0 (1ebeaa2dcad6) against m3.3.0**
(`rank_shift_m3_3_0_to_m3_4_0.json`, `snapshot_m3_4_0.json`,
`a2_ship_check.json`). The build serves exactly what proof 3 measured in
memory: the same ranks, the same indices and the same scores on both
searches, row for row, and the same gate ratio (0.969937), so the shift
is proof 3's, now on a build:

| Search | Metros | Ranks changed | Kendall τ | Median move | p90 move | Largest move | Top 10 |
|---|---|---|---|---|---|---|---|
| The stated default (a woman of 30 seeking men 28–40) | 193 | 59 | 0.995 | 0 | 1 | 3 (Deltona 105 → 108, Springfield MO 119 → 122, Scranton 148 → 145, Laredo 170 → 167) | the same ten cities in the same order |
| The same-sex reference (a man of 31 seeking men 27–38, never married, with a degree) | 120 | 33 | 0.994 | 0 | 1 | 2 | San Jose still top by index (115.5) |

The default search's index moves a median 0.02 points (p90 0.11, largest
0.55; range 85.2–111.5 → 85.3–111.5, the median margin 4.12 unchanged).
The disclosed reference searches keep their top city (San Jose 631.6 →
629.6 for the graduate Asian woman of 30 and 583.8 → 582.2 for the
graduate Asian man of 34; Montgomery 317.3 → 317.1 for the Black woman of
30; Fayetteville 2,482 → 2,496 and 1,007 → 1,010 for the Pacific Islander
man and woman of 35, the woman's count of metros above 250 falling from 8
to 7; the graduate woman of 30 reads San Jose 190 as before).

**Every test search whose wobble rose more than 25% from m3.3.0**
(`a2_ship_check.json`, the two builds' validation reports per search;
findings, not gates) — five of 516, against 248 steadier, 247 shakier and
21 unchanged (total wobble 307.128 → 306.703, the median 0.4597 →
0.4572):

| Search | Wobble, m3.3.0 → m3.4.0 |
|---|---|
| man of 40, some college, American Indian or Alaska Native | 1.14 → 1.71 |
| same-sex: man of 30 seeking men, high school or less | 0.32 → 0.47 |
| man of 40, bachelor's | 0.29 → 0.37 |
| woman of 25, bachelor's, white | 0.29 → 0.36 |
| man of 30, bachelor's, Hispanic | 0.13 → 0.17 |

The two searches at the slider's match end stay the wobbliest on the
site, 2.878 → 2.899 places. (The C3 candidate, measured in memory and not
shipped, would have raised 22 searches by more than 25%, nine of them
same-sex grid searches, and read 2.98 at the match end.)

**At B3 — m3.5.0 against m3.4.0** (`rank_shift_m3_4_0_to_m3_5_0.json`,
`b3_ship_check.json`). The served index is unchanged on every search
(Kendall τ 1.000 on the index, largest change 0.00); the rankings move
because the match feature now enters the score by its value:

| Search | Metros | Ranks changed | Kendall τ | Median move | p90 move | Largest move | Top 10 |
|---|---|---|---|---|---|---|---|
| The stated default (a woman of 30 seeking men 28–40) | 193 | 158 | 0.938 | 3 | 12 | 19 (Corpus Christi 117 → 98, Las Vegas 58 → 40, Salem OR 157 → 140, McAllen 159 → 143; the other way Kalamazoo 100 → 115, Tulsa 132 → 117, Augusta 107 → 122, Olympia 142 → 157) | the same first seven; Atlanta and Seattle swap 8th and 9th; **Washington DC replaces San Jose at 10th** |
| The same-sex reference (a man of 31 seeking men 27–38, never married, with a degree) | 120 | 104 | 0.867 | 5 | 15 | 19 (Las Vegas 63 → 44, El Paso 69 → 51, Fresno 42 → 59, Milwaukee 47 → 31, Santa Maria 27 → 43, Orlando 62 → 46, Palm Bay 40 → 56, Reno 44 → 60) | San Francisco and Los Angeles still first and second; San Jose 5th → 3rd, New York 6th → 4th, Boston 3rd → 5th, Seattle 4th → 6th; Chicago enters at 9th, Denver leaves |

The disclosed reference searches keep their top city by index at the
same score and a higher rank (San Jose 9th → 6th for the graduate Asian
woman of 30, 12th → 8th for the graduate Asian man of 34, 8th → 6th for
the graduate woman of 30; Montgomery 80th → 75th for the Black woman of
30; Fayetteville 37th → 35th and 38th → 33rd for the Pacific Islander man
and woman of 35; San Jose 5th → 3rd on the same-sex reference): the top
city's normalised match value was already 100 under the percentile rank,
so its score stands while the cities around it spread out.

**Every test search whose wobble rose more than 25% from m3.4.0**
(`b3_ship_check.json`, the two builds' validation reports per search;
findings, not gates): **95 of 516**, against 342 steadier and 174
shakier (total wobble 306.703 → 245.073, the median search 0.457 →
0.364); 16 of the 95 rise from a base under 0.1 of a place, 17 are
same-sex grid searches and two are personas. The twelve largest rises:

| Search | Wobble, m3.4.0 → m3.5.0 |
|---|---|
| woman of 25, high school or less, Asian | 0.19 → 0.83 |
| same-sex: woman of 40, graduate | 0.31 → 0.72 |
| man of 30, graduate, Pacific Islander | 0.25 → 0.64 |
| woman of 25, some college, another race | 0.65 → 1.04 |
| woman of 50, graduate, Pacific Islander | 0.99 → 1.37 |
| woman of 40, some college | 0.44 → 0.80 |
| woman of 40, high school or less, Pacific Islander | 0.70 → 1.05 |
| man of 30, some college, Hispanic | 0.03 → 0.38 |
| same-sex: woman of 40 | 0.71 → 1.06 |
| man of 40, graduate | 0.17 → 0.47 |
| woman of 35, bachelor's, Pacific Islander | 0.73 → 1.04 |
| man of 50, bachelor's, American Indian or Alaska Native | 0.64 → 0.93 |

The other 83, named: women of 25 — some college, Pacific Islander (0.29 → 0.52); high school or less (0.31 → 0.49); Asian (0.05 → 0.20); bachelor's, another race (0.52 → 0.65); bachelor's, Asian (0.01 → 0.13); graduate, Black (0.15 → 0.27). women of 30 — undisclosed (0.48 → 0.73); graduate, Pacific Islander (0.37 → 0.60); Asian (0.13 → 0.34); bachelor's, Black (0.21 → 0.40); bachelor's (0.20 → 0.33); high school or less, Hispanic (0.14 → 0.23); Hispanic (0.18 → 0.24); Black (0.07 → 0.12); graduate, Asian (0.06 → 0.10). women of 35 — high school or less, Pacific Islander (0.64 → 0.88); graduate, Black (0.31 → 0.52); bachelor's, two or more races (0.23 → 0.42); graduate, Hispanic (0.21 → 0.28); Asian (0.28 → 0.36); Black (0.13 → 0.16). women of 40 — bachelor's, Black (0.45 → 0.63); graduate, Black (0.25 → 0.39). women of 50 — graduate, Hispanic (0.26 → 0.53); high school or less (0.11 → 0.35); Asian (0.18 → 0.41); graduate, Asian (0.20 → 0.39); high school or less, Asian (0.48 → 0.64); high school or less, Hispanic (0.09 → 0.15). men of 25 — Pacific Islander (0.15 → 0.43); graduate, Pacific Islander (0.07 → 0.34); high school or less, Asian (0.13 → 0.34); Hispanic (0.20 → 0.34); some college, Hispanic (0.22 → 0.31); bachelor's, Asian (0.07 → 0.15); graduate, Hispanic (0.12 → 0.20); graduate, Asian (0.05 → 0.13). men of 30 — graduate, another race (0.53 → 0.82); high school or less, Asian (0.21 → 0.38); graduate, Asian (0.19 → 0.34); bachelor's, American Indian or Alaska Native (0.44 → 0.57); bachelor's, Hispanic (0.17 → 0.30); some college, Pacific Islander (0.27 → 0.39); bachelor's, Pacific Islander (0.27 → 0.38); Hispanic (0.08 → 0.17); bachelor's (0.22 → 0.29). men of 35 — bachelor's, two or more races (0.12 → 0.32); high school or less, Asian (0.27 → 0.40); graduate, Pacific Islander (0.33 → 0.43); some college, Hispanic (0.22 → 0.32); bachelor's, Black (0.34 → 0.43); some college, Asian (0.20 → 0.29); undisclosed (0.15 → 0.23); Hispanic (0.11 → 0.16). men of 40 — two or more races (0.43 → 0.62); graduate, Hispanic (0.27 → 0.45); graduate, Pacific Islander (0.45 → 0.61); Hispanic (0.08 → 0.13). men of 50 — high school or less, Asian (0.22 → 0.51); bachelor's, Asian (0.12 → 0.36); high school or less, Pacific Islander (0.41 → 0.66); Asian (0.11 → 0.29); graduate, Asian (0.12 → 0.25); bachelor's, Black (0.19 → 0.33); bachelor's, two or more races (0.36 → 0.48); bachelor's (0.30 → 0.37). same-sex: women of 30 — graduate (0.08 → 0.16). same-sex: women of 35 — bachelor's (0.16 → 0.21). same-sex: women of 40 — high school or less (0.26 → 0.38). same-sex: men of 25 — undisclosed (0.00 → 0.17); graduate (0.15 → 0.21). same-sex: men of 30 — undisclosed (0.00 → 0.12); some college (0.16 → 0.23). same-sex: men of 35 — bachelor's (0.16 → 0.30); undisclosed (0.09 → 0.19). same-sex: men of 40 — some college (0.34 → 0.56); undisclosed (0.37 → 0.47); bachelor's (0.07 → 0.15). same-sex: men of 50 — graduate (0.59 → 0.85); undisclosed (0.33 → 0.56); high school or less (0.27 → 0.34). the persona with only high school disclosed (0.26 → 0.48); the same-sex pool persona (0.41 → 0.52).

The two searches at the slider's match end are still the wobbliest on
the site and the one place the reordering costs: 2.90 → 3.37 places.
Everywhere else the field steadied — 342 searches, the median from 0.457
to 0.364 of a place. The pattern behind the risers: seekers whose ranked
set holds a run of cities at or beyond the fences — the Asian, Pacific
Islander and Hispanic grid searches are 49 of the 95 — where cities
the percentile rank held apart by a fixed step now sit close together on
the value scale and swap under replicate noise. That is the trade the
rule accepted in advance: the outlier condition bounds how far the field
can be squeezed, and V2 is the candidate that stayed inside it.

## Gate check

- **R (ADR 0014)**: the tie rule was committed (2d2c063) before the ship
  (ba6f438); every held-out decision on the record re-run through the
  shared functions came out as expected — race × education ships (+14.07,
  gate pass), the same-sex education term ships (+12.26 / +15.16) and the
  interaction rides (+2.90), C2 does not qualify (+0.007 < δ), C1 and C3
  are tied and C1 ships as the nested form, every Phase 3b and 3c verdict
  and every other same-sex component decision unchanged — and the δ
  interval is reported: every outcome the same for δ in (0.0073, 2.898],
  every intermediate verdict for δ in (0.0073, 2.828] (§1). ✓
1. **A1**: the refactor reproduces m3.3.0 to 6.3e-10 (dials) and 4.4e-12
   (same-sex), bandwidths equal; the goldens are unchanged under the
   refitted kernel; the timing profile is reported. **The objective is
   not strictly no worse**: −2.8e-7 and −5.7e-8 per 1,000 couple-sides,
   the one crawling cell the old rule kept moving, 3,500 times below the
   precision any decision reads — reported, not recovered. ✓ with that
   finding
2. **A2**: all four proofs measured — off reproduces A1 to 8e-15; on, the
   objective rises 0.0097 per 1,000 sides and the held-out record does
   not fall; the served index, the rank shifts and the gate reported. The
   re-run C1/C2/C3 verdict flipped under the old rule (C3 over C1 by
   0.007) and the phase halted; under ADR 0014 every re-run verdict
   matches m3.3.0's (C1 ships), and **m3.4.0 (1ebeaa2dcad6) passes all
   ten hard gates**, the ADR 0011 gate at 0.970, the build serving the
   same ranks, indices, scores and gate ratio as the in-memory candidate
   (§3, `a2_ship_check.json`). ✓
3. **A3**: skipped, with the profile's reason. ✓
4. **B1 was committed (4bab576) before any candidate was measured**; the
   measurement started after that commit (`b2_candidates_run.log`). N0
   reproduces the Part A build bit-identically: goldens.json is
   byte-identical after the registry gained the block, and the test
   asserts the same rankings, scores and normalised values as a manifest
   with no block. ✓
5. **B2**: every candidate reports its gate verdict and ratio, its
   match-end and gate-set wobble, the outlier condition with its worst
   searches and the steering τ (§2); the winner, V2, is the one the rule
   picks — the only candidate meeting all three conditions; the tie
   clause was not needed. ✓
6. **All hard gates pass on the final build** (1ebeaa2dcad6 as m3.5.0):
   ten of ten, the ADR 0011 gate 0.775 against the m3.2.0 reference with
   the old overlap share reported beside it (0.7375, the two match-end
   personas, a soft reading), as in Phase 3c (§2). ✓
7. **Latency**: p95 35.32 ms on the 400-query battery at a one-minute
   load of 2.46 on m3.5.0, and 36.25 ms at 2.43 on m3.4.0, against the
   100 ms budget; both 23 ms under m3.3.0's readings on the same code
   path, which points at the machine rather than the engine for the rise
   Phase 3c recorded (the engine-level A/B stays open as a finding). ✓
8. **Strings and copy**: the registry owns every new parameter
   (`normalization.match_scoring`, `match_value_floor`, `match_value_cap`,
   `match_fence_iqr`) and no user-facing string was added or changed; axe
   reports zero serious or critical issues on the ten page shapes; the
   banned-vocabulary sweep returns zero across 2,065 explanations
   (`validation_report_m3_5_0.json`) and the e2e banned-string checks
   pass on every page; Nathan's approved copy is byte-identical — the
   diff touches no string. The methodology page's "Each city's stats are
   compared across the cities that can answer your search" stays true:
   every candidate is computed per request across the ranked set, as the
   percentile rank was. No sentence of his was made inaccurate by this
   phase; the standing race-boxes item Phase 3c listed was settled by
   Nathan's call after Phase 3c. ✓

## Deviations

- A1: `kernel_refine check` (the Phase 3b check that the Form machinery reproduces kernel.py on the baseline form) is pinned to the old stopping rule (`stop="cell"`), since it compares against kernel.py's own IPF; every other caller takes the new rule by default.
- A1: the fit store for Part A is a seeded copy of the Phase 3c records in two directories — `results/phase3d/speedup/a1/` (the new stopping rule, items 2–3) and `results/phase3d/speedup/a2/` (the projection) — so each stage's record survives the next; files byte-identical to their Phase 3c originals are not committed again.
- A1: `kernel_refine fit --only` accepts `shipped` (the m3.2.0 form refitted by name from the store's record), so the re-scored held-out comparison reads every form from the same code rather than a new C1 against the old shipped record.
- A1: the raw stage keeps the same couple-weighted tolerance as the other stages (1e-7) although the brief allows it to stop looser: on the shipped form it reaches 1e-7 at pass 7 and 1e-5 at pass 6 (`a1_trajectories.json`), so loosening would save one pass, and the bandwidth choice is shown not to depend on the tolerance either way.
- A1: the "before" timings were re-measured on this machine with the m3.3.0 code (`timing_old_code.json`: 290.9 s for the shipped form's fit, 229.8 s for the same-sex fit) beside the Phase 3c record (153.5 s and 113.3 s including the report tables), because the machine carried other work during this session (one-minute load 2.3–3.2 throughout); before/after pairs are read on the same box.
- A1: with the interaction's blind directions still in the fit, the interaction stage stops on its 200-pass cap under the new rule too (the table's move per pass is still 2e-6 and the objective still gains 7e-5 per 1,000 sides per pass at pass 200), so Stage 1's speed-up on that stage is the per-pass cost alone; the stage's pass count falls only with A2's projection.
- A1 (LOMO): with the 25-sweep cap gone and no projection yet, every leave-one-metro-out refit of an interaction form runs its interaction stage to the 200-pass cap in the slow mode, so the A1 re-score ran at 1,499 s per 40 metros with 8 workers (about 4 h for the 387, against Phase 3c's 6,772 s for three forms at the 25 cap; one-minute load 12–15 during the run, the machine carrying other work). It was left to finish because the brief asks for the re-score on the new records; the LOMO speed-up is Stage 2's, as the brief says.
- A1 (LOMO, actuals): the re-score of five forms took 7,871 s with 8 workers (every interaction refit at the 200-pass cap, 28.5 s each; the raw and smoothed stages stopped on tolerance at 4–6 and 2–4 passes in every metro) and the same-sex fit and LOMO 1,566 s; both against Phase 3c's 6,772 s (three forms) and 1,880 s. The decisions re-scored identically (`a1_rescore.json`).
- A2: the first LOMO run died with a broken worker — the crash report shows a segmentation fault inside LAPACK's SVD (`dgesdd`, Apple's Accelerate dispatching threads) in a forked child, where the projection's basis was being built lazily. The projections are now built in the parent before the pool forks (`run_lomo_forms`, `cmd_samesex`) and the chain was resumed from the LOMO step on the six stored refits (`_a2_chain_resume.sh`).
- A2 (re-run, Phase 3b's decision): the race × education verdict is re-run with the current gate (ADR 0011 against the m3.2.0 reference) on the candidate as Phase 3b wrote it (`kernel_refine candidate`: baseline + interaction, no same-sex terms), because the old overlap gate on the m3.1.0 build cannot be reproduced without that retired build; the held-out part is re-run as it was.
- A2 (the flip): the re-run C1/C2/C3 verdict comes out differently on the finished fit — C3 (+69.715 per 1,000 sides over the shipped form) now leads C1 (+69.707) by 0.007 where Phase 3c read C1 ahead by 0.001, and C2 now improves on the shipped form (+0.007, was −0.003) and qualifies. The rule as written picks C3. Per the brief this is a stop condition: m3.4.0 is NOT shipped (no version bump, no goldens, no launch-config change, no served number moves), the projected fits and every measurement are on the record for Nathan's decision, and Part B was not started. The rank shift and served-index move of A2 were measured in memory on the m3.3.0 build with the candidate kernels (`a2_rank_shift.py`) instead of on a built m3.4.0.
- A2: the A2 code (the projection, on by default) is committed as the stage's deliverable; it moves no served number until an artifact is rebuilt and shipped.
- A3: skipped. The profile after A2 puts the whole fit at about 1.1 s (raw 0.28 s / 7 passes, smoothing 0.02 s, smoothed 0.16 s / 4, interaction 0.62–0.67 s / 18–19 passes) and a LOMO refit at about 3 s; the raw stage of the cohort forms is a quarter of the fit and seven passes long, so an accelerator over the sweep has nothing left to buy.
- R (ADR 0014): the free-parameter count `select_form` uses after nesting reads the projection's rank, so with the interaction present the per-sex education matrix adds no free direction (C2 counts 2,192 like the shipped form, C3 5,520 like C1); nesting, checked first, is what separates those pairs, and the count would only ever decide between non-nested forms (C1 against C2). Recorded in ADR 0014 rather than hidden behind a cell count.
- R (ADR 0014): the δ interval is reported twice — every outcome (what ships or is served) is unchanged for δ in (0.0073, 2.898]; every intermediate verdict for δ in (0.0073, 2.828], the upper end being Phase 3b's reading of the sex-specific education matrix (+2.83 over the baseline), whose outcome (dropped for the combination's gate failure) is the same either way. The brief's "about 0.008 to 2.89" is the first interval, with the lower end computed as 0.0073 (the C3 − C1 margin on the finished fit, exclusive).
- R (finding): the same-sex margins moved far more than δ between the Phase 3c and A2 records (the interaction's from 8.92 to 2.90, the education term's from 6.98 to 12.26 with the interaction off) because the projection moves the pair-shaped parts of the opposite-sex interaction into opposite-sex main effects that a same-sex search does not use — a change in what the borrowed term contains, not in where the optimiser stopped. The anchors in ADR 0014 name the three opposite-sex shifts the brief lists and state this one beside them; the same-sex verdicts hold under δ on both fits.
- R: `a2_decisions.py` re-reads the same-sex decision from `lomo_samesex.json` through `kernel_refine.samesex_decision` (the stored `samesex_fit.json` heldout block was written under the old rule and is kept beside it as `old_rule`); the C1/C2/C3 choice goes through `select_form` and the old rule's reading stays in the record.
- B1 (mechanical, before anything was measured): the drafted N0 bit-identity test takes a `goldens` fixture that only `test_goldens.py` defined, so `test_engine.py` gained the same module-scoped fixture (goldens.json read once); no drafted rule, candidate, constant or test assertion was changed. The drafts were applied otherwise exactly as written from `results/phase3d/_b1_drafts/` in the README's order; no path or build id needed changing (the measurement takes the build directory as an argument).
- B1: ADR 0013 carries the date it was drafted (24 September, in the A2 session, before the halt) although it is committed on 25 September after the m3.4.0 ship; the draft is committed as written, and the commit order — B1 before `match_scoring_candidates` runs — is the proof the rule preceded the measurement.
- B1: `cube.build` on the unchanged data refreshed 1ebeaa2dcad6's manifest in place (the normalization block, N0 the default) rather than producing a new build, as the build code does for a display-metadata change; the fixture manifest was regenerated the same way and goldens.json is byte-identical (N0 reproduces the Part A build).
- B2: the ADR 0011 gate's basis on every candidate reads "touched searches" with all 516 touched — not the "nothing touched" case ADR 0013 anticipated — because the gate compares against the m3.2.0 reference, whose kernel differs from m3.4.0's, so every search's index differs from the reference's; the totals run over every search in both cases and the verdict is the same reading.
- B2: the match-end set holds every one of the 518 ADR 0011 test searches (516 scored), because no test search sends explicit `weights` (the personas that move weights use the importance controls, which the rule does not exclude); the definition is applied as written.
- B3: the data files are unchanged by a scoring change, and the build id is the data's hash, so `cube.build` refreshed 1ebeaa2dcad6's manifest in place (model_version m3.5.0, match_scoring V2) rather than writing a new directory: m3.5.0 IS build 1ebeaa2dcad6, and the m3.4.0 build survives as its records (`snapshot_m3_4_0.json`, `validation_report_m3_4_0.json`, `latency_m3_4_0.json`, `rank_shift_m3_3_0_to_m3_4_0.*`) rather than as a directory to retire; `.claude/launch.json` already pointed at it.
- B3 (retirement): ee4f08cf33e1 (m3.3.0), now the intermediate build, is retired to its manifest, metros and kernel record as the brief says, and its kernel.npz (9.8 MB) is kept beside them — Phase 3c's B1 deviation records the cost of dropping it (the m3.0.0 kernel had to be rebuilt from kernel.json for the past readings), and the standing engine-level A/B of the m3.3.0 and m3.4.0 kernels needs it loadable; the 330 MB of cubes, byte-identical to 1ebeaa2dcad6's, go. f20cb02c3af8 (m3.2.0) stays complete as the gate's reference.
