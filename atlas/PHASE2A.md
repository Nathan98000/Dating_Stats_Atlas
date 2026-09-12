# Phase 2a — intervals, context pillars, model v1.1

Build `674aa70fc57c` · model `m1.1.0` · schema `cube-v1` (unchanged).
Reproduce: `bridge.tract_puma_cbsa` → `build.battery` → `build.intervals` →
`build.features` → `build.cube` → `tests/golden/make_fixture.py <build>` →
`pytest atlas` → `build.validate <build>`.

**Gate 0 closed; the public beta is unblocked on intervals.** The served
interval is a **one-sided calibrated bound** (Option 2): served RSE =
exp(X·β + metro offset) × per-race-stratum inflation, X = [log allocated n,
log Kish/allocated ratio, log domain share, marital screen, race dummies].
Measured on the double holdout (30% of shapes AND 20% of metros held out,
served region only, gates read once): **true MOE ≤ served MOE on 97.5% of
points (gate ≥ 95%); median overstatement 23.4% (gate ≤ 25%)**. Product
copy says **"at least this wide," never "±"** — the manifest, the
methodology page and the fixed policy strings all carry those words and
those numbers. Option 1 (a two-sided model) was worked first and **failed
honestly at p90 relative error 23.6%** vs its 15% gate (ladder selected by
train-internal CV only; M0 power law 30.9% → extended+offsets 20.9% in CV).
Diagnosis before fitting, as required: within the unfiltered stratum the
error is carried by weight structure (log Kish/alloc r=−0.29), calibration
proximity (log share −0.14) and marital composition (+0.12) — age span,
income-floor position, purity and metro size are all ≈0; across strata,
identity-filtered domains sit on different variance curves because ACS
weights are calibrated to county race/Hispanic-origin controls. Battery:
**480 stratified shapes** (3× Phase 1's 160, which was thin — 160
unfiltered plus 40 per race level, cycled over span/education/income/
marital strata), ~186k metro-points. A separately noteworthy measurement:
validated on the served region (n_gate ≥ 100, where intervals can actually
display), Phase 1's old power law scores 28.9%, not 44% — the old headline
was dominated by sub-gate domains that suppression removes.

## The correctness finding of the phase: Phase 1's mask axis bug

Phase 1's `score.py` flattened preference masks with einsum output
`"samier"` — income and education **transposed** relative to the cube's
memory layout. Axes with no filter are all-ones and align by accident, so
every Phase 1 calibration (SQL-based), every unfiltered check and the tier
study were unaffected — but **every cube-served query with a partial
education or income filter selected a scrambled cell set** (Kansas City,
men 40–55 graduate: cube said 12,412; the truth is 5,226). Phase 1's
committed persona CSVs are fine (SQL path); the `b4d99c1c1dea` cube's API
responses and goldens for education/income-filtered queries were wrong and
are superseded. Caught in Phase 2a because the validation suite's
rank-stability harness computes replicate rankings from SQL truth and one
persona "destabilized" at 0.388 — with one metro leaving the top-10 in
80/80 replicates, which noise cannot do. Fixed (`"sameir"`);
`test_mask_axis_semantics` now pins the flattened mask to the cube layout
cell by cell; the engine's pool values now equal the SQL values exactly
(and match Phase 1's SQL-based persona numbers, e.g. NY persona-A pool
190,165).

## Acceptance items

**1. Repo restructure.** §13.1 layout in place (`pipeline/{adapters,
bridge, build, contracts, registry}`, `model/` standalone with
`tests/golden/`, `api/` thin transport, `docs/`); the move was pure motion
with all 14 Phase 1 goldens green before and after, committed before any
behavior change. One documented deviation: `model/loader.py` does file→
array I/O inside model/ because the API, goldens and validation suite must
share exactly one loading path; scoring/suppression/explain import nothing
from it but the Build dataclass.

**2. Adapter contract, provenance, license.** Typed `Adapter` protocol +
`LicenseTerms(shippable)` + full `Provenance` records
(`pipeline/contracts/provenance.py`); ten sources wrapped (Census ACS/
PUMS/DHC/delineation/rel-file, CBP, QCEW, BEA, EPA SLD, NOAA, IPEDS). The
Phase 1 manifest's wrong strings (DHC "P1/P5", "from DHC P5") are fixed at
the source: the DHC adapter's `requested_variables` is the single origin
for both the query and the manifest record, and the cube build asserts
manifest-vs-adapter equality plus no-non-shippable-source over every
scored feature's provenance. `variance.npy` is retired from the artifact
(the failed Phase 1 diagnostic); intervals live in the manifest + a
features.parquet offset column.

