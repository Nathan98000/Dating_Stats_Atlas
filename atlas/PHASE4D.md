# Phase 4d — political lean: the source is in, and the state-totals check stopped the phase

Every number here is read from `results/phase4d/validation.json` (written by
`pipeline/build/political_lean.py`, whose rules were committed in 86df38e
before it first ran). Nothing on the site has changed: no registry entry, no
build, no manifest, no page, no score and no rank.

**In plain words, for Nathan.** The election data is in, and its licence is
what the brief expected: CC0 (free to use), with the lab asking for its
citation. Built the way the brief says, adding votes county by county and
dividing once, 380 of the 387 metros get a figure, and 187 of the 193
ranked. The seven without one are:

- **Connecticut's five metros.** The data reports Connecticut by its old
  counties, and the metros are now drawn on the new planning regions.
- **Anchorage and Fairbanks.** Alaska reports by legislative district, and
  some districts reach past each metro's edge. One district takes in all
  of Denali Borough, for example.

Then one of the brief's own checks stopped the work. In six states, the
votes added up county by county don't match the lab's statewide totals
to within 0.1%:

- **Maine and Rhode Island** are short of ballots the states count only
  statewide, probably overseas and military ballots, which nobody can put
  in a county. That's 1.2% of Harris's Maine votes and 0.5% of her Rhode
  Island votes.
- **Arizona, Delaware, Nebraska and Virginia** match on Harris and Trump
  exactly (Virginia to within 0.07%). The count for everyone else is off
  by 0.2–0.5%, apparently because write-ins are counted differently.

On the site's whole-number percentages, the gaps matter little. Suppose the
missing votes were spread like the counted ones. Then 16 of the 28 metros
in those six states would show one number a point different, and never
more than a point. Seven of those 16 are ranked. Your call is below (§5).

## 1. The source and its licence

- **Dataset.** MIT Election Data and Science Lab, *County Presidential
  Election Returns 2000–2024*, Harvard Dataverse, doi:10.7910/DVN/VOQCHQ,
  version 20 (released 25 February 2026).
- **Licence.** CC0 1.0, read from the dataset page on 30 September 2026.
  Its Terms tab adds the Dataverse community norm that credit is given
  "via citation", using the citation shown on the dataset page.
- **Citation.** The new `LicenseTerms` entry (`medsl_president`, shippable)
  carries that citation: MIT Election Data and Science Lab, 2018, "County
  Presidential Election Returns 2000-2024",
  https://doi.org/10.7910/DVN/VOQCHQ, Harvard Dataverse, V20,
  UNF:6:xvsJJxrfXMIvzAuDYlfvVw== [fileUNF].
- **The download.** The dataset is behind a guestbook asking for a name,
  email, institution and position, so you downloaded it by hand.
  `adapters/medsl_president.py` pins that copy of
  `countypres_2000-2024.csv` (sha256 `9299583148f5…`, byte for byte the
  MD5 Dataverse publishes) with its codebook, and records the manifest
  entry as obtained by hand.
- **The check-only files.** Two sources are used as checks and never
  served. The lab's state-level returns (*U.S. President 1976–2024*,
  doi:10.7910/DVN/42MVDX, CC0 1.0, no guestbook; entry
  `medsl_president_state`) supply the state totals. The Census Bureau's
  2024 Alaska district-to-tract relationship file, with 2020 Census tract
  populations, decides Alaska.

## 2. Coverage

| 2024 | metros | with a figure | Not available |
|---|---|---|---|
| All metros | 387 | 380 | 7 |
| Ranked metros | 193 | 187 | 6 (3.1%, under the 5% stop) |

Not available, and why (2020 is the same seven):

- **Bridgeport, Hartford, New Haven, Norwich and Waterbury, CT** (all
  ranked). The returns report Connecticut by its eight former counties. The
  2023 delineation builds these metros from planning regions (09110–09190).
  The former counties don't nest in the planning regions, and no metro is a
  union of former counties.
- **Anchorage, AK** (ranked) **and Fairbanks, AK** (not ranked). Alaska
  reports by house district, not borough.
  - Anchorage: district 30 holds all of Denali Borough (1,619 people in
    2020) beside part of Matanuska-Susitna. Districts 9 and 29 reach into
    populated tracts of the Chugach and Copper River census areas.
  - Fairbanks: district 36 holds six whole tracts outside Fairbanks North
    Star Borough (12,151 people).
  - So neither metro is a union of whole districts.

## 3. Validation

- **Modes.** 2024 has 2,778 reporting units with a TOTAL row, 367 with no
  mode at all (eight states), and 9 South Dakota vote-centre counties with
  split modes only, which are summed. 2020 has 2,306 TOTAL and 849 summed.
  Every unit reconciles with its own reported total: 0 exceptions in either
  year. No candidate appears only in split modes, and no TOTAL VOTES CAST
  row disagrees.
- **Rows that are no vote for anyone.** TOTAL VOTES CAST, UNDERVOTES,
  OVERVOTES and SPOILED are dropped by name. Arizona's, Iowa's and DC's
  over- and undervotes carry party OTHER, and would otherwise have counted
  as votes for "everyone else".
- **The Alaska code collision.** DISTRICT 20's code reads as 02020,
  Anchorage Municipality's. A plain county join would have given
  Anchorage one district's votes; Alaska's rows never join as counties.
