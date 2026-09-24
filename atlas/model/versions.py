"""Version pins for the scoring model and the cube schema contract.

MODEL_VERSION covers the scoring model, pillar set, weights, suppression
policy and interval mechanism; a change that moves any golden requires a
bump here and regenerated goldens with a commit note. SCHEMA_VERSION is the
cube axis contract validated at load.

m3.3.0 — Phase 3c (ADR 0011; ADR 0010 amended): the rank-stability gate
becomes total WOBBLE against the fixed m3.2.0 reference (the mean rank
move of the cities in either top 10 over the 80 replicates, summed over
the searches a change touches; fail above 1.10x), which lets the cohort
age term ship: a gap curve per seeker sex and age cohort (Phase 3b's
seventeen cohorts, B1) added to the shipped form (baseline + race x
education) — held-out gain +69.7 per 1,000 weighted couple-sides over
m3.2.0's form, better in 386 of 387 metros, gate 0.971. The sex-specific
education matrix is dropped as measured (-0.003 per 1,000 on the shipped
form; with the cohort term it ties the cohort term to 0.001 and adds
nothing). Same-sex searches take the EDUCATION term from same-sex
couples (face check for the same-sex matrix: own level above 1 and above
every level two or more away), with the opposite-sex race x education
interaction riding by held-out fit (+8.9 per 1,000 same-sex sides over
the composition without it); race stays borrowed; the artifact records
same_sex.interaction_applies. The same-sex sentence names what is served
and the loader asserts it against same_sex_components. Scores and
rankings move for every search (a new age term, a new same-sex
composition); goldens regenerated.

m3.2.0 — Phase 3b, Part B (ADR 0010): the kernel gains a race x
education two-way term per seeker sex, shrunk toward no interaction by
empirical Bayes (tau 0.18; a cell keeps n/(n+31) of its raw log ratio),
undialled — the one refinement of three that both improves held-out
likelihood (+14.1 per 1,000 weighted couple-sides, leave-one-metro-out
split-half) and passes the standing rank-stability gate (0.800). The
cohort age term (+70.4, the best fit) fails the gate and is dropped; the
sex-specific education matrix (+2.8) passes alone but fails in
combination with the interaction and is dropped. Artifact kernel_v2 (a
gap curve per sex x cohort, an education matrix per sex, the optional
interaction, optional same-sex terms; v1 still loads). Same-sex searches
take their AGE term from a kernel fitted on the 65,011 allocated
same-sex couple-sides (+205.7 per 1,000 sides held-out over the
opposite-sex fallback, 374 of 387 metros; served at dial 1), while
education and race keep the opposite-sex term with the metro's dial —
education because its same-sex matrix fails the standing face-validity
gate (not diagonal-dominant in the bachelor's row), race because the
small groups' own-group cells hold 5-44 effective sides. A same-sex
search's rows carry the registry sentence
saying whose patterns the figure is built from (match.note), and the
response says so (match_inputs.same_sex, same_sex_components). Goldens
regenerated; the before/after is in PHASE3B.md.

m3.1.0 — Phase 3b, Part A (ADR 0009 amended): the kernel's fitting
sample moves from recent unions alone to EVERY union weighted by
exponential decay with a five-year half-life (unmarried partners at
weight 1), chosen by the standing rank-stability gate, shortest half-life
first — five years is the first candidate on which all eighteen personas
reach the 0.80 bar (the m3.0.0 recent-only kernel failed three at 0.70–
0.71); the Pew number was not the criterion. The chances-of-matching
DISPLAY is capped at a registry ceiling (250, rendered "250+") through
one formatting helper; scoring is untouched and rankings are asserted
bit-identical with and without the cap. The Pew tie against the raw
per-metro dial is accepted on the record (ADR 0009 §4). Goldens
regenerated; the before/after is in PHASE3B.md.

m3.0.0 — Phase 3 (ADR 0009): the slider's second pole is CHANCES OF
MATCHING. A new match pillar (default 0.25, the weight balance carried)
scores match_propensity — the kernel-weighted share of the visitor's own
matched pool, served as an index where 100 is the national average for
that same search: sum_c w(seeker, c) n_c / sum_c n_c over the
search-masked cube cells, a RATE (so it trades against pool size rather
than duplicating it), divided by the same ratio over the cube summed
across every metro. The weights come from the assortative kernel fitted
on recent couples (pipeline/build/kernel.py) — age gap by seeker sex,
4x4 education, 8x8 race/ethnicity by seeker sex, odds multipliers
relative to random pairing given availability, one per-metro dial per
component where the leave-one-metro-out test earned one; race enters on
the same footing as age and education, Nathan's decision. Two OPTIONAL
seeker inputs (self.education, self.race_ethnicity) sharpen the kernel;
an unset one falls back to the population-average marginal for the
seeker's sex and age, so every combination answers. The margin of the
index comes from sumw2 with the weights squared (delta method on the
ratio); suppression still gates on the UNWEIGHTED n. Balance is
DEMOTED to a displayed statistic (pool_balance: context_only, weight 0)
— computed exactly as before, shown everywhere it was, scored nowhere.
The slider control is pool_vs_match; pool_vs_balance is accepted as a
deprecated alias for exactly this version (the size_vs_odds precedent).
Goldens regenerated; the before/after across the 193 is in PHASE3.md.

m2.0.0 — Phase 2c (ADR 0004): balance is redefined as the plain sex ratio
of single adults in the searched age range — count(sought sex) /
count(seeker sex), same ages, same marital selection, deliberately NOT
filtered by race, education or income — served as "per 100" and scored by
the balance pillar directly. The pool÷rivals ratio and the whole
symmetric-rivals apparatus leave the serving path (ratio, ratio_moe,
rivals and the rival mask are gone from the engine and the response); the
Phase 1 rival code and findings stay in the pipeline as history. Also:
race filters select who matches and nothing more (the interim cross-group
pairing rate is retired from serving; "Two or more races" and "Another
race" are always counted); marital narrows to never/previously at the API;
importance controls map to weights through registry constants; margins
keep being computed and returned but no longer render. Second breaking
contract change after ADR 0003.

m2.4.0 — Phase 2g (ADR 0008): rent moves from the ACS one-bedroom
median (B25031) to HUD's FY2027 50th Percentile Rent Estimates — a
gross rent on HUD's adjusted-standard-quality ACS 2020-2024 base,
carried into the fiscal year by recent-mover, inflation and trend
factors, so the card speaks in current dollars instead of a five-year
average. The metro figure is a renter-household-weighted mean of the
county file's medians (B25003_003E weights; New England town rows
collapse the same way one level down), exact against HUD's published
area figure wherever a metro is a single FMR area. The feature id is
renamed rent_1br while no public URL exists. Rent carries 0.5 of the
cost pillar, so scores and ranks move (goldens regenerated; the
before/after is in PHASE2G.md); pool counts, balance and every other
pillar's inputs are byte-identical to m2.3.1's build, asserted.

m2.3.1 — Phase 2f (ADR 0007): DISPLAY ONLY. The tone vocabulary widens
from three to five (good_strong/good/neutral/poor/poor_strong): the two
extreme bands of a directed feature now read harder than the two middle
bands, derived in the registry loader exactly as before — position
crossed with band_direction, never judgment per label. Registry copy
moves with Nathan's line-by-line review (home headline, slider note,
crime caution boxes, card blank states, definitions, the What-we-measure
composition and per-source stat-page attribution lines). NO NUMBER
MOVES: every score, rank, pool, balance and card value is identical to
m2.3.0 (asserted by pipeline/build/display_only_diff.py against the
m2.3.0 fixture across all fifteen golden vectors); goldens regenerated
under the bump differ only in the version line.

m2.3.0 — Phase 2e (ADR 0006): rent becomes the ONE-BEDROOM median gross
rent (B25031, variable selected from group metadata by label) — the
all-units median moved with each metro's unit mix, reading family-stock
metros as expensive for reasons a single person's rent never sees. The
cost pillar's internal weights are unchanged; only the rent input moves,
and with it the cost pillar and every score (goldens regenerated; the
before/after is in PHASE2E.md — Austin stays high at the 87th percentile
because its one-bedroom rents really are high; Provo drops ten points
because its family stock was the inflation). Fallback for a metro
without a one-bedroom median: the all-units median, flagged in the build
report (none needed in 2020-2024). Crime rates gain five-band standings
with deliberately NEUTRAL tones (colouring them would make the exact
comparison the FBI caution disclaims).

m2.2.0 — Phase 2e (ADR 0006, reversing ADR 0004's always-counted rule):
race and ethnicity become eight equal checkboxes. A selection filters the
pool to exactly the ticked groups — "Two or more races" and "Another
race" are no longer ORed into every selection — and zero ticked or all
eight ticked means no filter. DEFAULT-SETTING OUTPUTS REPRODUCE m2.1.0
EXACTLY (asserted against the pinned snapshot): the unfiltered universe
is unchanged, balance_masks is untouched and race-blind as m2.0.0 made
it, and only race-filtered requests move — they no longer include the
two groups the visitor did not tick. Goldens with race filters
regenerated under the bump.

m2.1.0 — Phase 2d (ADR 0005): six pillars — lifestyle splits into weather
(0.06) and students (0.04), dividing its 0.10 in the proportion its two
features already carried, so default-setting scores reproduce m2.0.0
exactly (asserted against a pinned snapshot); four importance controls
(cost, reach, students, weather; "lifestyle" accepted as a deprecated
alias applying to both halves for exactly this version; size_vs_odds is
gone, its one deprecation version served). pleasant_days is recomputed
from GHCN-Daily observations with a precipitation threshold — the Normals
substitution averaged away the variation the statistic counts and served
San Francisco 365 — which moves the weather pillar and therefore scores.
Standing bands go from tertiles to national quintiles with tones derived
from a registry direction. Crime context arrives (FBI CDE, coverage-
gated, never scored, D01) and static stat pages ship from the build.

m1.2.0 — Phase 2b (ADRs 0002+0003): n-only suppression; feature-level
attribution; comparator retired; interim pairing counterweight.
m1.1.0 — Phase 2a: five pillars; Gate 0 served intervals ("at least this
wide"); §8.2 contract.
"""

MODEL_VERSION = "m3.3.0"
SCHEMA_VERSION = "cube-v1"
