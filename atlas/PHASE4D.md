# Phase 4d — political lean, shown as context and never scored

Every number here is read from a file under `results/phase4d/`, or from the
build's validation report, which it names; nothing was recomputed for the
report. The measure's rules were committed (86df38e) before it first ran.

**In plain words, for Nathan.** Each city now shows how its metro area voted
in the 2024 presidential election. There's a small card beside "Who lives
here", for example "47% Democratic · 52% Republican" for Pittsburgh. Under
the numbers are a split bar and the names of its three parts. Compare shows
both cities side by side. What we measure explains the figure, and a new
page lists every ranked city by name, which visitors can re-sort by either
party's share.

The figure is context only. Nothing is scored, filtered, weighted or asked,
and every ranking on the site is exactly as it was: all 518 test searches
return the same response, byte for byte, apart from the build's id.

The data is MIT's county election returns, free to use (CC0) with a
citation that now sits in Sources and credits. 380 of the 387 metros have
a figure, including 187 of the 193 ranked ones. The seven without one
are:

- Connecticut's five metros: the data reports Connecticut by its old
  counties, not the new planning regions the metros are built from;
- Anchorage and Fairbanks: Alaska reports by legislative district, and the
  districts spill past both metros' edges.

Those seven say "Not available". The phase stopped once on the brief's
state-totals check; you accepted the small gaps it found, and they're
recorded in ADR 0019. The copy for your approval is §6.

## 1. The source and its licence

- **Dataset.** MIT Election Data and Science Lab, *County Presidential
  Election Returns 2000–2024*, Harvard Dataverse, doi:10.7910/DVN/VOQCHQ,
  version 20 (25 February 2026).
- **Licence.** CC0 1.0, read from the dataset page on 30 September 2026.
  Its Terms tab asks for the data citation the page shows.
- **Citation.** It sits in Sources and credits only (licence entry
  `medsl_president`; ADR 0012 amended): MIT Election Data and Science Lab,
  2018, "County Presidential Election Returns 2000-2024",
  https://doi.org/10.7910/DVN/VOQCHQ, Harvard Dataverse, V20,
  UNF:6:xvsJJxrfXMIvzAuDYlfvVw== [fileUNF].
