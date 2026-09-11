# Phase 0 findings — is the PUMS→metro allocation believable?

**Verdict: yes.** Allocated PUMS estimates reproduce published ACS 2020–2024
5-year tables to within a fraction of a percent on totals and within sampling
error on nearly all demographic cells, with one structural weakness found and
quantified (point-mass group-quarters facilities in boundary-straddling PUMAs,
worst case Killeen) and one measurement caveat (count-controlled published
cells make "within published MOE" the wrong yardstick in a few metros).

Everything below is reproducible: `bridge.py` → `pums.py verify` → `pums.py all`
→ `checks.py`, with sources pinned in `results/fetch_manifest.json` and
`results/geography_manifest.json`.

## 1. Calibration against published tables

All comparisons are against ACS 2020–2024 5-year tables for the same CBSA
(2023 OMB delineation, Bulletin 23-01), pulled from `api.census.gov/data/2024/acs/acs5`.
Calibration queries include institutional GQ because the published universes do.
"Combined MOE" = √(pub² + PUMS²), the statistically meaningful envelope when
both sides carry sampling error. Full per-cell tables are in `results/calibration_*.csv`.

| Check | Against | Result | Notes |
|---|---|---|---|
| Total population | B01003 | **10/10 within 2%** — worst gap **+0.155%** (Killeen), median gap 0.01% | The bridge + weights reproduce metro totals almost exactly |
| Sex × 5-yr age band, 18–69 (200 cells) | B01001 | **140/200 within published MOE; 191/200 within combined MOE** | 19 of the 60 published-MOE misses are cells whose published MOE is < 100 people (count-controlled counties — see §5). Of the 9 combined-MOE misses, **5 are Killeen** (purity 0.78 flagging exactly this); the rest are gaps of 0.3–1.0% against small MOEs |
| Never-married share, 30–34, by sex (20 cells) | B12002 ÷ B01001 | **20/20 within published MOE** | The single most product-relevant check (marital × age × sex through the whole pipeline). Provo's genuinely different market shows up correctly: never-married men 23.0% vs published 21.7% (NY: 57.9% vs 58.1%) |
| Race/ethnicity, 8 cells × 10 metros | B02001 + B03003 | **55/80 within published MOE; 69/80 within combined MOE** | 6 of 11 combined-MOE misses are Hispanic cells where the published MOE is **0** (controlled); gaps there are 0.3–1.1%. Killeen again: White +3.4%, Black −5.2%. NY "some other race alone" −1.4% (see §5) |
| Total group quarters (added check) | B26001 | 8/10 within ±4%; San Jose **+9.7%**, Killeen **−22.0%** | The one real structural failure — see §4 |
| Median gross rent | B25064 | Eyeball pass | San Jose $2,840 > DC $2,027 > NY $1,830 > Austin $1,726 > Atlanta $1,672 > Provo $1,534 > Ann Arbor $1,463 > Mpls $1,440 > Killeen $1,217 > Pittsburgh $1,053 — confirms the resolved CBSA codes are the right metros. (PUMS person files carry no rent, so this validates metro identity only) |
| MOE ~ 1/√n | internal | Slope **−0.587** (r²=0.95) across 97 subpopulation queries | Pooling in universe-scale queries steepens it to −0.71 because calibrated weights collapse variance near control totals — expected ACS behaviour, not a bug |
| GQ contrast (Ann Arbor, Killeen ≫ Pittsburgh) | internal | **Half fails as specified** | Ann Arbor 5.3% vs Pittsburgh 2.5% (2.1×) passes; Killeen 3.4% (1.4×) fails — partly the −22% GQ undercount, partly a miscalibrated prior: Pittsburgh is itself a heavy university-GQ metro (18–24 noninst-GQ share 17.2%, vs Ann Arbor 18.0%, Killeen 16.9%). At 25–34 the expected contrast is clean: Killeen 2.0% / Ann Arbor 2.5% vs Pittsburgh 0.5% |

**A failing check is the finding:** nothing was tuned. The allocation weights
are as first computed from tract populations; the two systematic misses
(Killeen GQ, controlled-cell tolerances) are reported, not patched.

## 2. Persona × metro results

