# Phase 3d — the kernel fit gets fast and finishes; the finished fit flips a photo-finish verdict, so nothing ships and the scoring change waits

Every number here is read from a file under `results/phase3d/` (or a
committed record it names); nothing was recomputed for the report.

**In plain words, for Nathan.** The model that turns the Census's couples
into the chances-of-matching figure now fits in about one second instead
of several minutes, and gives the same answers as before to more decimal
places than anyone reads (Part A, stage 1). Stage 2 then let the fit run
to its proper finish: the old fit always stopped at a fixed pass count
while still creeping, because part of the model was moving in directions
the data cannot see; those directions are now taken out and the fit
converges in eighteen passes. Letting it finish changes the served
figures only a little (on the default search the index moves a median
0.02 points and the top ten cities are the same ten in the same order),
and the stability test passes with room to spare. But the brief asked
one more thing before shipping: re-run the decisions that shaped the
current site on the finished fit and stop if any of them comes out
differently. One did. In Phase 3c two versions of the cohort age term
tied to the third decimal and the rule picked the simpler one (C1); on
the finished fit the other (C3, which also lets men's and women's
education patterns differ) is ahead by 0.007 of a point per 1,000
couples, so the rule as written now picks C3, and the sex-specific
matrix on its own moves from a hair below to a hair above the current
form. These are tiny margins on a large gain, but the brief made a
flipped verdict a stop condition, so I have not shipped a new build, not
changed a served number, and not started Part B (scoring by value); its
rule, code, tests and decision record are drafted and ready to commit the
moment you decide. Your decision is which form the finished fit should
ship — C3 by the rule, C1 by judging the difference too small to matter,
or something else — recorded in an ADR; then Part A ships as m3.4.0 and
Part B runs on it.

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

### A2 — the interaction projection (measured; not shipped)

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

**Not started**, by the stop condition above. So that it can start the
moment Nathan decides, the following are drafted and unapplied (kept
untracked under `results/phase3d/_b1_drafts/` with a README, outside the
commits, so that no candidate could be measured before the rule is
committed): the four candidates behind one
registry switch (`normalization.match_scoring`, N0 the default, with
`match_value_floor` 40, `match_value_cap` 250 and `match_fence_iqr` 1.5
as registry constants carried in the manifest), the gate's diagnostics
(the match-score spread over the middle 80% and the steering τ, on the
record and never in the verdict), the unit tests of the transform and of
N0's bit-identity, the assertion that the gate scores through the
engine's function, ADR 0013 and the ADR 0009 §8 amendment, and the
measurement script (`match_scoring_candidates.py`: the gate, the
match-end set, the outlier condition, the steering τ and the disclosed
searches for each candidate, then the selection rule). None of it was
run. The candidates' table, the winner and the disclosed searches'
tops are therefore empty here.

## 3. What changed for the visitor

Nothing yet: no build ships from this phase. Measured in memory on the
m3.3.0 build with the candidate kernels, so that the decision is taken
with the numbers in view:

**At A2, the C1 candidate** (section 1, proof 3): the default search's
top ten unchanged in order, 59 of 193 ranks changed by a median of 0, a
p90 of 1 and at most 3 places; the same-sex reference 33 of 120 changed,
at most 2. **Every test search whose wobble rose more than 25% from
m3.3.0** (`a2_wobble_vs_m3_3_0.json`; findings, not gates) — five of
516, against 248 steadier and 247 shakier:

| Search | Wobble, m3.3.0 → C1 candidate |
|---|---|
| man of 40, some college, American Indian or Alaska Native | 1.14 → 1.71 |
| same-sex: man of 30 seeking men, high school or less | 0.32 → 0.47 |
| man of 40, bachelor's | 0.29 → 0.37 |
| woman of 25, bachelor's, white | 0.29 → 0.36 |
| man of 30, bachelor's, Hispanic | 0.13 → 0.17 |

The two searches at the slider's match end stay the wobbliest on the
site, 2.88 → 2.90 places. Under the C3 candidate 22 searches rise by more
than 25%, nine of them same-sex grid searches (the man of 30 seeking men
with high school or less 0.32 → 0.67 the largest), and the match-end
searches read 2.98.

**At B3:** nothing; Part B did not run.

## Gate check

1. **A1**: the refactor reproduces m3.3.0 to 6.3e-10 (dials) and 4.4e-12
   (same-sex), bandwidths equal; the goldens are unchanged under the
   refitted kernel; the timing profile is reported. **The objective is
   not strictly no worse**: −2.8e-7 and −5.7e-8 per 1,000 couple-sides,
   the one crawling cell the old rule kept moving, 3,500 times below the
   precision any decision reads — reported, not recovered. ✓ with that
   finding
2. **A2**: all four proofs measured — off reproduces A1 to 8e-15; on,
   the objective rises 0.0097 per 1,000 sides and the held-out record
   does not fall; the served index, the rank shifts and the gate (0.970,
   pass) reported; **the re-run C1/C2/C3 verdict flips** (C3 over C1 by
   0.007; C2 now qualifies). Stop condition: m3.4.0 not shipped, no hard
   gate run on a build. ✗ — halted as the brief requires
3. **A3**: skipped, with the profile's reason. ✓
4. **B1**: not committed (Part B not started). —
5. **B2**: not run. —
6. **All hard gates on the final build**: no build. The shipped build
   stays ee4f08cf33e1 (m3.3.0), ten of ten from Phase 3c. —
7. **Latency**: not re-measured (no new build); ee4f08cf33e1's readings
   stand at 58.27 / 59.19 ms against the 100 ms budget. —
8. **Strings and copy**: no registry string or parameter was added
   (B1's block is drafted, unapplied); axe and the banned-vocabulary
   sweep were not re-run (no build); Nathan's approved copy is
   byte-identical — the diff touches no string — and no sentence of his
   is made inaccurate by a phase that changed no served number. The
   methodology page's "Each city's stats are compared across the cities
   that can answer your search" stays true. ✓

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
