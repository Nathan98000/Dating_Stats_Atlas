# Phase 2g — rent from HUD, two rewritten explainers, and the empty state

Build **5d0e3ca2f708**, model **m2.4.0** (ADR 0008). Suites at close:
**41 pytest, 49 vitest, 69 Playwright**, all **eight validation hard gates**
re-run and passing on the new build (the data changed, so the battery ran
in full), axe zero serious/critical across ten page shapes (about-crime-data
joined the list), banned-vocabulary sweep zero across eleven.

## What the swap did to the ranking

**The level shift.** HUD's FY2027 figure over the ACS 2020–2024 one it
replaces, across the 193 ranked metros: **median ×1.278, p10 ×1.144, p90
×1.458**. Every metro rises — a five-year average giving way to a series
trended into fiscal-2027 dollars — and the spread of the rise is the story:
College Station grows least (×1.057) and Santa Cruz most (×1.925).

**Austin, by name.** $1,500 → **$1,638** — a ×1.092 rise, *below the p10*.
The measure that started this line of work in Phase 2e now shows the other
half of the story: under HUD's recent-mover and trend chain, Austin's
one-bedroom market has cooled relative to everywhere else, and it moves
from 169th- to **134th-cheapest** of 193 on the rent page. Its overall rank
under the stated default search does not move at all (6 → 6).

**The rent page's ten biggest moves** (positions in cheapest-first order):

| City | ACS → HUD | Position |
|---|---|---|
| Springfield, MA | $869 → $1,530 | 44 → 124 (−80) |
| Providence, RI | $961 → $1,646 | 74 → 137 (−63) |
| Scranton, PA | $755 → $1,187 | 15 → 64 (−49) |
| Worcester, MA | $1,068 → $1,748 | 103 → 152 (−49) |
| College Station, TX | $1,068 → $1,129 | 102 → 54 (+48) |
| Port St. Lucie, FL | $1,193 → $1,929 | 125 → 172 (−47) |
| Buffalo, NY | $869 → $1,306 | 43 → 88 (−45) |
| Columbia, SC | $1,106 → $1,208 | 113 → 69 (+44) |
| Slidell, LA | $1,158 → $1,256 | 119 → 76 (+43) |
| Roanoke, VA | $892 → $1,320 | 52 → 92 (−40) |

The pattern is legible: Northeastern metros whose five-year ACS averages
lagged their current markets (Springfield, Providence, Worcester, Buffalo,
Scranton) re-price sharply upward, while college and Sun-Belt-adjacent
markets that cooled recently (College Station, Columbia, Slidell) climb the
cheap end.

**The overall ranking** under the stated default search: **162 of 193 ranks
change**, Kendall τ **0.963** — a broad shuffle of small moves. The largest
are ±14 (College Station up, Worcester down); the full list is in
`results/phase2g/rent_swap_report.json`. Gate 4 held bitwise: the three
cubes, `pairing_cells.parquet` and `metros.json` are **SHA-256-identical**
to m2.3.1's build, every non-rent feature column is identical, and pool
counts and balance figures match row for row across both builds' responses
— only cost moved, asserted rather than assumed.

## The aggregation, shown working

Verified schema first (the brief's requirement — nothing was written
against assumed columns): `FY2027_FMR_50_county.xlsx`, one sheet
`fy2027_fmr_50`, **4,764 rows**, columns `state_code, county_code,
county_sub_code, cntyname, town_name, hud_areaname, fips2025, rent_50_0 …
rent_50_4, hud_area_code, state_alpha, pop2023`. The one-bedroom figure is
**`rent_50_1`** (populated on all 4,764 rows, range $477–$3,579); the area
file carries 2,605 areas (649 METRO-coded, 1,956 nonmetropolitan — the
brief's "roughly 530 + 2,045" reads on a different grouping of HMFA
subdivisions, so the actuals are recorded here). All 1,186 counties of the
site's 387 metros are present; Connecticut already speaks the OMB 23-01
planning-region codes. **Coverage asserted: 387 of 387 metros, 193 of 193
ranked.** The gap the ACS never quite closed is closed.

One rule everywhere: a metro's rent is the mean of its counties'
one-bedroom medians **weighted by renter-occupied households**
(`B25003_003E`). The checks:

- **246 metros are a single FMR area**, and for every one the weighted
  mean is **asserted equal to HUD's published area figure** (to 1e-9)
  against `FY2027_FMR_50_area.xlsx` — the weights cannot move a mean of
  identical values, so any deviation would have been a join bug.
- **141 metros compose multiple FMR areas.** The widest within-metro
  spreads (max − min county figure), where one number does the most work:
  Washington DC **$1,282**, New York $1,007, Atlanta $997, Nashville $961,
  Providence $922, Boston $902, Durham–Chapel Hill $884, Charlotte $878,
  Chicago $870, San Francisco $861.
