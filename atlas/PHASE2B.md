# Phase 2b — the site, the n-only gate, and the stat as the primitive

Build `dc23609755ad` · model `m1.2.0` · schema `cube-v1` (unchanged).
Reproduce: `build.pairing` → `build.cube` → `tests/golden/make_fixture.py
<build>` → `pytest atlas` → `build.validate <build>` →
`cd atlas/web && npm ci && npm test && npx playwright test` →
`npm run dev` against `BUILD_DIR=<build> uvicorn atlas.api.app:app`.

**All six acceptance gates hold.** (1) Every population figure renders with
its margin in the row in the policy strings' exact words — "margin at least
±N", never a bare "±", never a tooltip — asserted per-row by e2e, and the
served CV never appears in a row. (2) Every number reaches its provenance
record in one click: stat rows link to the methodology page's provenance
register, which renders the build manifest's records and the typed license
attributions, not prose. (3) Suppressed metros are permanent footer counts
with verbatim reason strings; `shown_unranked` renders only if non-empty
and a "0 metros shown" line can never render. (4) WCAG 2.1 A/AA: axe
reports **zero serious or critical violations** on all four page shapes,
the hero control has a full keyboard path with a visible focus ring, and
the margin carries a screen-reader supplement ("at least plus or minus …
a calibrated upper bound, not a precise figure") that cannot read as
precise. (5) The permalink round-trips **byte-for-byte both directions**
against 11 cases the Python model emitted through the API's own pydantic
path — a shared test, not inspection. (6) 18 Playwright specs run green in
CI beside the 33-test python suite and the 12-test vitest suite, all
hermetic against the pinned fixture.

The site is Next.js 15 + TypeScript + Tailwind (§8.3), sharing one token
set with the validation review page so the product reads as a single
statistical publication. The browser never calls FastAPI (D04): server
components and a same-origin proxy are the only callers, and nothing is
recomputed client-side — every rendered number, display string, standing
and explanation arrives from the API. Measured, not asserted: **time to
first ranking, median 114 ms** (max 132 ms) over 7 cold production-mode
navigations against the real 387-metro build, against §10.2's 2-second
budget; `/v1/rank` with full stat blocks for all 387 metros now costs
**p50 21.5 ms / p95 23.1 ms / p99 26.6 ms** (target p95 < 60 ms).

## The CV tiers are gone, on this build's own evidence (item 11, ADR 0002)

The ADR's stop-condition was measured first: across the 480-shape battery's
served region (n_gate ≥ 100, est > 0 — 23,028 metro-points, all 387
metros, true 81-replicate CVs), **p99 true CV = 9.80% and the maximum =
11.77%**, with **zero** points above 20% (zero even above Phase 1's
12.9%; the max sits at Fresno at n_gate = 100.04, the gate boundary, where
theory says the worst case lives). The removed rule provably could not
have fired, so removal proceeded: `min(n_alloc, kish) < 100`, an empty
pool, or an empty rival set suppresses; nothing else ranks or demotes.
`shown_unranked` stays in the contract as a permanently empty array;
`cv_above_20`/`cv_above_30` can no longer be produced and the golden and
validation suites assert only the three n-only reasons appear. The served
margin beside every figure is untouched — this changed who gets a rank,
never what sits next to a number. The measurement is recorded in ADR 0002,
on the methodology page, and recomputed into every validation report.
`model_version` → `m1.2.0`, goldens regenerated with the commit note
saying what moved and why.

## The stat is the primitive (item 12, ADR 0003)

Attribution is feature-level: a stat's contribution is
`w_pillar_eff × u_feature_eff × (z_f − ref_f)` with the reference defined
**once**, at feature level, as the median of each normalized feature
across the query's own ranked set; a pillar's contribution is the sum of
its features', and the §7.5 sum identity is **asserted on every request**
(and again in tests, including under missing-feature renormalization,
where the reference score becomes metro-specific through the effective
weights — documented in `scoring.py`). Every metro row, ranked or
suppressed, carries a full stats block — value, server-formatted display
string, standing (percentile of the raw value among the query's ranked
set; interpolated standing for suppressed metros), effective weight,
contribution — so the metro and compare pages render from **one**
`/v1/rank` response and can never renormalize over a set of two.

The D10 comparator is deleted end to end: `comparator()`, `MIN_RANK_GAP`,
`POPULATION_DISTANCE`, the response field, the registry block (the loader
now rejects one), the metric-record field, and every template sentence.
Results lead with the stats that moved them: the API selects `top_stats`
(the same `explain.top_stats` the explanation renders — one place decides),
each shown with display name, real-units value and signed points; e2e
asserts the movers change when the slider moves, which is the feature's
point. The compare page takes two CBSA codes plus the full preference
query string, side by side from one response: rank, pool **with each
metro's own margin** (a pool difference would be a population figure
without a margin, so it is deliberately withheld, with the reason printed
in the cell), odds, and every static stat with both values, the
difference, and each metro's contribution.

