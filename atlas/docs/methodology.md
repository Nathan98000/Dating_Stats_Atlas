# Methodology — Dating Stats Atlas

Versioned with `model_version` (this page: m1.1.0). The frontend renders
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

## Suppression — our policy, not Census's

Census provides the variance machinery and declines the judgment, so the
threshold is a published product policy (D08), computed on the served
(upper-bound) CV so every rule errs toward *not* ranking:

| Condition | Behaviour |
|---|---|
| under 100 effective respondents (min of allocated count and Kish effective n) | suppressed |
| served CV above 30% | suppressed |
| served CV 20–30% | shown with its margin, not ranked |
| served CV at or below 20%, n at or over 100 | ranked, margin beside the figure |
| fewer than 40 metros ranked | the page says so above the list |

## Allocation purity

`allocation_purity` is the share of a metro's estimate arriving through
PUMAs that lie at least 95% inside it. Measured effect (Phase 2a): interval
coverage does not degrade at low purity; agreement with published tables
falls ~5 points in the worst bin. Metros below 0.5 purity carry a visible
`low_allocation_purity` flag rather than being dropped.

## Provenance

Every number traces to `{source, dataset, table, variables, geography,
vintage, transform_id, tier}`, rendered from the build manifest, and every
source carries a typed license with a `shippable` flag the build enforces.
All Phase 2a features are **Measured** tier (ACS, BEA RPP, CBP/QCEW,
EPA SLD street-network measures, NOAA 1991–2020 Climate Normals, IPEDS).
Crime is never scored (D01). The walkability figure is the walkability of
where the metro's **residents** live (SLD population-weighted), not a share
of the matched pool — the pool exists only at metro level.
