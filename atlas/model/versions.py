"""Version pins for the scoring model and the cube schema contract.

MODEL_VERSION covers the scoring model, pillar set, weights, suppression
policy and interval mechanism; a change that moves any golden requires a
bump here and regenerated goldens with a commit note. SCHEMA_VERSION is the
cube axis contract validated at load.

m1.1.0 — Phase 2a: five pillars (pool, balance, reach, cost, lifestyle);
served intervals via the Gate 0 one-sided calibrated bound (coverage 97.5%,
median overstatement 23.4% on holdout — copy says "at least this wide",
never "±"); full D08 tier policy computed on the served CV; §8.2 contract;
purity < 0.5 flagged (measured: no coverage degradation, ~5pp calibration
penalty — flag, not gate).
"""

MODEL_VERSION = "m1.1.0"
SCHEMA_VERSION = "cube-v1"