**Terminology is data.** Every registry feature carries `display_name`,
`unit`, `unit_short` and `definition`; every pillar a `display_name`; the
loader asserts they exist and rejects the §12.3 banned vocabulary; the
manifest ships the legend and `/v1/meta` serves it, so no user-facing
label lives in code — frontend included. `balance` renders as **Odds**,
the ratio as **matches per 10 people looking** (stored ×10, one decimal,
computed server-side). A hard validation gate sweeps every policy string,
every legend field and all 1,064 rendered explanations of the 12 personas
for "rival/market/supply/inventory/competitor": zero.

## The duplicated explanation, diagnosed (item 12, as demanded)

The 23-of-33 duplication was **not** in the committed code, which is why
it wasn't where it looked. Three facts pin it, 33/33 consistent: the
committed report contains the string "It is helped by" ten times, which
exists in **no committed file**; the committed template renders the same
records cleanly; and the duplicated rows are exactly those whose second
strength also clears the 8-point "large" bucket under today's attribution.
So the committed panel was rendered by a **pre-commit iteration of the
renderer that keyed phrasing on the magnitude bucket alone** — every
large-bucket strength read "Its biggest edge is …", so two large strengths
duplicated it — and after the committed template fixed the mechanism
(position-keyed), **the panel was never re-rendered**. The report was the
output of code that no longer existed, and nothing recorded which code had
produced it.

Three permanent remedies, none of them "the rewrite disposes of it":
`validation_report.json` now carries `generated_by` (git SHA + dirty flag +
timestamp), rendered on the review page; a **hard gate** asserts every
rendered explanation keeps its lead phrase position-unique; and the
face-validity rows now carry `pool`, `pool_moe` and `n_unweighted`, so the
magnitude check — the one that would have caught the mask bug — can be
done from the report (the review page renders them in each row and its
"two gaps" footer is replaced by their closure).

## The interim pairing rate (item 5)

Couples are RELSHIPP 20 ↔ 21/22/23/24 links inside PUMS households —
codes **asserted against the pinned 2020–2024 dictionary** the way `pums
verify` does — with each partnered adult (18–70) weighted `PWGTP × a_eff`
like every pool figure. Zero households had ambiguous partner records.
Sanity, reported not tuned: partnered adults are 54.0% of the pool
universe; the national out-group share is **16.8%** (Pew's 2015 newlywed
figure: 17% — different quantity, right magnitude).

The margin is **measured, not modelled**: per (metro, sex, race) cell the
80 replicate numerator/denominator sums ship in the artifact
(`pairing_cells.parquet`), so any serve-time aggregation over a race
selection carries an exact successive-difference 90% margin. The Gate 0
one-sided model does not extend to this ratio — it was trained on weighted
totals — and it does not need to: it exists because per-query pools are
too combinatorial to measure directly, and a fixed build-time feature
isn't. Served equals measured by construction; the methodology page says
so in its own section, with the §7.3 limitation verbatim in spirit ("how
couples here actually pair," never "what people here want"; subfamily
couples unobserved). The same `min(allocated, Kish) ≥ 100` gate applies,
and a below-gate cell serves `null` plus an explicit reason — never a bare
number, and the frontend never renders null as 0%.