`results/phase0_pools.csv` has the full 50 rows. Pools exclude institutional
GQ; dorm/barracks residents are included and tagged. Ratio = pool ÷ rivals
(rivals: same sex as seeker, seeker's age ±5, same education floor as the
pool filter — deliberately crude, no marital/race screen).

Pool-to-rival ratios (**bold** = ranked; ~~struck~~ = suppressed by display policy):

| Metro | A | B | C | D | E |
|---|---|---|---|---|---|
| New York | **0.206** | **0.557** | **0.129** | **0.267** | **0.019** |
| Washington | **0.228** | **0.517** | **0.158** | **0.303** | **0.049** |
| Atlanta | **0.141** | **0.501** | **0.096** | **0.259** | **0.036** |
| Minneapolis | **0.152** | **0.450** | **0.092** | **0.222** | ~~0.009~~ |
| Pittsburgh | **0.163** | **0.447** | **0.091** | **0.194** | ~~0.003~~ |
| Austin | **0.220** | **0.440** | **0.151** | **0.227** | ~~0.017~~ |
| San Jose | **0.282** | **0.400** | **0.175** | **0.211** | ~~0.005~~ |
| Provo | ~~0.068~~ | **0.177** | ~~0.060~~ | **0.089** | ~~0.001~~ |
| Ann Arbor | **0.162** | **0.407** | ~~0.097~~ | **0.214** | ~~0.009~~ |
| Killeen | ~~0.058~~ | **0.289** | ~~0.052~~ | **0.170** | ~~0.007~~ |

**Tier distribution: 38 ranked, 0 shown-not-ranked, 12 suppressed**
(A: 2, B: 0, C: 3, D: 0, E: 7). Every suppression is driven by the n < 100
respondent rule (e.g. persona E in Provo rests on **one** respondent, pool
estimate 22 ± 43); the CV-only band (20–30%) caught nothing extra at this
metro size. Persona E survives only in NY, DC and Atlanta — the intended
stress-test behaviour, and the ordering (DC 0.049 > Atlanta 0.036 > NY 0.019)
tracks the size of Black professional populations.

