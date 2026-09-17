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

MODEL_VERSION = "m2.1.0"
SCHEMA_VERSION = "cube-v1"