- **The remaining special cases.**
  - Kansas City, Missouri reports on its own: 124,288 votes in 2024. All
    four of its counties lie in its metro, so those votes join the metro.
  - Kalawao County, Hawaii has no returns. Hawaii counts its voters with
    Maui, in the same metro.
  - Four New Mexico Libertarian cells read NA and count as zero; those
    units still reconcile.
- **State totals: the stop condition.** Like with like: the Democratic
  count, the Republican count and the votes for a candidate, each file's
  non-vote rows dropped.
  - 2024: 45 of 51 are within 0.1%. The Democratic count is exact in 48,
    the Republican in 48, the votes for a candidate in 37.
  - Outside the tolerance (2024):

    | State | Democratic | Republican | Votes for a candidate |
    |---|---|---|---|
    | Maine | −1.22% | −0.26% | −0.79% |
    | Rhode Island | −0.49% | −0.05% | −0.25% |
    | Virginia | +0.07% | +0.05% | −0.46% |
    | Nebraska | exact | exact | −0.53% |
    | Arizona | exact | exact | +0.34% |
    | Delaware | exact | exact | −0.24% |

  - 2020, for the record: 39 of 51 within 0.1%.
- **Swing check** (the 5-point threshold was fixed before the first run).
  380 metros compared. 35 metros swing more than 5 points away from their
  state, and every one follows a known 2024 pattern rather than a data
  error:
  - the Texas, California and Arizona border metros (Eagle Pass −19.85
    points against Texas, Laredo, El Centro, El Paso, McAllen,
    Brownsville, Yuma) and Miami;
  - upstate New York against a state swing that New York City carried
    (Ithaca +11.45, Kingston, Rochester, Binghamton);
  - college towns (Champaign, Bloomington IL, San Luis Obispo).
- **The Pew guard** finds nothing in the new files.

## 4. Stopped here

The brief's stop condition, "a state's summed county totals disagree with
the dataset's own state totals by more than 0.1%", fired for Arizona,
Delaware, Maine, Nebraska, Rhode Island and Virginia. The other three
conditions pass:

- the licence is CC0;
- 3.1% of ranked metros are Not available;
- no score or rank has moved, since nothing was built.

Done and committed:

- the pinned source and the check-only files;
- the licence entries;
- the measure's rules and their 13 tests (86df38e);
- the validation record and the per-metro table
  (`political_lean_metro.csv`, both years).

Not started, per the brief's halt:

- ADR 0019 and the ADR 0012 amendment;
- the registry feature, the build and version bump, and the API block;
- the city card, the compare row, the What-we-measure entry and the stat
  page;
- the Sources and credits line;
- the gate check, and the Playwright and axe runs.

## 5. Your decision

1. **Accept the gaps and record them (recommended).** Show the county-based
   figure for all 380 metros that have one. ADR 0019 would name the six
   states and the size of each gap. The gaps come from how those states
   report: ballots counted only statewide can't be placed in any metro by
   anyone. At the site's whole numbers they move at most one point, in at
   most one of a metro's three numbers. With the gap votes spread like the
   counted ones, these ranked metros would show one number differently:
   - Omaha: 48 → 47 Democratic
   - Portland ME: 37 → 36 Republican
   - Providence: everyone else 3 → 2
   - Richmond: 43 → 42 Republican
   - Roanoke: 59 → 58 Republican
   - Tucson: everyone else 2 → 1
   - Virginia Beach: everyone else 1 → 2
2. **Leave the six states' metros out.** That's 28 metros, 13 of them
   ranked. With the six already missing, 19 of 193 ranked metros (9.8%)
   would show Not available. That's past the brief's 5% limit, so it
   would stop again.
3. **Hold the feature.**

On a yes to 1, the rest of the brief runs as written, from the ADRs through
the full battery.

## 6. Tests so far

pytest 142 (129 + 13 new aggregation tests), all passing. The other
suites were not run: nothing they cover has changed.

## 7. Deviations

One line each; `results/phase4d/deviations.md` is identical.

- The county file has no state rows, so the check's state totals come from the lab's companion state-level file (doi:10.7910/DVN/42MVDX, CC0 1.0), read as a check only; Nathan approved the download.
- The dataset is behind a guestbook, so Nathan downloaded it by hand and the adapter pins that copy (the pinned sha256 and Dataverse's MD5) instead of fetching it; its manifest entry says it was obtained by hand.
- The state totals are compared like with like (the Democratic count, the Republican count and the votes for a candidate, each file's non-vote rows dropped), a definition written after a first look at both files; on the state file's reported totals, which in some states count blank and spoiled ballots, 13 states would fall outside instead of 6.
- The citation is the dataset page's string with a full stop added, the house rule for citations.
- Alaska is decided from the Census Bureau's 2024 district-to-tract relationship file and 2020 Census tract populations (Nathan approved the download); the district-to-county file fetched beside it is on the manifest but unused.
- The 2020 Alaska metros are Not available without a check, since the 2020 returns use the districts drawn after 2010.
- Kalawao County is counted with Maui, and Kansas City's own returns join the Kansas City metro; both are asserted to lie in one metro.
- The state-gap reading (the gap spread like the counted votes, and all of it in one metro) was added after the first run, to size the finding; it decides nothing.