**3. Feature registry.** `registry/features.yaml` + typed loader: the only
home of signs, weights, the NAICS venue list, the pleasant-day definition,
winsor bounds and the missing-data policy. Crime: `default_weight: 0`,
`context_only` (D01), asserted at load. POI union: `status: deferred` with
a tracked TODO, weight 0, excluded from scoring — not a stub. Loader
asserts pillar weights sum to 1, per-pillar feature weights sum to 1,
complete provenance on every entry, and scoring references ⊆ registry.

**4. Context pillars — the four traps, measured.**
- *CBP/QCEW suppression:* QCEW N-flag counts per NAICS (111–341 cells);
  CBP absences per NAICS (0–156). QCEW proves some small-NAICS CBP
  absences are nonzero, so "absent = zero" is applied only to the venue
  **sum** the feature uses; cross-check gate on that sum (log-corr
  **0.997**, median ratio 1.0), per-code correlations 0.86–1.00 reported
  as measured.
- *SLD 2010 geography:* population-weighted BG10 → tract20 → metro
  crosswalk via the tab20 tract relationship (uniform-density split only
  at actually-split tracts, documented); reconciliation asserted: corr
  0.999, max |log ratio| 0.20 (2018-vintage SLD population vs 2020–2024
  metro totals — structural, noted). SLD row accounting exact: 217,182 =
  220,134 national − 2,952 in AS/GU/MP/PR/VI, verified against the
  server's own counts after a silent-truncation hole (transient empty
  pages) was found and fixed.
