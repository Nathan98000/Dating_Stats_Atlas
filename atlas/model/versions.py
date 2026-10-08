"""Version pins for the scoring model and the cube schema contract.

MODEL_VERSION covers the scoring model, pillar set, weights, suppression
policy and interval mechanism; a change that moves any golden requires a
bump here and regenerated goldens with a commit note. SCHEMA_VERSION is the
cube axis contract validated at load.

m4.2.1 — Phase 5 (the design audit of 8 October 2026, Nathan's decision
4): the movers line changes shape. It names at most two pluses, largest
first, and then the single biggest eligible minus (explain.pick_movers;
MAX_PLUSES, MAX_MINUSES), and reads "Biggest pluses: X, Y · Biggest minus:
Z" — "Biggest minus: Z" alone when nothing is a plus — instead of "... · Z
counts against it", which disagreed with plural phrases ("Walkable
neighbourhoods counts against it") and could hide a city's main downside
behind three pluses (San Francisco named no minus, though rent cost it 3.6
points). The m4.1.1 sides rule, TOP_STATS_MIN_POINTS and the merged price
levels are unchanged. The pick is also served as data, `movers` ([{key,
sign}]) beside top_stats and summary_line, for the result chips; the
registry gains each mover's chip_label and writes "walkable
neighborhoods". No score, rank, figure, band or suppression moves; only
which items a line names, its wording, top_stats and movers. The data
files are unchanged, so the build keeps its id (63c4e5fa51bf) with its
manifest refreshed. Goldens regenerated: the summary lines, beside the
version line. Phase 5's commit I adds one served field in the same
release: each variant's score_median {value, display}, the median overall
score of the ranked set (ADR 0018 amended); no golden moves for it.

m4.2.0 — Phase 4e (Nathan's rule, 2026-10-03): a new definition of a nice
day. A day counts when it meets all six of: an average temperature,
(TMAX + TMIN) / 2, between 55 and 75°F inclusive; a high below 85°F; a low
above 45°F; at most 0.1 in of rain; no measurable snowfall (SNOW = 0); and
snow on the ground under 1 in (SNWD). A day with no snow reading counts as
snow-free. Every threshold lives in the registry's pleasant_day block
(transform lifestyle_pleasant_days_v3); station eligibility and the
completeness policy are unchanged. pleasant_days is the weather pillar's
only feature, so the weather pillar, scores and ranks move; the build takes
a new id (features.parquet changes). Goldens regenerated; the measured
effect is in results/phase4e/ and atlas/PHASE4E.md.

m4.1.1 — the movers line (Nathan's report, 2026-10-03, after the launch):
two errors on the live site. (1) The two BEA price levels, goods and
services, share the mover phrase "everyday prices", so a row could read
"Biggest pluses: ..., everyday prices, everyday prices", or name everyday
prices as a plus and the minus at once. They are now one item, their
contributions added, before the top three are picked (explain.mover_units).
(2) Austin read "Walkable neighbourhoods counts against it" beside a card
saying "More walkable than most": the score measures a stat against the
middle of the cities ranked for the search, the card against every city,
and in narrower searches the ranked cities are mostly big, walkable metros.
The line now never names a stat as a minus where the city's card says
better than most, nor as a plus where it says worse than most
(explain.mover_sides, pick_movers). No score, rank, figure, band or
suppression moves; only which items a line names, and top_stats with it.
The data files are unchanged, so the build keeps its id (2dbd9ebfa7ff)
with its manifest refreshed (the version alone). Goldens regenerated: the
summary lines that moved, beside the version line.

m4.1.0 — Phase 4c (ADR 0004 amended, Nathan's decision): dating pool
balance is the single people of the sought sex per 100 single people of
the OTHER sex — the opposite of the sought sex — in the search's age range
and marital selection, before any other filter. On an opposite-sex search
the other sex is the visitor's own, so the figure is unchanged, block for
block; a same-sex search, which m4.0.0 served as not applicable (both
sides the visitor's own sex: the same people), shows the figure an
opposite-sex search for the same people shows. Balance is displayed and
not scored (since m3.0.0), so no score, rank, compatibility figure,
suppression or band moves — checked over every ADR 0011 test search and
every variant (PHASE4C.md). Balance no longer depends on the visitor, so
/v1/rank sends it once (variants.balance) instead of once per own sex
(variants.by_sex), and the response is smaller for it; balance_applies
and the policy string balance_same_sex are retired. The
data files are unchanged, so the build keeps its id (5b780e4f2444) with
its manifest refreshed (the version and two registry strings). Goldens
regenerated: only the same-sex vector's balance moves, beside the version
line.

m4.1.0, build 2dbd9ebfa7ff — Phase 4d (ADR 0019, Nathan's decision):
political lean, each metro's 2024 presidential vote, is shown as context
and never scored, filtered, weighted or asked. features.parquet gains
three vote columns (political_dem_votes, political_rep_votes,
political_votes), so the build takes a new id; its cubes, kernel, pairing
cells and metros are byte-identical to 5b780e4f2444's, and no scored
input, weight, suppression rule or interval changes. No golden moves —
the eighteen vectors are identical and only goldens.json's fixture_of line
names the new build — so MODEL_VERSION stays m4.1.0: a bump is for a moved
golden. Every /v1/rank response over the 518 ADR 0011 test searches is
byte for byte the same but for the build id (results/phase4d/
served_numbers_check.json); the figure is served apart, by GET
/v1/political_lean (model.context).

m4.0.0 — Phase 4, Stage 5 (ADR 0018, Nathan's decisions 1-5): the
figure is renamed COMPATIBILITY (internal names unchanged); race is off by
default — a visitor who has not switched it on gets the RACE-FREE form
(the cohort age term and the education matrix, refitted with no race
component and no interaction, its own per-metro dials), not C1 with a
population-average mixture over races; a visitor who switches race on
gets C1 exactly as m3.5.0 served it; a same-sex search uses the same-sex
age and education terms and nothing else (refitted with no race, no
interaction, no dial), even with race on — superseding the Phase 3c/3d
call that the interaction rides. The kernel artifact is kernel_v3 and
carries all three forms. The visitor's own sex, education and race never
reach the server: /v1/rank takes the own age and an explicit sought sex,
refuses the three with a 422, and returns every variant (model.variants,
50 per search), which the browser selects from without computing a
ranking number; every variant equals rank() for that seeker (asserted).
The request path shares the parts no variant changes (the seeker weights'
tensor, the balance sums, each metro's cards and crime block), contracts
the interaction tensor level by level and computes average ranks in
numpy — the same served numbers on the m3.6.0 build, checked over 181
searches — and the compatibility figure's technical stats entry carries
the figure at its match block's precision (two decimals). Goldens
regenerated; the rank shift from m3.6.0, the stability gate's reading
against m3.5.0 and the reference move are in PHASE4.md.

m3.6.0 — Phase 4, Stage 3b (ADR 0012, Nathan's decision): US weather
stations only. The GHCN-Daily adapter keeps US stations alone (a GHCN
id's country code, ghcn_daily.US_STATION_PREFIX); its network filter
had only ever looked at US ids, and the Phase 4 audit found one served
metro on a station across the border: Detroit (19820), matched to
Windsor, Ontario (CA006139520, 14.9 km). It is rematched by the same
rule to the nearest qualifying US station, Detroit Metro Airport
(USW00094847, 25.3 km), and its nice days a year move 115.6 -> 120.7.
No other metro's station or value changes (two record a lower candidate
rank, their nearer non-US candidates gone); static_features.csv differs
in that one cell. The weather feature is scored by percentile rank
across each search's ranked set, so the change can move other cities'
weather percentiles, scores and ranks slightly. The kernel, the scoring
rules, suppression, bands and every other feature are unchanged. The
data changes, so the build id changes. Goldens regenerated; the rank
shift from m3.5.0 is in PHASE4.md.

m3.5.0 — Phase 3d, Part B (ADR 0013): CHANCES OF MATCHING is scored by
its value, not its rank. The match feature's normalised value is
x = ln(index / 100) clipped to the Tukey fences of the ranked set (1.5
interquartile ranges beyond the quartiles, the registry's
match_fence_iqr) and min-max scaled to 0-100 across the ranked set for
this query (candidate V2), so near-ties get near-equal scores and a large
real lead counts as large while no single outlier city can squeeze the
field; a one-city set or identical values score 50, a missing value stays
missing. Chosen by the rule committed before it was measured (B1,
3e21195): of N0 (the percentile rank), V1 (winsorized at the 1st and 99th
percentiles), V2 (the fences) and V3 (the index clipped to [40, 250]), V2
is the one candidate that passes the ADR 0011 gate (0.775 against the
m3.2.0 reference), keeps at least 40 points of match-score spread over
the middle 80% of ranked cities on every test search (its worst 41.8;
V1 30.2 and V3 23.5 fail) and wobbles less than N0 over the match-end
set (1,025 against 1,100 places); V3 had the lowest match-end total
(1,000) and V1 the next (1,012), both disqualified by the outlier
condition. The served index, its display cap, suppression, bands and
standing, the kernel and every other feature's percentile rank are
unchanged; only the match feature's normalised value moves, so scores
and rankings move for every search. The data files are unchanged, so
the build keeps its id (1ebeaa2dcad6) with its manifest refreshed.
Goldens regenerated; the before/after is in PHASE3D.md.

m3.4.0 — Phase 3d (ADR 0010 amended; ADR 0014): the kernel fit reaches
the optimum it states. After every Newton step on the race x education
interaction the directions the penalised objective cannot see are taken
out (kernel_refine.Projection: the seeker-only part dropped, the
education-pair and race-pair parts moved into the main effects), so the
interaction stage stops on tolerance at 18 passes instead of the 200-pass
cap it hit in m3.2.0 and m3.3.0; the penalised objective rises 0.0097 per
1,000 weighted couple-sides, the fit takes about a second instead of
minutes, and the sweep keeps its table and stops on the couple-weighted
move (Phase 3d A1, which reproduces m3.3.0 to 1e-9 under the old rule).
The served form is unchanged in kind: C1 (seventeen seeker-age cohorts
per sex on the shipped form, the pooled education matrix, the
interaction) ships by ADR 0014, the held-out tie rule — on the finished
fit C3 leads C1 by 0.007 per 1,000 sides and C2 reads +0.007, both under
the 0.25 tie margin, so C2 does not qualify, C1 and C3 tie and the nested
form ships; race x education (+14.07 over the baseline, gate 1.002) and
the same-sex composition (education served, the interaction riding by
+2.90) hold. Against m3.3.0 the gauged education and race main effects
move by up to 0.036 and 0.095 in log units and the dials by up to 0.027;
the default search's index moves a median 0.02 points with the same top
ten in the same order (Kendall tau 0.995), gate 0.970 against the m3.2.0
reference. Scores move slightly for every search; goldens regenerated;
the before/after is in PHASE3D.md.

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

MODEL_VERSION = "m4.2.1"
SCHEMA_VERSION = "cube-v1"
