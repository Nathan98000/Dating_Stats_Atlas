# Methodology — Dating Stats Atlas

Versioned with `model_version` (this page: m1.2.0). The frontend renders
this page's interval, suppression and provenance language verbatim.

## What the numbers are

Every pool estimate is a weighted sum over ACS 2020–2024 5-year PUMS person
records, allocated from PUMAs to metros through a tract-population bridge
(household records) and a 2020-Census DHC P18 group-quarters bridge
(dormitory/barracks and institutional records separately). Institutional
group quarters are excluded from every pool. The file is 2020–2024 —
never "2024".

## Margins of error — "at least this wide"

Every population figure carries a margin of error, always visible in the
row. The margins are **calibrated upper bounds**, not symmetric "±"
intervals:

> The true margin of error is at or below the shown margin on **at least
> 95% of held-out validation queries (measured: 97.5%)**, and the shown
> margin overstates the true one by **23% at the median (gate: at most
> 25%)**.

Both numbers are measured on a 480-shape query battery evaluated with the
full 81-replicate ACS machinery, with 30% of query shapes AND 20% of metros
held out, and are recorded in the build manifest. A two-sided model was
attempted first and failed its 15% error gate (90th-percentile relative
error 23.6%); the failure and its diagnosis are published rather than
shipped. An interval that is too wide on a known, measured fraction of
queries is defensible; one that is too narrow is not.

The served coefficient of variation, where shown, is an upper bound from
the same mechanism. It appears only in expandable detail, labelled as a
bound, and **decides nothing** (see below).

## Suppression — our policy, not Census's

Census provides the variance machinery and explicitly declines the
judgment, so the threshold is a published product policy (D08, as amended
by ADR 0002). The gate is **sample size alone**:

| Condition | Behaviour |
|---|---|
| under 100 effective respondents (min of allocated count and Kish effective n) | suppressed |
| empty pool, or an empty comparison set for the odds ratio | suppressed |
| everything else in the ranked set | ranked, margin beside the figure |
| fewer than 40 metros ranked for a query | the page says so above the list |

Earlier drafts of this policy carried two further rules keyed to the
coefficient of variation (suppress above 30%, show-but-don't-rank at
20–30%). They were removed in m1.2.0, for a measured reason: across the
480-shape validation battery, on the 23,028 metro-points where the
sample-size gate passes, the true replicate CV never exceeds **11.8%**
(99th percentile **9.8%**) — so the CV rules provably could not fire on
the data. Worse, Phase 2a computed them on the *served* CV, which is a
deliberate upper bound (median overstatement 23%), so the only way the
tier could have fired was through the interval model's conservatism rather
than through anything about a metro's data. A rule that cannot fire except
by accident is not a safeguard, and it was removed rather than carried
(ADR 0002). **The margins themselves are unaffected**: this changed which
metros get a rank, never what is shown beside a number.

## Allocation purity

`allocation_purity` is the share of a metro's estimate arriving through
PUMAs that lie at least 95% inside it. Measured effect (Phase 2a): interval
coverage does not degrade at low purity; agreement with published tables
falls ~5 points in the worst bin. Metros below 0.5 purity carry a visible
`low_allocation_purity` flag rather than being dropped.

## How couples here actually pair — the interim pairing rate

Whenever a race or ethnicity filter is active, the site shows, beside the
pool and at the same visual weight, the **cross-group pairing rate**: among
partnered people of the sought group in that metro, the share whose spouse
or unmarried partner is outside the group. It comes from real couples in
PUMS households — spouse and partner links to the household reference
person, verified against the pinned data dictionary — weighted exactly like
every pool figure.

Its margin is not modelled: because the pairing cells are fixed at build
time, the survey's own 80 replicate weights are evaluated directly, so the
served margin **is** the measured one (90% confidence). The one-sided
calibrated bound used for pool figures exists because per-query pools are
too combinatorial to measure directly; it is not needed here and is not
claimed here.

The limitation, stated plainly (§7.3): observed couples describe who
**matched**, not who was **available**. The rate is endogenous to the very
conditions being measured. The copy therefore says "how couples here
actually pair," never "what people here want." PUMS also links only the
reference person's partner, so couples in subfamilies are not observed.
This interim estimate is replaced in Phase 3 by the full assortative
kernel, whose validation gate is reproducing Pew's published metro
intermarriage table; until then the interim rate is checked against that
table for direction only (measured: Spearman 0.83 across 124 matched
metros — different quantities, same ordering).

## Terminology

The `balance` pillar renders as **Odds**, and the ratio renders as
**matches per 10 people looking**. "Market", "supply", "inventory" and
"rival" are accurate modelling terms and corrosive product copy (§12.3);
none of them appears in a rendered string, and a build gate fails if one
does. Every label, unit and definition on the site comes from the feature
registry through the build manifest — no user-facing label lives in code.

## Findings the spec had not anticipated

- **B12007 (median age at first marriage) is not published at CBSA level**
  in the 2024 ACS 5-year release — every metro value returns an annotation
  jam. The external-correlation check falls back to state medians through
  each metro's primary state, and is labelled as coarse.
- **Walkability is the walkability of where the metro's residents live**
  (EPA SLD, population-weighted), not "% of the pool in walkable tracts" —
  the pool exists only at metro level after PUMA allocation, so the
  proposal's §5.3 mock wording was corrected rather than inherited.
- The **score margin** shown in row detail is a first-order approximation
  stacked on the one-sided pool and odds bounds, with the query's
  normalization frozen. It is labelled an approximation and kept out of
  the ranking row.

## Provenance

Every number traces to `{source, dataset, table, variables, geography,
vintage, transform_id, tier}`, rendered from the build manifest, and every
source carries a typed license with a `shippable` flag the build enforces.
All scored features are **Measured** tier (ACS, BEA RPP, CBP/QCEW,
EPA SLD street-network measures, NOAA 1991–2020 Climate Normals, IPEDS).
Crime is never scored (D01) and renders, when its context data ships, only
with the FBI's own Caution Against Ranking attached.