- *"% of the pool in walkable tracts" is not computable:* shipped as
  `resident_walkability_index` (SLD-population-weighted walkability of the
  metro's residents); the §5.3 mock's wording is flagged for correction in
  the features report and the methodology page.
- *Missing features:* NaN + per-metro flags; pillar weights renormalize
  per metro, whole-missing pillars redistribute pro-rata; covered by
  `test_missing_feature_policy_renormalizes`. Reality: only
  `pleasant_days` is missing anywhere (4 station-less metros); every other
  feature covers 387/387.
- Cost composition decision: rent (B25064) + RPP Goods + RPP
  Services:Other; **all-items RPP excluded** because rent is measured
  directly and all-items embeds housing rents — using both would
  double-count housing. NOAA deviation recorded: 1991–2020 Normals daily
  product instead of §6's GHCN-Daily; station→metro via TIGERweb county
  internal points (the Gazetteer's yearly files are no longer on www2);
  383/387 metros, median station 7.7 km. The pleasant-day definition
  (TMAX 55–85°F, TMIN ≥ 40°F) is registry-owned; its consequences are
  visible and reported (coastal California ≈ 365; high-desert Bend ≈ 20).

**5. Model v1.1.** Five pillars, §7.2 normalization computed across the
query's own ranked set (never the build's); score 0–100; exact per-pillar
contributions vs the ranked median; first-order `score_moe` from the
served bounds (documented approximation, inherits their conservatism).
D05 slider: pure function; s=0.4545 reproduces the §8.2 default weights.
D10 comparator: one function in `model/explain.py`, `MIN_RANK_GAP = 5`,
population distance |ln(pop_a/pop_b)|, never compares to #1. **Purity
decision (Phase 1 open item), measured and closed:** on the battery,
interval coverage does **not** degrade at low purity (100% in the worst
bin) and Phase 1 calibration agreement falls only ~5 pp from the ≥0.9 bin
(98.5%) to the <0.5 bins (93.3–93.6%) — no cliff, so **flag, not gate**:
`allocation_purity < 0.5` adds a visible `low_allocation_purity` flag
(named constant, keyed to this study); 5 ranked metros carry it today.

**6. API contract.** §8.2 aligned: `self`/`seeking`, marital as a list,
spec race names (`black_nh`), multi-select race, `name`, `rank`, `score`/
`score_moe`, `pool`/`pool_moe`/`cv`, `n_unweighted` (defined as
min(allocated, Kish) — correction-2 semantics, documented), `tier`,
`ratio`, `allocation_purity`, `comparator`, `contributions`, `permalink`
with both version pins, `reason` strings `n_below_100`/`cv_above_20`/
`cv_above_30`, 409 on version-pin mismatch, `shown_unranked` present (and
can now fire, since D08's CV tiers run on the served CV). Documented
deviations, all additive: `rivals`, `ratio_moe`, `n_alloc`/`n_kish`
detail, `flags`, `explanation`, `few_metros_notice`, `size_vs_odds`;
`cross_group_pairing_rate` is `null` until the Phase 3 kernel. Loopback
bind, no CORS, no public API (D04).

**7. Explanation layer.** Deterministic jinja templates over the exact
attribution: top-two positive and negative contributions, phrasing by
magnitude bucket (≥8 / ≥3 / else score points), real numbers, real
comparator ("3.0× the compatible pool of Phoenix"). Suppression and
confidence strings are fixed in `suppression.POLICY_STRINGS`, keyed to the
policy table and versioned with the model — including the interval wording
in the exact required words. The §9 structured metric record is produced
per ranked row (`explain.metric_record`) and is the contract the Phase 2b
build-time narratives consume; face-validity rows in the validation report
show 33 of them.

**8. Validation suite** (`build/validate.py`, machine-readable report,
hard gates exit nonzero):
- interval calibration — **PASS** (coverage 0.975, median overstatement
  0.234, mechanism + copy rule in the manifest).
- suppression goldens — **PASS** (12 pinned §8.2 vectors, exact rankings,
  scores, pools, served MOEs, suppression sets; regenerated only with the
  m1.1.0 bump, noted in the commit).
- rank stability — **PASS**: ≥8-of-10 top-10 overlap in 0.875–1.0 of
  replicates across all ten evaluable personas (two are suppressed nearly
  everywhere by design). Before the einsum fix this gate correctly failed
  at 0.388 — it is the check that caught the bug.
- adversarial artifacts — **PASS**: zero college/military/prison
  watchlist metros in any persona top-10; rule = fail if >15% of a
  persona's pool in a watchlist metro is noninstitutional GQ.
- face validity — 33 top-3 rows with attribution-consistent explanations
  written for hand review.
- weight sensitivity — τ 0.944–0.982 (target ≥0.85): no pillar is
  secretly the whole model.
- external correlation — **as measured, weak-positive**: score/ratio vs
  B09021 living-alone share r≈+0.22/+0.25; vs median age at first
  marriage r≈+0.20/+0.26 — with a source finding: **B12007 is not
  published at CBSA level in 2024 acs/acs5** (every metro returns
  annotation jams; verified 2026-09-12), so state medians through each
  metro's primary state were used, flagged. Framing shipped in the report
  verbatim: the index measures opportunity, not outcome.

**9. Runtime, disk, latency, artifact.**

| Stage (new in 2a) | Time | Notes |
|---|---|---|
| 480-shape battery (81 replicates × 387 metros) | 35 min | reusable points parquet, 21 MB |
| Gate 0 diagnosis + fits + calibration | ~3 min | offline from points |
| EPA SLD REST pull | ~95 min wall | EPA throttles ~40× at deep offsets and under concurrency; state-partitioned, per-state counts verified server-side |
| NOAA stations (387 metros) | ~7 min | ~250 daily-normals CSVs cached |
| CBP + QCEW + BEA + IPEDS + rent | ~4 min | |
| BG10→tract20 crosswalk + features build | ~3 min | |
| Bridge re-run (corrected provenance) | ~5 min | reproduces Phase 1 exactly |
| Cube build + fixture + goldens | ~3 min | |
| Validation suite | ~4 min | |

Disk: 5.5 GB under `data/` (two builds retained); artifact **331 MB**
(unchanged — intervals ride in the manifest and features.parquet). API
resident set **469 MB**. Latency with intervals, static pillars and
explanations in the response path: **p50 12.2 ms · p95 19.9 ms · p99
20.8 ms** over 400 randomized §8.2 requests (target p95 < 60 ms).

## Deviations ledger (with reasons)

1. `model/loader.py` performs I/O inside model/ — one shared loading path
   beats purity (item 1).
2. NOAA Normals instead of GHCN-Daily; TIGERweb instead of the retired
   Gazetteer files (item 4).
3. Cost pillar composition: all-items RPP excluded (double-counts housing).
4. Walkability named `resident_walkability_index`; §5.3 mock wording
   flagged for the frontend.
5. API additive fields beyond §8.2 (item 6); `cross_group_pairing_rate`
   null until Phase 3.
6. CBP/QCEW gate moved to the venue sum actually consumed; per-code
   correlations reported, not gated.
7. B12007 metro-level unavailability; state fallback, recorded.
8. `variance.npy` retired; Phase 1's diagnostic numbers remain in
   results/phase1/.
9. D08's CV tiers are computed on the served (upper-bound) CV — every rule
   errs toward not ranking.

## Open items for Phase 2b / Phase 3

- Frontend (2b): URL state, hero slider, §5.3 rows with "at least this
  wide" margins, methodology page rendering docs/methodology.md, the
  suppression footer, metro pages; build-time narratives consuming the §9
  metric records (contract pinned, land at builds/<dv>/ in 2b).
- POI union (Overture + Foursquare) + §11 coverage-bias regression
  (registry entry `poi_venue_density`, deferred).
- Pairing kernel (3): replaces crude symmetric rivals; fills
  `cross_group_pairing_rate`; Pew intermarriage reproduction as its gate.
- Interval model upgrade candidate for a future two-sided attempt:
  race-domain interactions were the diagnosed residual; a per-stratum
  central model might pass 15% — the one-sided bound stands until
  something beats it under the same holdout discipline.
- Counsel packet (user-side, in progress at docs/decisions/counsel_packet)
  before any Zillow/Opportunity-Insights source enters.
