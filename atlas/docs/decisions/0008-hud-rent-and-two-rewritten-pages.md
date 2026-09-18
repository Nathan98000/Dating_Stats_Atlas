# ADR 0008 — Rent from HUD, a renter-weighted aggregation, and two pages rewritten

Date: 2026-09-18 (Phase 2g, model m2.4.0, build 5d0e3ca2f708)
Status: accepted

## 1. Rent moves to HUD's FY2027 50th Percentile Rent Estimates, renamed `rent_1br`

The ACS B25031 one-bedroom median (m2.3.0–m2.3.1) is a 2020–2024 average.
HUD's 50th-percentile series is built on the SAME ACS 2020–2024 base — per
HUD's FY27 methodology: "adjusted standard quality" gross rents (cash rent,
ten acres or less, full plumbing, complete kitchen, meals not included;
units below the 75th percentile of public-housing rents removed) — then
adjusted to recent movers, inflated 2024→2025, and trended into fiscal
2027, so the card speaks in current dollars for the standard-quality
private market a mover actually faces. Gross rent includes tenant-paid
utilities, which is why Phase 2f's unit line ("median 1-bedroom monthly
rent, with utilities") ships unchanged — the new source vindicates the old
sentence. Two recorded caveats from HUD's own document: published
50th-percentile rents are floored at the (40th-percentile) FMR, and FY2027
is the first year the utility component comes from composite EIA/BLS
inflation factors rather than the metro CPI utility indices BLS
discontinued in January 2025 — the utility half of this number is
new-method this year.

The feature id was renamed `median_gross_rent` → **`rent_1br`** while the
site has no public URL: the metro figure is no longer a median of anything
(see §2), so the old id would have named a thing the column does not hold.
`/stats/median_gross_rent` redirects permanently. The rent-regulation
caution box was deleted with its registry string: HUD trims the subsidised
bottom of the distribution and adjusts to recent movers, so the
stabilised-tenancy drag the note described is not in this measure.

Consequence: rent carries 0.5 of the cost pillar, so scores and ranks
moved (MODEL_VERSION m2.4.0, goldens regenerated). The before/after is in
PHASE2G.md; the level shift is median ×1.278 across the 193 (p10 1.144,
p90 1.458), 162 of 193 overall ranks move under the default search with
Kendall τ 0.963, and nothing else moved: the three cubes and every
non-rent feature column are byte-identical to m2.3.1's build, asserted in
`rent_swap_report.py`.

## 2. A metro's rent is a renter-household-weighted mean of county figures

HUD publishes per FMR area — CBSAs, subdivided into HUD Metro FMR Areas
where the data justifies it — so 141 of the 387 metros span more than one
published rent. The county file joins to the site's metros exactly through
the OMB 23-01 delineation the build already holds, and one rule applies
everywhere: **a metro's rent is the mean of its counties' one-bedroom
medians, weighted by renter-occupied households** (ACS `B25003_003E`) —
renters rather than population, because an average of rents should be
weighted by the households actually paying one. In the six New England
states HUD publishes town rows instead of county rows, and the same weight
applies one level down (county-subdivision renter households), with a
name-based fallback for the five rows whose FIPS subdivision codes lag the
2024 revisions (four Massachusetts "Town cities" and one Maine township,
each named in the build report).

**Owned plainly: a weighted mean of county medians is not the metro's
median.** It cannot be, from published aggregates. What keeps it honest:
for the 246 metros whose counties all sit in one FMR area the weights
cannot move the mean, and the figure is asserted equal to HUD's own
published area figure at build time; for the composed 141 the within-metro
spread is reported (Washington DC's counties span $1,282; the top ten are
in PHASE2G.md), so the reader can see where a single number is doing a lot
of work.

Rejected options:

- **HUD's area file alone** — leaves a multi-HMFA metro ambiguous: New
  York spans seven published rents, Boston six; there is no defensible way
  to pick one.
- **Population weighting** — weights people who own their homes into an
  average of rents.
- **Holding the ACS figure** — a 2020–2024 average against a measure the
  site now describes as current; it also kept reading Austin's cooling
  one-bedroom market at its five-year average.

## 3. Two explainer pages replaced, and what that removed

`docs/methodology.md` (How it works) and `docs/crime.md` (About the crime
figures) are Nathan's rewrites, shipped verbatim with two corrections the
build required — the metro-count sentence (the site counts matches in all
387 metros and ranks the 193 that clear BOTH conditions: 250,000 people
and 5,000 allocated adults) and the rent row of the data table (HUD, per
§1) — plus one typo fix ("nationally-recognized"). What the replacements
removed from the site: the methodology page's margins-of-error section,
its crime-shown-never-ranked section (the crime page and the table's own
note now carry that), its reproducibility paragraph, and the old intro's
"available on request" sentence; the crime page's account of coverage
tightened, and it never carried the implausible-submission story (the
NIBRS transition exclusions live in the build report only — recorded in
PHASE2G.md so the absence is on the record).

## 4. The margins and reproducibility paragraphs are gone by decision

Recorded plainly, because a reviewer will otherwise ask: **the site
computes a margin of error on every count, suppresses on it, and — after
this rewrite — no longer tells anyone that this machinery exists.** The
interval model still runs on every build (Gate 0 calibration asserted),
`pool_moe` and `cv` are still returned by the API, ADR 0004 still keeps
them off the pages, and the technical strings remain available on request.
Likewise the `/r/[dv]/[mv]/[token]` reproduction route **keeps working** —
every ranking the API serves remains exactly reproducible under its pins —
but no page explains it any more. The counsel packet carries the same
disclosure sentence.