Face validity throughout: San Jose is the best market for women seeking
high-earning educated men (A and C, #1 both) and mediocre for men (B, #8);
NY is the best market for men (B 0.557); Provo is at or near the bottom for
everyone (early marriage removes both pools and rivals asymmetrically);
DC leads for persona D. These match the known sex-ratio folklore without any
of it being coded in.

## 3. Allocation purity and group-quarters share

| Metro | purity (PUMS-wt) | noninst GQ, 18–70 | inst GQ, all ages |
|---|---|---|---|
| Ann Arbor | 1.000 | 5.3% | 1.3% |
| New York | 0.995 | 1.9% | 0.6% |
| Provo | 0.982 | 2.9% | 0.3% |
| San Jose | 0.966 | 2.2% | 0.6% |
| Minneapolis | 0.952 | 1.5% | 0.7% |
| Pittsburgh | 0.944 | 2.5% | 1.0% |
| Atlanta | 0.941 | 1.0% | 0.6% |
| Washington | 0.937 | 1.5% | 0.5% |
| Austin | 0.936 | 1.7% | 0.7% |
| **Killeen** | **0.782** | 3.4% | 1.9% |

Only Killeen looks problematic: 22% of its allocated population arrives
through PUMAs shared with non-metro counties, and that same geometry loses
22% of its GQ population (Fort Cavazos barracks are a point mass that
proportional-to-tract-population allocation smears across the PUMA). Its
pools remain usable for 25+ personas but its 18–24 counts and anything
GQ-sensitive carry a real, now-quantified bias. `allocation_purity` is doing
its job as a carried-forward quality signal; Phase 1 should consider a
GQ-aware allocation (tract-level GQ population is published in the decennial
DHC) before trusting military metros.

## 4. Surprises, and what could not be verified

1. **The 2020–2024 5-year PUMS has a single `PUMA` column, coded to 2020
   Census definitions** (verified in the data dictionary; asserted against
   every state CSV header). The 2018–2022 and 2019–2023 files carried dual
   PUMA10/PUMA20 columns; a naive port of code written for those vintages
   would look for the wrong columns. This is why only one bridge was needed.
2. **`ST` was renamed `STATE`** in this vintage — the brief's column list
   needed correction; `pums.py verify` now asserts 35 such semantics
   (including RELSHIPP 37/38 as the person-file GQ identifiers, MSP codes,
   SCHL cutpoints, ADJINC factors) before any extraction.
3. **Count-controlled published cells make "within published MOE"
   unachievable by construction** in near-single-county metros: San Jose,
   Provo and Ann Arbor publish sex×age MOEs as small as ±9 people, and
   Hispanic totals publish MOE = 0. Those cells fail the letter of the
   tolerance while the estimates sit within 0.3–1.1% of the controls. The
   honest test there is the combined MOE (191/200 sex×age, 69/80 race).
4. **The Killeen GQ undercount (−22% vs B26001)** described in §3 — the
   clearest structural finding of the phase. San Jose's +9.7% is the same
   mechanism in reverse (GQ point masses in the high-a PUMAs it shares with
   nothing — likely Stanford-adjacent geography).
5. **14 retired Suffolk County (NY) tract IDs** exist in the 2020
   tract→PUMA relationship file but not in the ACS 2024 tract universe
   (~77k people in 2020). Harmless here — both affected PUMAs are
   single-county, so a = 1.0 regardless — but Phase 1 must reconcile
   relationship-file vintage against the ACS universe, because the same event
   inside a boundary-straddling PUMA would silently bias weights.
6. **DC's weighted person total equals published B01003 exactly** (681,294)
   — a reminder that PUMS weights are controlled to population totals, so
   total-population agreement tests the *allocation*, not the weighting.
7. **Pittsburgh is a heavy university-GQ metro** (dorm share at 18–24 on par
   with Ann Arbor's), which is why the brief's "materially higher than
   Pittsburgh" GQ contrast half-fails even though GQ tagging is working.
8. Not verifiable from a primary source: *why* NY's "some other race alone"
   count runs 1.4% below B02001. The plausible mechanism (differences between
   PUMS editing and tabulation processing of the 2020-revised race write-ins)
   is consistent with the fact that only `RAC1P`/`HISP` are stable across this
   file's internal coding change, but Census documentation does not settle it;
   flagged rather than explained.
9. Definitional choices this phase had to make (documented in code):
   separated (MSP=5) counts as "not currently married" for pools; rivals are
   not filtered by marital status or race (the brief's crude spec);
   `gq_share` in the pools CSV is the noninstitutional-GQ share of the 18–70
   non-institutional population.

## 5. Runtime and disk (for scoping Phase 1 at all 387 metros)

Measured on an Apple-silicon Mac over residential broadband, cold cache:

| Stage | Time | Disk |
|---|---|---|
| Reference files + delineation + dictionary | ~1 min | 3.5 MB cached |
| Tract populations (14 API calls) + bridge | ~1.5 min | 23 KB parquet |
| PUMS download+extract, 14 states, 7.9M rows | **13.5 min** | 1.16 GB zips + 5.1 GB CSV, all transient (peak single-state ~1.5 GB); **176 MB parquet retained** |
| Pool table build + all checks + personas | ~4 min | 257 MB pool.duckdb |
| **Total** | **~20 min** | **peak ~2.5 GB transient; 435 MB retained** |

Phase 1 projection (51 states, ~15.5M person rows, every PUMA touching any
of 387 metros): ~2.3 GB of zips, ~11 GB transient CSV processed sequentially
(peak still ~1.6 GB if eviction is kept), ~1.3 GB retained parquet, ~2 GB
pool table; extraction ~30 min, tract populations ~4 min. The per-metro
persona loop must switch to one `GROUP BY cbsa` scan per filter (the current
10-metro loop would be 387 × 5 × 2 scalar queries); with that change the
whole Phase 1 pipeline should run in well under an hour on this machine and
never need more than ~6 GB of free disk.

## Sources

- OMB CBSA delineation: `list1_2023.xlsx`, Bulletin 23-01 (July 21, 2023)
- 2020 Census Tract to 2020 PUMA relationship file (www2.census.gov/geo/docs/maps-data/data/rel2020/)
- ACS 2020–2024 5-year PUMS, person files, `csv_p{st}.zip` (14 states) + `PUMS_Data_Dictionary_2020-2024.csv`
- ACS 2020–2024 5-year published tables via API vintage `2024/acs/acs5`: B01003, B01001, B12002, B02001, B03003, B26001, B25064
- SHA-256, byte size and fetch time for every file: `results/fetch_manifest.json`