Against Pew's 126-metro 2015 newlywed table (committed as an attributed
validation reference with the full provenance header, matched on CBSA
codes): **Spearman 0.831, Pearson 0.834, n = 124 matched metros** — a
direction check logged as a soft warning rule (bar: 0.30), because the
quantities differ by construction; reproducing the Pew table itself stays
Phase 3's gate, and this estimate is explicitly replaced then. Registered
in `features.yaml` with full provenance, `default_weight: 0`, pinned
unscored by a loader assertion alongside crime.

## The safety rails from the mask-bug family (item 10)

- **Randomized cube-vs-SQL differential, hard gate**: 40 seeded query
  shapes with partial education/income/race/marital filters, computed
  through the flattened-mask gemv path AND by SQL over the contribution
  table, per metro. Worst relative disagreement this build: **2.0×10⁻⁷**
  (tolerance 10⁻³). This is the check that would have caught the `"samier"`
  transposition the day it was written.
- **The loader refuses a model-version mismatch** (explicit
  `allow_model_mismatch=True` for deliberate cross-version work, which
  then fails on the next honest error rather than silently serving).
- **The BUILD_DIR fallback refuses to guess** when more than one complete
  build is present, naming them. `b4d99c1c1dea`'s cubes are retired from
  `data/builds/` (manifest and metros.json kept for the record; its cube
  contents were never wrong — the bug was in the query).
- The validation suite passes **all six hard gates** on this build
  (intervals; suppression with n-only reasons; the differential; rank
  stability 0.875–1.0 across all ten evaluable personas; explanation
  invariants over 1,064 renderings; adversarial GQ with zero watchlist
  appearances). Soft: weight-sensitivity τ 0.944–0.982; external
  correlations +0.20…+0.26 "as measured"; the pairing direction check
  above; the ADR 0002 CV evidence.

## The site, section by section