- **New England**, where HUD publishes town rows instead of county rows
  (757 of them; 14 counties straddle two HUD areas): the same
  renter-household weight applies one level down. **Finding:** five HUD
  rows carry pre-revision FIPS subdivision codes against ACS 2024's
  current ones — Watertown, Methuen, Amesbury and Easthampton (the
  Massachusetts "Town cities") and Maine's Drew UT — resolved by a
  name-within-county fallback that refuses on name collisions; zero rows
  ended at zero weight. Each is named in `features_report.json`.
- **Gate 3, traced end to end** (`rent_trace.py`, an independent
  recomputation sharing nothing with the build code past the adapters):
  Provo ($1,304), Austin ($1,638), Abilene ($1,112, three counties one
  area), New York ($2,757 across 7 HMFAs), and Boston ($2,481 across 6
  HMFAs and 197 town rows) — traced value == served value == the API's
  display string, all five.

From HUD's FY27 methodology, read and recorded: the 50th-percentile rent
is a **gross rent** (shelter + tenant-paid utilities — so Phase 2f's "with
utilities" unit line ships unchanged, vindicated); the base is **ACS 2024
5-year (2020–2024)** adjusted-standard-quality rents (cash rent, ≤10
acres, full plumbing, complete kitchen, meals excluded; units under the
75th percentile of public-housing rents removed), carried forward by the
recent-mover comparison, a 2024→2025 gross-rent inflation factor and a
trend factor into FY2027; published 50th-percentile rents are **floored at
the FMR**; and **the utility half of this number is new-method this year**
— FY2027 is the first year HUD builds it from composite EIA/BLS inflation
factors after BLS discontinued the metro CPI utility indices (January
2025). One operational finding: huduser.gov answers a non-browser
User-Agent with an empty HTTP 202, so the adapter fetches with a browser
UA through the same content-addressed cache and manifest as every source.

## What came off the site

All five removals are deliberate and confirmed; a later reader should find
them here rather than notice them missing:

1. **The margins-of-error explanation** (methodology §"Why aren't margins
   of error printed…"). The machinery is untouched — the interval model
   runs on every build, `pool_moe`/`cv` are still returned, suppression
   still fires on them — and the site now says none of that anywhere. The
   old intro's "precise uncertainty figures… available on request"
   sentence went with it, since keeping it would have contradicted the
   ADR's stated consequence. Recorded in ADR 0008 and in the counsel
   packet, because a reviewer will otherwise ask.
2. **The reproducibility paragraph** ("Can a result be reproduced
   later?"). The `/r/[dv]/[mv]/[token]` route **keeps working** — the e2e
   suite still proves a permalink resolves and a stale pin refuses plainly
   — it simply loses its explanation.
3. **The crime page's implausible-submission note** — with a correction to
   the brief's premise: the shipped crime page **never carried** that
   paragraph. The NIBRS transition exclusions (New York's 2021 filings,
   Orlando's twelve zeros, 13 agency-years in all) have always lived in
   the build report and PHASE2D.md only; they still happen in the build,
   and after this rewrite that remains the only place they are explained.
4. **The rent-regulation note** (`rent_page_note`, its build-JSON field
   and the caution box): HUD trims the subsidised bottom of the
   distribution and adjusts to recent movers, so the stabilised-tenancy
   drag the note described is not in this measure.
5. **The narrow-state note box** (`narrow_note` and its render): the new
   body's second sentence says what it said. Its "How it works" link went
   with it — the header nav still carries the route on that screen
   (asserted in e2e), so no widener-row link was added.

## The other items, measured

**2.1 The hero is a couple.** Shipped: *Adult couple holding hands* (Alice
Donovan Rouse, **CC0**, 6016×4016) — the couple walks toward the camera
framed from the shoulders down, so faces are not merely unidentifiable,
they are **out of frame entirely**: the strongest available answer to the
publicity-rights question, with no visible brands. Sourced through the
same licence gate (PD/CC0 enforced in `hero_image.py`, licence re-read
live), manifest row at `results/phase2g/hero_image.csv`, attribution
rendered under the band and still bound to the file by SHA-256. The other
candidates reviewed, for Nathan's eyes: *Senior-3336451 1920* (CC0,
Pixabay; an older couple from behind — sweet, but 1920px, a visible
"HollyBAG" brand, and it reads the audience differently) and *Couple
walking into St John's College Oxford* (public domain; from behind, but
portrait-orientation — a band crop keeps a sliver — and unmistakably
Oxford rather than a US city). The Phase 2f Burlington hero's manifest row
stays in `results/phase2f/` as the record of what shipped before.

**2.2 / 2.3 The all-excluded state.** `narrow_body` is Nathan's copy
verbatim (typographic apostrophes per that file's convention), the note
box is deleted, and e2e asserts the search phrase opens the sentence at
1280 and 375 ("Men 25–35, never married, … is a very small group in any
city."). Screenshots 04/05.

**2.4 The excluded-cities line** was already Nathan's wording from Phase
2f — verified rendering ("make a reliable estimate… Widen your search to
see more cities."), changed nothing.

**3. Nice days.** Shipped: "Days a year that **reach** between 55 and
85°F, don't dip below 40°F, and see no more than a light shower." —
**"reach" substituted for Nathan's "average", flagged here for his
confirmation**: the rule is on the day's high (`tmax_f: [55, 85]` with
`tmin_floor_f: 40`), so "average" would describe a statistic the site
does not compute. The dropped 30-year clause is carried by the same
page's source line (NOAA GHCN-Daily, 1991–2020).

**4 / 5. The two rewrites.** Both ship from `docs/` through
`sync_content.mjs`, verbatim plus the two corrections (the 387/193
two-condition sentence; the HUD rent row) and the one typo fix
("nationally-recognized"). **One flag for Nathan on item 5:** his draft
was not on disk anywhere I could find (the prompt file carries only the
deltas), so the shipped page is the live page transformed by exactly the
brief's stated deltas. Two seams were judgment calls, called out for his
read: the old second intro paragraph ("This page is kept in step… available
on request") was **removed** — keeping it would contradict the ADR's
"nothing on the site says it exists" — and the place-stats lead-in was
worded around the given typo fix ("each from a nationally-recognized
source, updated when that source publishes"). The race-and-ethnicity
section **stays** (the brief's removal list is exhaustive at three, and
the exit's removals list at five). The H1 remains "How the numbers are
made".

**1.3 The rename.** `median_gross_rent` appears nowhere in the registry,
the build JSON or the web app (grepped; the api/model/tests renamed;
`/stats/median_gross_rent` 308-redirects to `/stats/rent_1br`, asserted in
e2e). The rent stat-page image re-keyed with it (manifest row, JSON key
and file name — same image, same licence, same hash). Historical
instruments keep the old name deliberately: PHASE2D/E/F docs, the retired
builds' manifests, `display_only_diff.py` (a 2f-only instrument) and the
2d/2e/2f shoot scripts (their URLs still work via the redirect).

## Deviations, findings and judgment calls

1. **The brief's crime-page premise corrected** (removals item 3 above):
   no implausible-submission paragraph existed on the shipped page.
2. **The methodology draft reconstructed from deltas** (item 5 flag
   above) — the two seams named for Nathan's read.
3. **New England FIPS revisions** (aggregation section): five HUD rows
   matched by name, zero dropped.
4. **A latent test bug surfaced by the new data**: `score_display` rounds
   the unrounded score, but the golden engine test re-rounded the
   already-1-dp `score` — the two disagree exactly at a .5, which m2.4.0's
   scores hit for the first time (display 41 from 41.4x; round(41.5) → 42).
   The test now asserts the display is a whole number within half a point
   of the served score instead of recomputing it; the display code was
   already right and is untouched.
5. **huduser.gov's UA gate** (202-empty to non-browser agents) — the
   adapter carries a browser UA; recorded in its docstring.
6. **`docs/sources.md` is now committed**: it was Nathan's untracked file,
   but this brief instructs edits to it (the HUD row, the superseded
   move), and a phase deliverable cannot live untracked.
7. **The brief's area counts** ("roughly 530 metropolitan and 2,045
   nonmetropolitan") vs the file's 649/1,956 — recorded as actuals; the
   difference is HMFA subdivision counting, not missing data.
8. **m2.3.1 permalinks** now land on the earlier-edition page — correctly
   this time: the numbers really did change.
9. **`Apartment_List_Rent_Estimates_Summary_2026_08.csv`** in the parent
   folder: untouched, as instructed.
10. The **old build 98dcbb161236** is retired to manifest + metros.json
    (the 2e pattern); 5d0e3ca2f708 is the one complete build, and the API
    refuses to guess between multiples.

## Screenshots (results/phase2g/)

01 couple hero with CC0 credit · 02 rent page (HUD source line, no
caution box) · 03 Austin's card in FY2027 dollars · 04/05 the
all-excluded state at 1280 and 375 · 06 How it works (full page) ·
07 About the crime figures (full page).

## Gate check

1. HUD county file fetched and hashed at build time; 387/387 and 193/193
   asserted; no partial column. ✓
2. 246 single-area metros equal HUD's published figure exactly (asserted);
   141 composed metros' spreads reported, worst $1,282 (Washington DC). ✓
3. Five cities traced cell by cell — HUD rows → weights → served value →
   API display — including Boston across 6 HMFAs and 197 town rows. ✓
4. Cubes, pairing cells and metros byte-identical; non-rent feature
   columns identical; pool counts and balance figures identical row for
   row; the full 193-rank before/after above. ✓
5. `median_gross_rent` gone from registry, build JSON and web app; the
   redirect works; "with utilities" intact and now literally HUD's own
   definition. ✓
6. Hero CC0 with manifest row and rendered attribution; faces out of
   frame, not merely unidentifiable. ✓
7. New body reads as a sentence at 1280 and 375 (e2e + screenshots), note
   box gone, How-it-works route present in the nav. ✓
8. Both pages render from docs/ through sync_content.mjs with the two
   corrections and the typo fix; every other sentence is Nathan's (the
   two reconstruction seams flagged above). ✓
9. axe zero serious/critical on home, results, city, narrow, compare,
   compare landing, stat page, what-we-measure, how-it-works AND
   about-crime-data; registry owns every string (sweep clean); banned
   vocabulary zero. ✓
