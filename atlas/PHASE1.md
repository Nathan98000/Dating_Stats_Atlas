# Phase 1 — scaled build, corrections, serving artifact

Build `b4d99c1c1dea` · model `m1.0.0` · schema `cube-v1` · ACS 2020–2024 5-year
(PUMS person + housing, 51 states), OMB Bulletin 23-01 delineation, 2020 DHC
P18 for GQ allocation. Reproduce: `bridge.py` → `pums.py verify|person|housing`
→ `checks.py` (+`checks.py hh`) → `variance.py` → `cube.py` →
`tests/make_fixture.py <build>` → `pytest atlas/tests`.

The delineation file yields **exactly 387 metropolitan CBSAs in the 50 states
+ DC** (393 including Puerto Rico, excluded with the PUMS state set). One spec
correction: the cube has **27,566,784 cells** (387×2×53×3×4×7×8); the brief's
27,564,768 was an arithmetic slip. One documented deviation: `count_cube` is
**float32, not uint16** — allocated counts are fractional (Σ a_eff), and
rounding them would corrupt exactly the conservative n-gate they exist to
feed; the magnitude itself is tiny (max cell 1,520).

## 1. Education and income calibration — pass

The gap Phase 0 left open is closed. Cells within the combined-MOE envelope
(√(pub² + PUMS²)), all 387 metros / restricted to the 193-metro ranked set:

| Check | Table(s) | All 387 | Ranked 193 |
|---|---|---|---|
| Educational attainment 25+, sex × 4 levels | B15002 | 93.4% (2893/3096) | **97.9%** |
| Attainment × age × sex (40 cells/metro) | B15001 | 97.1% (15033/15480) | **99.1%** |
| Earnings distribution by sex (PERNP×ADJINC) | B20001 | 97.0% (3753/3870) | **99.1%** |
| Median earnings by sex (point vs pub MOE; independent ADJINC read) | B20002 | median \|gap\| **1.22%**; 82.2% within 3% | **95.1%** within 3% |
| Per-capita income (PINCP×ADJINC — the cube's exact variable) | B19301 | median \|gap\| **1.10%**, mean signed gap **−0.25%**; 88.6% | **92.7%** |
| Household income (HINCP×ADJINC, housing files) | B19001 | 96.0% (2601/2709) | **97.4%** |

A wrong `ADJINC` application would move medians and per-capita income by
whole percentage points across the board; both sit near 1% with no signed
bias. The SCHL cutpoints for the new axis (HS-or-less / some-college /
bachelor's / graduate) are dictionary-verified (`pums.py verify`, 42
assertions) and reproduce B15002/B15001 after regrouping published levels.
Misses concentrate where every check's misses concentrate: low-purity small
metros outside the ranked set (worst income gap: Logan UT-ID, purity 0.026,
+27% — not served).

## 2. `n_unweighted`, defined precisely

Stored per query, all three: `n_raw` (contributing records — Phase 0's
inflated definition, reported only), `n_alloc = Σ a_eff` (allocated
respondents), and `n_kish = (Σw)²/Σw²` with w = PWGTP·a_eff (Kish effective
sample size). **The suppression gate takes min(n_alloc, n_kish)**; on the
28k-point battery Kish is the binding one 99.9% of the time, so the gate is
effectively a Kish gate — it absorbs both allocation fractions and weight
variability. The serving artifact carries `sumw2_cube.npy` so the gate is
honored at request time, not approximated.

Phase 0 personas re-run under the corrected definition: **exactly two tier
flips**, both ranked → suppressed, both in the metros the correction was
designed to protect against:

| Cell | n_raw | n_alloc | n_kish | flip |
|---|---|---|---|---|
| Ann Arbor, persona A | 142 | 142.0 | **89.4** | ranked → suppressed |
| Killeen-Temple, persona D | 229 | 199.2 | **96.1** | ranked → suppressed |

Full 50-cell re-report: `results/phase1/personas_rerun.csv`.

## 3. Variance model — fitted, validated, and **not shipped**

Fitted `log(RSE) = α + β·log(n_alloc)` per metro over a seeded battery
(120 train + 40 held-out shapes × 387 metros; 28,100 train points;
universe-scale points excluded; per-metro α, β + per-metro validation error
in `results/phase1/variance_fit.csv`, aggregate in
`variance_validation.json`).

- **β median −0.570** (p10 −0.614, p90 −0.542): the −0.5 hard-code was
  indeed biased, as correction 3 predicted.
- **Validation: p90 relative error 44.0%** (median 11.4%) — far beyond the
  15% gate. Per the brief, the approximation is **stopped and reported, not
  shipped**.
- Diagnosis: the tail is identity-filtered domains — Hispanic-filtered
  queries p90 error 181%, nh_asian ~50%, everything else ≤~35%. ACS weights
  are calibrated to county race/Hispanic-origin controls, so identity domains
  sit on structurally different variance curves at the same n. A Kish-
  regressor refit does no better (p90 46%): the failure is domain structure,
  not the choice of count. Candidate Phase 2 fix: a race-domain offset term
  (γ_race), refit and re-validated.
- Consequence for serving: `variance.npy` ships **diagnostic-only**
  (manifest: `shippable: false`, `used_by_api: false`); API responses carry
  no modeled MOE or CV. Exact replicate MOEs exist for every offline result.

## 4. Symmetric rivals — the crude definition was biased, confirmed

Rivals now carry the pool's marital screen. Two documented decisions: rivals
face **no income floor** (they compete for the pool regardless of their own
income) and **no race screen** (the crude kernel stays race-blind; the
pairing kernel is Phase 3).

Movement (same Phase 1 data, crude vs symmetric): **median ratio shift
+146%**, range +31% to +540%, largest exactly where marriage rates are
highest. The diagnostic cases:

- **Provo**: A 0.068 → **0.317**, C 0.060 → 0.384, D 0.089 → 0.446. Provo's
  Phase 0 bottom-of-table result was substantially a rival-definition
  artifact, as suspected — it now sits mid-table on balance for most
  personas (persona B, never-married only, moves least: 0.177 → 0.433).
- **Persona E**: ratios roughly +60–130% (DC 0.049 → 0.076, NY 0.019 →
  0.029); still ranked only in NY / DC / Atlanta — the stress test's
  severity was overstated by the old rivals but its suppression geography
  was right.

## 5. GQ-aware allocation — the Phase 0 defect is fixed

GQ records allocate on `a_gq_inst` / `a_gq_noninst` from 2020 DHC **P18**
tract-level GQ by major type (the DHC's P5 turned out to be a
Hispanic-by-race table — variables are selected from group metadata by
label, with an inst+noninst=total identity asserted per tract). Household
records keep `a_hh`. Fallback (type → total GQ → a_hh) needed for only
19 of 2,462 PUMAs.

B26001 re-check: **Killeen −22.0% → +2.9%; San Jose +9.7% → +2.8%**; all
ten Phase 0 metros pass. Across 387: 276 within ±4% strictly, 344 within
±4%-or-combined-MOE; **43 metros carried as `gq_flag`** in
`features.parquet` (all small; worst Albany OR +57% on a 1,647-person GQ
base). Ranked set: 94.3% pass.

## 6. Tract reconciliation — gate passes

18 relationship-file tracts are absent from the ACS 2024 universe: the 14
retired Suffolk County NY tracts (2020 pop 76,505) and 4 zero-population CT
offshore water tracts. **Zero populated unmatched tracts sit inside
straddling PUMAs**, so the correction-6 build gate passes;
`results/phase1/tract_reconciliation.csv` lists every tract with its 2020
DHC population and straddle status. Connecticut required real work: the 2023
delineation and ACS 2024 use planning regions while the relationship file
and DHC use the old counties; tracts are re-parented by TRACTCE under
statewide-uniqueness assertions (879 matched; the only collisions are the
water tracts, excluded and proven empty on both sides).

## 7. Ranked set, and the middle tier catches nothing

**193 of 387 metros qualify** (population ≥ 250k and ≥ 5,000 allocated
adult records; the spec projected ~190). Purity over the ranked set: median
0.970, but a real tail — five ranked metros sit below 0.5
(Huntington-Ashland 0.009, Roanoke 0.425, Duluth 0.365, Longview TX 0.433,
Hagerstown-Martinsburg 0.468); purity ships in `features.parquet` as the
carried-forward quality signal.

The (n, CV) study over 23,262 ranked-set battery points with true replicate
CVs: once `min(n_alloc, kish) ≥ 100` holds, **true CV never exceeded 12.9%**
(p50 4.4%, p99 9.8%). The 20–30% middle tier fired on **zero** points; the
CV>30 suppression rule fired on zero points the n-gate hadn't already
caught; the n-gate alone agrees with the full specified policy on
**100.00%** of points. The largest Kish n ever observed with true CV>30% was
17, and with CV>20% was 41 — both far below the 100 gate.
**Recommendation: remove the middle tier and the CV rules; gate on n alone.**
`m1.0.0` implements exactly that (with `shown_unranked` retained in the
response contract, always empty, so removing the tier later is a no-op for
clients).

## 8. Endpoint and golden tests

`POST /v1/rank` (FastAPI, single process, loads build `b4d99c1c1dea` at
boot, cubes in memory, never writes, no CORS, loopback bind): three arrays +
counts, scoring = pool + balance pillars with per-request winsorize/log10/
min-max normalisation and exact attribution vs the median metro.
Reproducibility is pinned by the manifest (axis schema validated at load —
a reordered axis or wrong schema version refuses to boot; file SHA-256s
verified).

- **Latency: p50 8.2 ms, p95 8.64 ms, p99 8.8 ms** over 400 randomized
  requests through the ASGI stack (target: p95 < 60 ms). Queries are BLAS
  matrix–vector products over the flattened cubes; no per-metro loops.
- **Golden tests: 14 pass in 0.28 s** on a pinned 12-metro fixture (the
  Phase 0 ten + the lowest-purity ranked metro + the smallest metro): 12
  request vectors, 4 race-filtered, one deliberately below the suppression
  bar (8 vectors produce suppressions), one same-sex pool, exact ranking
  order + exact suppression sets + scores to 5e-5, pinned to
  `model_version` — a model change fails until the version is bumped and
  goldens are regenerated with a commit note. CI workflow committed
  (`.github/workflows/ci.yml`); the repo has no remote yet, so "CI" today
  means the same command running green locally.

## 9. Runtime, disk, artifact (for Phase 2 scoping)

| Stage | Time | Disk |
|---|---|---|
| Bridge (tract pops + DHC GQ, 102 API calls, all assertions) | ~6 min | 30 KB |
| PUMS person, 51 states, 16.1M rows → 14.4M kept | 29.4 min | 2.28 GB zips + 10.5 GB CSV transient (evicted; peak single state 1.49 GB); 1.28 GB parquet |
| PUMS housing, 51 states, 7.7M rows → 6.8M kept | 12.3 min | 0.96 GB zips + 4.3 GB CSV transient; 0.52 GB parquet |
| contrib/hcontrib build | ~4 min | 2.4 GB pool.duckdb |
| Calibration suite (12 tables × 387 metros) | ~12 min | results CSVs |
| Variance battery (160 shapes × 81 replicates × 387 metros) | ~19 min | 2.3 MB points |
| Cube + manifest + fixture + tests + latency | ~4 min | **331 MB artifact** |
| **Total pipeline compute** | **≈ 1.5 h** | **4.4 GB retained** |

The artifact is 331 MB (three float32 cubes 110 MB each + features/variance/
manifest); the server resident set is ~450 MB. Nothing in Phase 2's likely
additions (reach/cost features are per-metro scalars) changes that
materially.

## Deviations and open items

1. `count_cube` float32 (above). 2. Cube cell count corrected (above).
3. The variance model ships diagnostic-only; **serve-time MOE display is an
   open Phase 2 item** (candidate: γ_race term, or per-cell variance storage
   at coarser granularity — both need validation against the same battery).
4. Ranked-set metros with purity < 0.5 are served with the purity flag; a
   Phase 2 decision is whether purity should join the ranked-set gates.
5. B20002 medians are point-compared (no replicate median at 774 cells);
   the published MOE is the envelope — adequate for its role as an ADJINC
   sanity read.
6. Rival income/race decisions are policy, documented in `score.py` and §4.
