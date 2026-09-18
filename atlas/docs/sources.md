# Data sources

Every number the site serves comes from one of the sources below. Each one is a
public dataset from a federal statistical agency, with the single exception of
the city and stat-page photographs, which come from Wikimedia Commons under
licences recorded per image.

The adapters in `atlas/pipeline/adapters/` carry the machine-readable version of
this list: `source_id`, `vintage` and a `LicenseTerms` record per source, with
`shippable` as the load-bearing field. Every feature in
`atlas/pipeline/registry/features.yaml` carries a `provenance` block naming its
source, dataset, table, variables, geography and vintage. This page is the human
copy — the one to hand to counsel or link from the methodology page.

Last checked against the build: 18 September 2026 (model m2.4.0).

## Sources that reach the site

| Source | Publisher | What it provides | Link |
|---|---|---|---|
| ACS 5-year public-use microdata (PUMS), 2020–2024 | Census Bureau | Every people count: pool size, the sex ratio, and the age / marital / education / income / race levels behind them | [census.gov/programs-surveys/acs/microdata.html](https://www.census.gov/programs-surveys/acs/microdata.html) |
| ACS 5-year detailed tables, 2020–2024 | Census Bureau | Tract populations for the geographic bridge; county and county-subdivision renter households (B25003) that weight the rent aggregation; the calibration checks | [api.census.gov/data/2024/acs/acs5.html](https://api.census.gov/data/2024/acs/acs5.html) |
| 50th Percentile Rent Estimates, FY2027 | HUD | "Rent" — the one-bedroom 50th-percentile gross rent (shelter plus tenant-paid utilities), county file, aggregated to metros by renter-household weights | [huduser.gov/portal/datasets/50per.html](https://www.huduser.gov/portal/datasets/50per.html) |
| 2020 Census Demographic and Housing Characteristics File (DHC) | Census Bureau | Tract population (P1) and group-quarters population (P18) — the allocation weights and the institutional split | [census.gov/data/tables/2023/dec/2020-census-dhc.html](https://www.census.gov/data/tables/2023/dec/2020-census-dhc.html) |
| Census geographic relationship files | Census Bureau | Tract→PUMA and 2020↔2010 tract crosswalks — how PUMA-level microdata becomes metro-level estimates | [census.gov/geographies/reference-files/time-series/geo/relationship-files.html](https://www.census.gov/geographies/reference-files/time-series/geo/relationship-files.html) |
| OMB metro delineations, Bulletin 23-01 (July 2023) | OMB, published by the Census Bureau | Which counties form each of the 387 metro areas, and each one's principal cities | [census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html](https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html) · [Bulletin 23-01 (PDF)](https://www.whitehouse.gov/wp-content/uploads/2023/07/OMB-Bulletin-23-01.pdf) |
| TIGERweb REST services | Census Bureau | Internal points for counties and places — metro display names, map dots, and the joins to weather stations and police agencies | [tigerweb.geo.census.gov/tigerwebmain/TIGERweb_restmapservice.html](https://tigerweb.geo.census.gov/tigerwebmain/TIGERweb_restmapservice.html) |
| Cartographic boundary file, states at 1:20,000,000 (2023) | Census Bureau | The state outlines on the locator map, projected to static geometry at build time | [census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html](https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html) |
| Regional Price Parities, metro areas (MARPP) | Bureau of Economic Analysis | "Everyday prices" — the goods and services-other price levels in the cost pillar | [bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area](https://www.bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area) |
| County Business Patterns, 2023 | Census Bureau | "Places to go out" — bars, cafés and venues per 100,000 adults | [census.gov/programs-surveys/cbp.html](https://www.census.gov/programs-surveys/cbp.html) |
| Smart Location Database v3.0 | US Environmental Protection Agency | "Getting around on foot" — the street-network walkability index (transit measures deliberately excluded) | [epa.gov/smartgrowth/smart-location-mapping](https://www.epa.gov/smartgrowth/smart-location-mapping) |
| GHCN-Daily station observations, 1991–2020 | NOAA / NCEI | "Nice days a year" — counted from daily TMAX, TMIN and PRCP records | [ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily](https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily) |
| IPEDS, 2023–24 collection | NCES, US Department of Education | "Students" — college students per 1,000 adults | [nces.ed.gov/ipeds/use-the-data](https://nces.ed.gov/ipeds/use-the-data) |
| Crime Data Explorer (summarized agency data) | FBI | Reported violent and property offence rates, and the reporting-coverage share. Shown as context on city and compare pages; **never scored** | [cde.ucr.cjis.gov](https://cde.ucr.cjis.gov/) |
| City and stat-page photographs | Wikipedia / Wikimedia Commons contributors | One lead photograph per city page and per stat page, displayed unmodified with per-image attribution | [commons.wikimedia.org](https://commons.wikimedia.org/) |

## The same sources in detail

### ACS 5-year PUMS, 2020–2024
Person and housing files for all states, plus the vintage's own data dictionary,
which the build verifies variable by variable before it trusts a single code.
Powers `pool_size`, `pool_balance` and `who_lives_here`, and the whole pool cube
beneath them.

- Files: `https://www2.census.gov/programs-surveys/acs/data/pums/2024/5-Year/csv_p{ST}.zip` and `csv_h{ST}.zip`
- Dictionary: [PUMS_Data_Dictionary_2020-2024.csv](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/PUMS_Data_Dictionary_2020-2024.csv)
- Licence basis: US public domain (17 USC 105); [Census API terms of service](https://www.census.gov/data/developers/about/terms-of-service.html)

### ACS 5-year detailed tables, 2020–2024
Pulled from the API dataset `2024/acs/acs5`.

- **B25003** (tenure, variable `B25003_003E` — renter-occupied households), at
  county level and, in New England, county-subdivision level: the weights for
  the HUD rent aggregation since m2.4.0
- **B01003** (total population): tract populations for the PUMA→metro bridge, and the metro-total accuracy check
- **B01001, B12002, B02001, B03003** (age by sex, marital status, race, Hispanic origin): the published totals the cube is calibrated and checked against

### HUD 50th Percentile Rent Estimates, FY2027
The rent statistic since m2.4.0 (ADR 0008). County file
`FY2027_FMR_50_county.xlsx` (one-bedroom column `rent_50_1`; New England
published as county-subdivision rows), area file for the exactness check,
both fetched with hashes recorded. Per HUD's FY27 methodology: a gross rent
(shelter plus tenant-paid utilities) on HUD's adjusted-standard-quality ACS
2020–2024 base — cash rent, ten acres or less, full plumbing, complete
kitchen, meals not included, units under the 75th percentile of
public-housing rents removed — carried into the fiscal year by a
recent-mover adjustment, a 2024→2025 gross-rent inflation factor and a trend
factor; published 50th-percentile rents are floored at the FMR. FY2027 is
the first year the utility component comes from composite EIA/BLS inflation
factors rather than the discontinued metro CPI utility indices.

- Landing page: [huduser.gov/portal/datasets/50per.html](https://www.huduser.gov/portal/datasets/50per.html)
- Methodology: [FY27-Public-FMR-Methodology.pdf](https://www.huduser.gov/portal/datasets/fmr/fmr2027/FY27-Public-FMR-Methodology.pdf)
- Licence basis: US public domain (17 USC 105)

### 2020 Census DHC
Tract-level P1 and P18, pulled from `2020/dec/dhc`. P18 gives the group-quarters
population by major type, which is how the build separates institutional
residents from the dating population. Variables are selected from the group
metadata by label rather than by variable number, after Phase 1 confirmed that
P5 is a Hispanic-by-race table and not what its position suggests.

### Census relationship files
- [2020_Census_Tract_to_2020_PUMA.txt](https://www2.census.gov/geo/docs/maps-data/data/rel2020/2020_Census_Tract_to_2020_PUMA.txt) — the main bridge
- [tab20_tract20_tract10_natl.txt](https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/tab20_tract20_tract10_natl.txt) — needed because the EPA's walkability data is on 2010 block groups
- [2010_Census_Tract_to_2010_PUMA.txt](https://www2.census.gov/geo/docs/maps-data/data/rel/2010_Census_Tract_to_2010_PUMA.txt)

### OMB metro delineations
`list1_2023.xlsx` (CBSAs, metropolitan divisions and CSAs) and `list2_2023.xlsx`
(principal cities), as published July 2023 under OMB Bulletin No. 23-01. These
define the geography the whole site ranks: "San Francisco" means the metro area,
not the city limits. A copy of the bulletin is also mirrored by
[BLS](https://www.bls.gov/bls/omb-bulletin-23-01-revised-delineations-of-metropolitan-statistical-areas.pdf).

### TIGERweb
Two layers, both cached locally after first fetch:
`Places_CouSub_ConCity_SubMCD/MapServer` for place internal points, and the
generalized county layer (with Connecticut planning regions) for county internal
points. The Gazetteer's yearly point files are no longer published on www2;
TIGERweb is the Census-operated equivalent.

### Cartographic boundary file
[cb_2023_us_state_20m.zip](https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_state_20m.zip),
already the generalized 1:20,000,000 rendition, projected at build time into
static SVG paths so no mapping library reaches the browser.

### BEA Regional Price Parities
[MARPP.zip](https://apps.bea.gov/regional/zip/MARPP.zip), the metro-area RPP
file (2024 data, released February 2026, on the OMB 23-01 delineation). The site
uses **Goods** and **Services: Other** rather than the all-items RPP, because
all-items embeds a large housing-rents component that rent already measures.

### County Business Patterns
API dataset `2023/cbp`, establishment counts by NAICS 2017 code for the
eating-drinking-and-entertainment industries, per metro.

### EPA Smart Location Database v3.0
June 2021 release, on 2010 block groups, read from
`https://geodata.epa.gov/arcgis/rest/services/OA/SmartLocationDatabase/MapServer`.
Street-network measures only — the transit measures rest on a GTFS snapshot taken
during the deepest pandemic service cuts and are excluded.

- Licence basis: CC0 / US public domain

### NOAA GHCN-Daily
Daily summaries for the station matched to each metro, 1991–2020.

- Station inventory: [ghcnd-inventory.txt](https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-inventory.txt)
- Observations: `https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations={station}`
- Variables: TMAX, TMIN, PRCP

### IPEDS 2023–24
- [HD2023.zip](https://nces.ed.gov/ipeds/datacenter/data/HD2023.zip) — institutional directory
- [EF2023A_DIST.zip](https://nces.ed.gov/ipeds/datacenter/data/EF2023A_DIST.zip) — enrollment by distance-education status, so fully-online enrollment does not count as people who live there

### FBI Crime Data Explorer
Agency roster plus summarized monthly offence counts per agency, read from
`https://api.usa.gov/crime/fbi/cde` with a key from
[api.data.gov](https://api.data.gov/signup/). Agencies are mapped to counties by
name within state, falling back to the nearest county internal point, then
aggregated to metros with coverage-weighted denominators: rates divide by the
*covered* population, never the metro's.

Served reference year **2025** — the latest complete year and also the
best-covered (372 of 387 metros clear the coverage floor). Displayed with the
FBI's own [Caution Against Ranking](https://ucr.fbi.gov/cautionagainstranking.pdf)
attached, and pinned to a zero weight in the registry so it cannot enter a score.

### City and stat-page photographs
The lead image of each metro's English Wikipedia article, resolved through the
REST summary and MediaWiki APIs, with licence, author and links read from the
Commons `imageinfo` / `extmetadata` fields.

- [Wikipedia REST API](https://en.wikipedia.org/api/rest_v1/) · [MediaWiki API](https://www.mediawiki.org/wiki/API:Main_page)
- Licences accepted: public domain, CC0, CC-BY, CC-BY-SA. Nothing NC or ND, and
  nothing whose licence or attribution field could not be read.
- 365 of 387 metros shipped a photograph; the rest fall back to the map card.
- Per-image manifest — source page, direct file, author, licence, deed link,
  retrieval date and SHA-256 — at `results/phase2e/city_images.csv`.
- These are the site's first shipped third-party assets and are the one item in
  this list that needs counsel's read before launch.

## Used as a check only — does not reach the site

| Source | Publisher | Why it is here | Link |
|---|---|---|---|
| Quarterly Census of Employment and Wages, 2023 annual averages | Bureau of Labor Statistics | Independent cross-check on County Business Patterns establishment counts, including where CBP suppresses a cell and QCEW does not | [bls.gov/cew](https://www.bls.gov/cew/) |

Read from `https://data.bls.gov/cew/data/api/2023/a/industry/{naics}.csv`.
Licence basis: US public domain (17 USC 105); [BLS copyright statement](https://www.bls.gov/opub/copyright-information.htm).

## Superseded

| Source | Replaced by | Why |
|---|---|---|
| [NOAA U.S. Climate Normals 1991–2020 (daily)](https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals) | GHCN-Daily observations, in Phase 2d | Averaging thirty years into one typical day destroys the day-to-day variation a "nice day" count is measuring — San Francisco came out at 365 nice days. The adapter file remains because it hosts the TIGERweb county-point helper. |
| ACS table B25064 (median gross rent, all units) | ACS table B25031 (one bedroom), in m2.3.0 | The all-units median moves with a metro's mix of studios and family houses, so it was reading as a cost-of-living difference when it was partly a housing-stock difference. |
| ACS table B25031 (median gross rent, one bedroom) — for rent | HUD FY2027 50th Percentile Rent Estimates, in m2.4.0 | A 2020–2024 average against a measure the site describes as current; HUD's series shares the same ACS base but is adjusted to recent movers, trimmed of subsidised units and trended into the fiscal year. The ACS detailed tables stay in the build for populations, renter-household weights and calibration. |

## Standards and documentation

Not data, but the record behind how the categories are defined:

- **OMB Statistical Policy Directive No. 15.** The site's race and ethnicity
  categories follow the 1997 standards, which remain in force.
  [The March 2024 revision](https://www.federalregister.gov/documents/2024/03/29/2024-06469/revisions-to-ombs-statistical-policy-directive-no-15-standards-for-maintaining-collecting-and)
  was deferred rather than withdrawn.
- **ICR 202605-0607-002**, approved 9 July 2026, is the record of that deferral
  for the ACS itself:
  [ICR record](https://www.reginfo.gov/public/do/PRAViewICR?ref_nbr=202605-0607-002) ·
  [supporting statement](https://www.reginfo.gov/public/do/PRAViewDocument?ref_nbr=202605-0607-002) ·
  [control number history](https://www.reginfo.gov/public/do/PRAOMBHistory?ombControlNumber=0607-0810).
  See `docs/decisions/0001-acs-race-ethnicity-standard.md`.
- **Licence basis for the federal sources**: works of the US government are not
  under copyright (17 USC 105). The per-agency statements the build records are
  the [Census API terms of service](https://www.census.gov/data/developers/about/terms-of-service.html),
  the [BLS copyright statement](https://www.bls.gov/opub/copyright-information.htm),
  and [BEA](https://www.bea.gov/).

## Considered but not used

Listed so the absence is on the record rather than an oversight. None of these
has been fetched, and none reaches the site.

| Source | Would provide | Status |
|---|---|---|
| [Overture Places](https://docs.overturemaps.org/guides/places/) | Venue counts, replacing the CBP proxy | Deferred with `poi_venue_density`; permissive licence, attribution required |
| [Foursquare OS Places](https://opensource.foursquare.com/os-places/) | Venue counts, merged with the above | Deferred; Apache 2.0, NOTICE must be preserved |
| [Cooperative Election Study](https://cces.gov.harvard.edu/data) | The religion estimate (Phase 4) | Not started; CC0 |
| [2020 US Religion Census](https://www.usreligioncensus.org/) (ASARB) | Religious adherence by county | Not started; terms need a read before use |
| [PRRI American Values Atlas](https://ava.prri.org/) | County-level religious composition | Not started; terms need a read before use |