**Ranking** (§10.1–10.3): opens on results, server-rendered from the query
string or the stated default profile (a woman of 30 seeking men 28–40,
never or previously married — arbitrary by necessity, stated on the page,
one click from being the visitor's own). The slider is the hero and sends
`size_vs_odds`; fine-tune weights live in a disclosure and win over the
slider exactly as the API rules say. Rows: rank, name from the build's
`metros.json`, pool with margin in the required words, odds, API-selected
movers, flags (`low_allocation_purity`, `gq_flag`, missing-feature
renormalization — each with its policy string in the accessible text), and
an expansion to every stat with strip-plot standings. `score_moe` sits in
the detail with `POLICY_STRINGS["score_moe_detail"]` saying what it is.
Below the list, permanently: suppression counts by reason with policy
links; above it, the fewer-than-40 notice when it fires. The list dims
during recalculation and never shifts layout.

**Identity controls** (§10.4, D02): off by default, closed disclosure,
never a funnel step. With a race filter active the counterweight renders
beside the pool at the same visual weight on every ranked row. Religion
appears nowhere — the first draft had a "not available yet" note and the
e2e review removed it as a teaser.

**Metro pages** (§10.5): all 387. The objective profile stands alone —
static stats with standings, the pairing composition with its measured
margin, and crime as the honest state below. The personalised layer
appears above it once preferences exist; an unranked metro says "not
enough sample to rank this metro for this profile" with the reason string,
the respondent count and the bar. No stars anywhere; numbers and margins.

**Methodology & provenance**: renders `docs/methodology.md` verbatim
(synced at build — Turbopack cannot trace outside its root, so a prebuild
step copies the file rather than paraphrasing it), then the versions
section and the provenance register generated from the manifest, with
attribution strings flowing from the typed license registry
(`adapters/base.py` → manifest → `/v1/meta` → render) so counsel's wording
lives in one file. The page now also carries what Phase 2a measured beyond
the spec: the B12007 state-median fallback, the resident-walkability
naming correction, and the interval mechanism's two published numbers.

**Search** (§8.3): a committed 30.5 KB index — delineation titles parsed
into city/state tokens plus hand-written colloquials ("the Triangle" finds
Raleigh and Durham) — fuzzy-matched in the browser, no round-trip.

## Deviations ledger (with reasons)

- **Crime context is not shipped as numbers** (item 6 said "renders at
  CBSA level"). The FBI publishes no metro-level table in the NIBRS era
  (the SRS-era MSA tables ended, CDE bulk is state/agency), CDE's API
  needs a key the build does not have, and agency→CBSA aggregation is a
  phase-sized adapter that D01's own confounder list warns against
  improvising — outside "one backend carve-out". What renders at CBSA
  level today is the FBI's own Caution Against Ranking, the D01 rule, and
  an explicit not-yet-loaded state (D03: an honest blank over a bad
  number). The registry entry stays `context_only` with its provenance.
- **The comparator's removal is the one breaking §8.2 change** (ADR 0003);
  every other response change is additive (stats blocks, counts by reason,
  counterweight fields, `top_stats`, `/v1/meta`).
- **The pairing margin's wording is its own policy string** ("measured
  directly from the survey's 80 replicate weights, 90% confidence") rather
  than "at least this wide" — claiming one-sided conservatism for a direct
  measurement would assert a property it does not have. Gate 1 is
  satisfied the way it is written: the rendered words are the policy
  strings' exact words, from one source.
- **The compare page's difference column is client-side subtraction** of
  two API values — the one deliberate piece of frontend arithmetic,
  specified by ADR 0003, applied only to static stats and never to a
  population figure (which would then lack a margin).
- **Weights defaults became float literals in the API**: pydantic keeps a
  default's type, so int defaults produced two permalink encodings of the
  same request ("0" defaulted vs "0.0" user-sent). Found by the shared
  permalink test's first run; fixed at the source.
- **A "shown but not ranked" screenshot cannot exist**: the tier cannot
  fire (ADR 0002). The evidence is the defensive rendering plus e2e
  asserting the section renders only if non-empty and that no "0 metros"
  line ever appears. The other three states ship as screenshots in
  `results/phase2b/`: ranked, race-filter with counterweight, the
  suppressed metro page, and the suppression footer.
- **`.venv`-side accessibility fixes were design-token changes**, recorded:
  axe's first run found `aria-label` on plain spans (11 nodes; replaced
  with visible-text + sr-only supplements) and 37 contrast failures from
  the review page's `#737b8a` ink-3 (4.1:1); the site's token is `#5b6472`
  (5.8:1). The review page itself keeps its palette — it is an internal
  tool — but shares everything else.

## Accessibility audit result

axe-core (WCAG 2.1 A + AA tags) on the ranking page, the race-filtered
ranking, a metro page and the methodology page: **0 serious, 0 critical**
violations (initial run: 2 violation classes, both fixed as above).
Keyboard: Tab reaches the hero slider in ≤15 stops with a visible ring;
arrows move it and rewrite the URL; a row expands via Enter. Margins have
non-precise screen-reader renderings. Reduced motion is respected
globally; the mobile layout keeps controls one tap away and margins in
every row.

## Timings

| what | measured |
|---|---|
| time to first ranking (production build, real artifact, 7 cold runs) | median **114 ms**, max 132 ms |
| `/v1/rank`, 400 mixed queries, full stat blocks | p50 21.5 / p95 23.1 / p99 26.6 ms |
| pytest (33) + vitest (12) | 0.8 s + 0.1 s |
| Playwright e2e, 18 specs, hermetic incl. both server boots | 11.1 s (+ ~40 s Next build in CI) |
| full validation suite on the real build | ~3 min (differential ~40 s, stability ~2 min) |
| artifact | 339 MB (`pairing_cells.parquet` adds ~8 MB) |

## What Phase 3 inherits

- The **assortative kernel**: empirical age/education/cross-group pairing
  windows replacing the crude symmetric rivals; its gate is reproducing
  the Pew table this phase committed as a reference; the interim
  `cross_group_pairing_rate` and its direction check retire then. The
  serve-time plumbing (cells with replicate sums, gating, display) is
  reusable as-is.
- The **build-time metro narratives**: the §9 metric record is pinned
  again — note its shape changed to feature-level with ADR 0003 while
  nothing consumed it, which is exactly why the change was cheap.
- The **POI union** (registry `status: deferred`, tracked TODO) and its
  coverage-bias regression.
- Religion (Phase 4), behind its own tier badge and sample gate.
- Deployment: the runbook's checklist starts with the counsel review.