- **The download.** The dataset is behind a guestbook (name, email,
  institution, position), so you downloaded it by hand.
  `adapters/medsl_president.py` pins that file by its SHA-256 (it matches
  Dataverse's own checksum) and records in the fetch manifest how it was
  obtained.
- **Checks only, never shown.** The lab's state-level returns
  (doi:10.7910/DVN/42MVDX, CC0) supply the state totals. The Census
  Bureau's 2024 Alaska district-to-tract file decides Alaska.

## 2. Coverage

| 2024 | metros | with a figure | Not available |
|---|---|---|---|
| All metros | 387 | 380 | 7 |
| Ranked metros | 193 | 187 | 6 (3.1%, within the brief's 5%) |

- **Bridgeport, Hartford, New Haven, Norwich and Waterbury, CT** (all
  ranked). The returns report Connecticut's eight former counties. The
  delineation builds these metros from planning regions, which the former
  counties don't nest in.
- **Anchorage, AK** (ranked) **and Fairbanks, AK.** Alaska reports by house
  district.
  - Anchorage: district 30 holds all of Denali Borough (1,619 people)
    beside part of Matanuska-Susitna, and districts 9 and 29 reach into
    populated tracts outside the metro.
  - Fairbanks: district 36 holds six whole tracts outside it (12,151
    people).

The stat page leaves the six ranked metros off, with its usual note, and
their city cards and compare cells say "Not available".

## 3. Validation (`validation.json`)

- **No double counting.**
  - 2024: 2,778 reporting units use their TOTAL rows, 367 (eight states)
    carry no mode at all, and South Dakota's 9 vote-centre counties are
    summed.
  - 2020: 2,306 TOTAL and 849 summed.
  - Every unit reconciles with its own reported total, and no candidate
    sits only in split modes.
- **Rows that count no vote for anyone** never count, whatever their
  party. Arizona's, Iowa's and DC's over- and undervotes carry party
  OTHER.
- **Special cases.**
  - Alaska's DISTRICT 20 code collides with Anchorage's county code; a
    plain join would have given Anchorage one district's votes. Alaska's
    rows never join as counties.
  - Kansas City's own returns (124,288 votes) join its metro, where all
    four of its counties lie.
  - Kalawao County, Hawaii is counted with Maui County, in the same metro.
  - Four New Mexico cells read NA and count as zero; their units still
    reconcile.
- **Metros across state lines** add their votes across states and divide
  once. There are 43 such metros, 29 of them ranked, and all have a figure
  (`political_lean_metro.csv`).
- **State totals.** 45 of 51 states are within 0.1% in 2024: the
  Democratic count exact in 48, the Republican in 48. The six outside:

  | State | Democratic | Republican | Votes for a candidate |
  |---|---|---|---|
  | Maine | −1.22% | −0.26% | −0.79% |
  | Rhode Island | −0.49% | −0.05% | −0.25% |
  | Virginia | +0.07% | +0.05% | −0.46% |
  | Nebraska | exact | exact | −0.53% |
  | Arizona | exact | exact | +0.34% |
  | Delaware | exact | exact | −0.24% |

  - Maine and Rhode Island are short of ballots counted only statewide.
  - The other four differ in how write-ins are counted.
  - This fired the brief's stop condition. The phase halted (7b7c597)
    and you accepted the gaps (§8).
  - Spread like the counted votes, the gaps would move one shown number
    by one point in 16 of the 28 metros in those states (7 of them
    ranked), never more.
- **Swing check.** 380 metros were compared, using the 5-point rule fixed
  before the check ran. 35 differ from their state's 2020→2024 swing by
  more than 5 points. Every one is a known 2024 pattern, not a data error:
  - the Texas, California and Arizona border metros (Eagle Pass −19.85
    points against Texas) and Miami;
  - upstate New York against a swing New York City carried (Ithaca
    +11.45);
  - college towns.

## 4. Where the figure appears

- **City page.** A card beside "Who lives here". It shows the two main
  shares, the caption, a split bar (Democratic blue, grey for everyone
  else, Republican red) with each part named under it in text, and the
  stat-page link. The bar is spoken with all three shares, and its colours
  hold 6.35:1, 6.39:1 and 3.81:1 on the white card (`lean_contrast.json`).
  The card shows with the metro's other stat cards.
- **Compare.** One row, "Political lean", with both cities' shares. It has
  no difference.
- **What we measure.** In the context group, after "Who lives here", with
  the definition.
- **Stat page** (`/stats/political_lean`).
  - Cities are listed by name by default, with no position numbers and no
    distribution strip.
  - "Sort by" offers Name, Democratic share and Republican share, highest
    share first.
  - The unit line is said once, under the column names.
- **Not on the home rows or in the side panel.** No page's browser ever
  requests it. The city and compare pages read it on the server from `GET
  /v1/political_lean`. The ranking response neither carries nor accepts it.

## 5. The gate check and the tests

- **Rankings.** Every one of the 518 ADR 0011 test searches returns a
  /v1/rank response identical to 5b780e4f2444's but for the build id,
  with the same bytes. All 1,036 single-seeker rankings are identical
  (`served_numbers_check.json`).
- **Goldens.** The goldens' 18 vectors are identical; only the
  `fixture_of` line names the new build. The shared web cases differ only
  in the build id.
- **The build.** New build **2dbd9ebfa7ff**: only `features.parquet`
  changed, gaining three vote columns, with every old column identical.
  MODEL_VERSION stays **m4.1.0**, since `versions.py` asks for a bump only
  when a golden moves; `versions.py` records the build.
- **`build.validate`.** 11 of 11 hard gates pass on 2dbd9ebfa7ff. The ADR
  0011 stability gate reads **1.0** against the m4.0.0 reference (516
  searches compared, none touched, wobble 261.18 both). The report equals
  Phase 4c's but for the build, its stamps and the gate's run time.
- **Tests.**
  - pytest 148: 129 before, plus 13 aggregation tests and 6 for the
    engine and API, which cover never scored, absent from every request
    field, and "Not available".
  - vitest 103: 92 before, plus 11 covering colour contrast, the sort
    order, and the card and cell including "Not available".
  - Playwright 125: 116 before, plus 9. That includes 18 axe runs (15
    before, plus 3 new), all with zero serious or critical findings
    (`test_counts.json`).
  - The banned-vocabulary sweep stays clean in `build.validate` and in the
    e2e specs. The loader refuses evaluative words in the feature's
    strings, and an e2e sweep reads its card, row and page.
  - The Phase 4 privacy and network tests pass unchanged.

## 6. Copy for your approval

(`copy_changes.json`)

| Where | Text | Status |
|---|---|---|
| Display name (card, compare row, What we measure, stat page) | Political lean | the brief's |
| Definition (What we measure, stat page) | How the metro area voted in the 2024 presidential election. It describes everyone who voted there, not the people who match your search. | the brief's draft |
| Caption (card; the stat page's unit line) | 2024 presidential vote, whole metro area | the brief's |
| The shares (card, compare cells) | 47% Democratic · 52% Republican | draft form |
| The bar's key; the stat page's columns | Democratic · Everyone else · Republican | draft |
| No figure (card, compare cell) | Not available | the brief's |
| Stat page title and link | Cities by political lean · See all cities by political lean | existing templates |
| Stat page sort control | Sort by: Name / Democratic share / Republican share | draft |
| Stat page source line | Source: MIT Election Data and Science Lab, County Presidential Election Returns 2000–2024 | draft |
| Compare row | Political lean · (no difference) | as above |

## 7. Offered, not done

- About us's "Where does the data come from?" table doesn't list political
  lean. The brief names Sources and credits as the one place for the
  credit. A row such as "Political lean | MIT Election Data and Science Lab
  — shown, never scored" is yours to add or leave.
- A dated PDF of the dataset's Terms page for the counsel packet, as HUD's
  was saved.
- The Connecticut and Alaska metros would need town-level or precinct
  returns from another source: a new licence entry and an ADR amendment.

## 8. The halt and your call (30 September 2026)

The state-totals stop condition fired on Arizona, Delaware, Maine, Nebraska,
Rhode Island and Virginia. The phase halted before building anything; the
record is 7b7c597. Of the options offered, you chose to accept the gaps and
record them. The figures stand as the county returns give them, and ADR
0019 names each gap. The other three stop conditions passed:

- the licence is CC0;
- 3.1% of ranked metros are Not available;
- no score or rank moved.

## 9. Deviations

One line each; `results/phase4d/deviations.md` is identical.

- The county file has no state rows, so the check's state totals come from the lab's companion state-level file (doi:10.7910/DVN/42MVDX, CC0 1.0), read as a check only; Nathan approved the download.
- The dataset is behind a guestbook, so Nathan downloaded it by hand and the adapter pins that copy (the pinned sha256 and Dataverse's MD5) instead of fetching it; its manifest entry says it was obtained by hand.
- The state totals are compared like with like (the Democratic count, the Republican count and the votes for a candidate, each file's non-vote rows dropped), a definition written after a first look at both files; on the state file's reported totals, which in some states count blank and spoiled ballots, 13 states would fall outside instead of 6.
- The state-totals stop condition fired (six states); the phase halted, and Nathan accepted the gaps and chose to record them in ADR 0019, after which the brief ran on as written.
- The citation is the dataset page's string with a full stop added, the house rule for citations.
- Alaska is decided from the Census Bureau's 2024 district-to-tract relationship file and 2020 Census tract populations (Nathan approved the download); the district-to-county file fetched beside it is on the manifest but unused.
- The 2020 Alaska metros are Not available without a check, since the 2020 returns use the districts drawn after 2010.
- Kalawao County is counted with Maui, and Kansas City's own returns join the Kansas City metro; both are asserted to lie in one metro.
- The state-gap reading (the gap spread like the counted votes, and all of it in one metro) was added after the first run, to size the finding; it decides nothing.
- The figure reaches the city and compare pages through its own endpoint (GET /v1/political_lean), not the rank response: the home page never shows it, and every search's response stays byte for byte as it was, the build id apart.
- MODEL_VERSION stays m4.1.0 though the build id changes (2dbd9ebfa7ff): no golden moves (goldens.json differs only in fixture_of), and versions.py asks for a bump only when one does; versions.py records the build.
- The compare row has no difference, against ADR 0007's every-row rule: a difference would set one party's share against the other city's; its cell is empty and carries no data-diff-for.
- The stat page has no distribution strip and no position numbers, and lists by name: either would line the cities up by one party.
- The stat page keeps the source line every stat page carries (the registry loader requires it), naming the lab; the citation itself is only in Sources and credits.
- The city card shows with the metro's other stat cards, which the city page shows for the 193 ranked-set metros only; the other 194 pages show no stat cards at all, an existing gap flagged for a separate task.
- The shares' text has a no-break space before its middle dot, so a narrow card breaks the line after the dot.
- Registry strings beyond the brief's words: the three segment names, the text and spoken-label templates, the sort control and the stat page's source name (drafts, §6), since no user-facing string lives in code.
- "Not available" is tested in the engine, the API and a vitest render, not in Playwright: no metro of the pinned 12-metro fixture lacks a figure, and adding one would change the golden fixture.
- The first full Playwright run failed one test: its sweep read the stat page's whole text and matched "left" in the note every stat page shares ("left off this list", approved copy); the sweep now reads political lean's own words.
- The web pages skip the figure when the API answers 404 (an API from before the feature), so a dev stack still serving 5b780e4f2444 keeps working.
- vitest compiles JSX with React's automatic runtime (vitest.config.ts) so the unit tests can render the card; tsconfig keeps JSX as it is for Next.
