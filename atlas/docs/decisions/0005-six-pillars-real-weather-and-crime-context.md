# ADR 0005 — Six pillars, weather measured on real days, and crime as coverage-gated context

Status: accepted (Phase 2d, model m2.1.0)
Supersedes: parts of ADR 0004 (§controls, §bands), the Phase 2a Normals
deviation recorded in the registry, and the §5 crime blank from Phase 2b.

## 1. The lifestyle pillar splits into weather and students

Student life was bundled with the weather in one 0.10 pillar, so a
visitor who wanted college towns but hated cold could not say so. The
pillar splits: **weather 0.06** (pleasant days) and **students 0.04**
(students per 1,000 adults) — the old 0.10 divided in exactly the
proportion the two features already carried inside lifestyle (0.6/0.4).
Six pillars: pool .30, balance .25, reach .20, cost .15, weather .06,
students .04.

**The split is a pure re-bookkeeping at default settings, asserted.**
Against the pinned m2.0.0 snapshot on identical data, every metro
carrying both features reproduces its unrounded score to 1.4×10⁻¹⁴
across all 11 personas (`results/phase2d/split_equivalence.json`). The
one principled exception, found by the gate and reported rather than
absorbed: a metro missing ONE lifestyle feature used to hand the whole
0.10 to its sibling feature via within-pillar renormalization; under the
split that metro is missing a whole pillar and the registry's
missing-pillar policy redistributes the weight pro-rata (Boulder and
Palm Bay moved ≤3.9 points). The exception is moot in the shipped build:
with GHCN-Daily matching, **no metro lacks pleasant_days anymore**.

Importance controls become **four** — Cost of living, Social life
(the reach pillar's new display name), Student life, Weather — labels
and one-line subtitles in the registry, levels still mapped through the
registry multiplier table, the frontend still sending choices and never
weights. `importance.lifestyle` is accepted as a deprecated alias for
exactly m2.1.0: its level lands on both split pillars, which reproduces
what it used to mean; naming it alongside either half is a 422.
`size_vs_odds` is **removed** — ADR 0004 granted it one deprecation
version (m2.0.0), and that version has been served.

## 2. Nice days are counted on real days (closing a Phase 2a deviation)

§6 specified GHCN-Daily; Phase 2a substituted the 30-year daily
*Normals* (recorded then as a deviation). That substitution broke the
statistic's meaning: normals average away day-to-day variation, so any
city whose AVERAGE day sits inside the thresholds scores every day —
San Francisco's normal highs sit in the band all year, so it served
**365**, and so did Santa Cruz and San Luis Obispo. The metric measured
"is the climate mild on average", not "how many nice days happen".

m2.1.0 computes on GHCN-Daily observations, 1991–2020: a pleasant day
actually stayed in [55, 85]°F, didn't dip below 40°F, and — new to the
definition — saw **no more than 0.1 inches of precipitation**; a 68°F
day with an inch of rain is not a nice day. All three thresholds live in
the registry. Per station, a year counts with ≥330 valid days, a station
with ≥25 qualifying years; each year scales by 365/valid (a missing
reading is unknown, not un-nice); the metro takes the nearest qualifying
station. San Francisco: 365 → **302**. No metro reaches 365. The whole
feature moved (median absolute change 44 days), the weather pillar with
it, and the goldens are regenerated under the bump.

Three findings from building it, each mechanically guarded now:

- **SNOTEL stations are excluded from matching.** Nine metros first
  matched to mountain snow-monitoring sites (Boulder to a ridge station
  that scored 39). COOP, WBAN and CRN networks measure where people
  live.
- **Station matching anchors at the principal city, not the county.**
  The central-county internal point sits up to 130 km from the city in
  huge Western counties — Reno's "nearest station" was 118 km away. The
  new anchor (TIGERweb Places, county fallback, cached in
  `results/phase2d/city_points.csv`) also fixes the locator-map dots and
  tightens the drive-time phrases in city descriptions; a place whose
  own point is degenerate (San Francisco's includes the Farallon
  Islands, 50 km offshore) is detected by having no station within 20 km
  and falls back to the county anchor.
- **"The wettest metro ranks near the bottom" is not how this climate
  behaves**, by inches (Gulf-coast rain comes in bursts on warm days —
  Daphne, AL sits mid-pack, correctly) or by rain-days (the drizzle
  belt's wet days are mostly cold days already excluded by temperature).
  The validation gate asserts the **mechanism** instead: the rain term
  only ever removes days (universally true) and removes most where wet
  days are mild (Spearman 0.81 against rain-days; the Appalachian
  wet-mild belt loses the most, ~50 days). The coldest-metro assertion
  stands and passes (Fairbanks, bottom decile).

## 3. Standing bands: five, cut on quintiles, coloured by direction

ADR 0004's three tertile bands become five national quintile bands
(edges 20/40/60/80 in the registry). The label states the POSITION; the
colour comes from a per-feature registry `band_direction` — good_low
(rent, prices), good_high (venues, walkability, nice days), neutral
(students, population) — through one tone rule in the loader, so a
position can never be coloured as a virtue by accident. Population keeps
absolute edges (250k/500k/1M/2.5M) because quantiles over mostly-small
metros would mislead, exactly as tertiles did in ADR 0004.

## 4. Crime: coverage-gated context, never scored (D01 implemented)

The FBI publishes no metro-level table in the NIBRS era, so the Phase 2d
adapter builds the aggregation: CDE agency-level offence counts →
county via each ORI's roster county (lat/lon nearest-county fallback
for NOT SPECIFIED, unmatched names, and Connecticut, whose CDE counties
predate the delineation's planning regions) → CBSA via the pinned
delineation. Served per metro: violent and property rates per 100,000,
and **coverage** — the share of the metro's population living in
agencies that reported a full year.

The two fatal traps, engineered against rather than remembered:

- **Rates divide by the covered population**, never the metro's — a
  metro-wide denominator would understate every rate by exactly the
  coverage gap.
- **A full year means 12 non-null months in both offence categories**,
  plus the transition-junk rule: the NIBRS cutover left some large
  agencies with twelve numeric months of near-nothing (New York City's
  2021 "reported" violent rate computes below 2 per 100k). An
  agency-year above the registry population bar whose violent AND
  property rates both sit under the registry implausibility bars counts
  as not reporting, and every exclusion is named in the build report.

Coverage below the registry floor renders the blank state instead of a
figure. The FBI's caution against ranking renders beside every figure;
on the compare page the non-comparability note sits between the two
columns. No composite, no ranking, no stat page — a permanent explainer
page instead. Crime enters no score, no weight, no stats list, asserted
at registry load, in the engine tests and in the validation suite.

## 5. Stat pages, and what may never get one

Every static statistic gets a page ranking the 193 ranked-set cities on
that one measure, served from a build-time JSON (no API call, no
recomputation, same artifact and formatting code as the city pages —
cell-for-cell agreement is by construction and asserted by e2e).
Matches and balance never get one (both depend on the visitor's search);
crime never gets one (D01).

## 6. The race-panel disclosure moved (raised, not decided)

Item 3 stripped the editorial sentence from the race control; the
always-counted-groups disclosure now lives ONLY on How it works and in
the methodology. Whether to keep the always-on rule with its relocated
disclosure, or drop it for a plain six-group filter, is raised for
Nathan in PHASE2D.md — this ADR records the relocation, not a decision
on the rule.
