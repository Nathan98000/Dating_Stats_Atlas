"""Version pins for the scoring model and the cube schema contract.

MODEL_VERSION covers the scoring model, pillar set, weights, suppression
policy and interval mechanism; a change that moves any golden requires a
bump here and regenerated goldens with a commit note. SCHEMA_VERSION is the
cube axis contract validated at load.

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

MODEL_VERSION = "m2.4.0"
SCHEMA_VERSION = "cube-v1"
