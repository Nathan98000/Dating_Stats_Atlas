"""Version pins for the scoring model and the cube schema contract.

MODEL_VERSION covers the scoring model, pillar set, weights, suppression
policy and interval mechanism; a change that moves any golden requires a
bump here and regenerated goldens with a commit note. SCHEMA_VERSION is the
cube axis contract validated at load.

m1.2.0 — Phase 2b (ADRs 0002 + 0003):
  - Suppression gates on n alone: min(n_alloc, kish) < 100, empty pool, or
    empty rival set. The CV tiers are removed — measured over the 480-shape
    battery's served region, true CV maxes at 11.8% (p99 9.8%), so the
    20%/30% rules provably could not fire, while the served-CV composition
    silently moved the published threshold. shown_unranked stays in the
    contract as a permanently empty array.
  - Attribution is feature-level (the stat is the primitive); pillar
    contributions are sums of their features'. The reference is the median
    of each normalized feature across the query's ranked set, defined once.
  - The D10 comparator is retired; explanations lead with the stats that
    moved the score; every user-facing label comes from the registry.
  - Interim cross-group pairing rate (PUMS couple links) serves the §10.4
    counterweight with a direct replicate-measured margin.
The interval mechanism itself is unchanged from m1.1.0.

m1.1.0 — Phase 2a: five pillars (pool, balance, reach, cost, lifestyle);
served intervals via the Gate 0 one-sided calibrated bound (coverage 97.5%,
median overstatement 23.4% on holdout — copy says "at least this wide",
never "±"); §8.2 contract; purity < 0.5 flagged.
"""

MODEL_VERSION = "m1.2.0"
SCHEMA_VERSION = "cube-v1"
