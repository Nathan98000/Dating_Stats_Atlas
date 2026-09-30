# Phase 4 — Pew out of the repository, the licences in the build, the intermarriage check from Census PUMS; m3.6.0 (US weather stations only) and m4.0.0 (Compatibility, race off by default, the "about you" details in the browser) ship

Every number here is read from a file under `results/phase4/` (or a
committed record it names); nothing was recomputed for the report. Every
decision recorded here is **Nathan's decision**.

**In plain words, for Nathan.** Pew's table is out of the repository and
out of every old version of it: the history was rewritten, and a scan of
every stored file finds none of Pew's city figures (it was run after the
rewrite and again today). Pushing the rewritten history and asking GitHub
to forget the old one are yours to do (§1). Every data source now carries
its exact credit line inside the build, and the build refuses to ship a
figure whose source is not cleared; one weather station sat across the
border (Detroit's, in Windsor), and Detroit now reads its airport (m3.6.0).
The check on the matching model now compares against the Census's own
newlyweds instead of Pew's. Then the main change, m4.0.0: the figure is
called **Compatibility**, and by default it uses no race at all — it is
refitted on age and education alone. Race counts only if a visitor
switches it on, and never on a same-sex search. A visitor's own sex,
education and race never leave their browser: the server works out every
possible answer at once — 50 versions of each search — and the browser
picks the one that fits, like a menu printed with every combination
already priced. That costs 2.3 times the data per search (the limit was 3)
and keeps every search well inside a tenth of a second. The default
ranking changes a lot, since it no longer uses race; anyone who switches
race on sees exactly what the site showed before. The stability check
reads 1.31 against the old yardstick — recorded, as you decided, not
blocking — and now uses the new site as its yardstick. The nav, About us
(with every credit in one place) and a privacy page are in; the privacy
text and every new or changed sentence wait for your approval (§6).

Commits: Stage 0 `9574d7c`; Stage 1 `be3bc8d`, `c768bc2`; Stage 2
`39971a8`; Stage 3 `529b62b`; Stage 3b `de35236` (m3.6.0); Stage 4
`c53a3c1`; Stage 5 `e8835ea` (ADR 0017), `17f2713` (ADR 0018),
`7bcc147` (the race-free fits), `f4dca83` (m4.0.0). Nothing is deployed,
pushed or sent.

## 1. Pew out

**The rewrite** (`pew_history_rewrite.json`, commit map `commit_map.txt`).
`git filter-repo` rewrote the history of `main` (75 commits; 20 of them
unchanged in content): the table itself is gone (its one version); Pew's
columns are stripped from the 26 `pew_lomo_*.csv` records of Phases 3 to
3c; the Jackson, Mississippi value is removed from two JSON records
(`results/phase3/kernel_report.json`, `results/phase3b/pew_rerun_decay_h5.json`);
and the per-metro figures quoted in `PHASE3.md`, `PHASE3B.md` and ADR
0009 read `[redacted]` (17 redactions) — 31 paths in all, 1,215 blobs
checked, no problem found. `origin` was removed by the tool and stays removed. The 33
commit hashes cited in 19 tracked files were updated to the new ones
(`cited_hashes_updated.json`).

**The scan** (`pew_history_scan.json`; again at this report,
`pew_history_scan_at_report.json`). Every blob reachable from every ref,
and every blob left in the object store, is read for Pew's table: its
header line, a Pew column or key, or ten or more of Pew's (metro, value)
pairs beating 200 seeded shuffles of Pew's values across its metros. After
the rewrite: 1,196 reachable blobs, clean. Today, with Stages 2–5
committed: **1,407 reachable blobs and 1 unreachable, 0 violations** (87
files sit below the limit — counts of small numbers that match by
coincidence, as the shuffle shows). A test holds every tracked file to the
same rules (`pipeline/tests/test_pew_reference.py`).

**Where Pew is now.** Only in `atlas/data/private/pew/` (gitignored:
the table, every historical version of each affected file, and the
rewrite's log) and in the pre-rewrite backup,
`~/Downloads/Projects/Dating_Stats_Atlas_backup_2026-09-28_pre_phase4_rewrite.git`
(private; it holds the old history).

**Yours to do** — nothing here was pushed:

```bash
git remote add origin https://github.com/Nathan98000/Dating_Stats_Atlas.git
```

```bash
git push --force --all origin
```

```bash
git push --force --tags origin
```

Then ask GitHub Support to purge cached views of the old commits (the
first rewritten commit was `365f2be`, now `464e67b`; every commit from it
on has a new hash), and check the repository's forks: a fork keeps the old
history and needs its owner's action or GitHub's. Keep the backup offline,
or delete it once the push is confirmed.

## 2. Licences

**The registry** (ADR 0012; `pipeline/adapters/base.py`). Fourteen sources
are typed as `LicenseTerms`: thirteen shippable — the Census Bureau's ACS,
2020 Census DHC, geography files and County Business Patterns, OMB's
delineation, BLS, BEA, EPA, NOAA's Normals and GHCN-Daily, IPEDS, HUD's
50th-percentile rents and the FBI's Crime Data Explorer — each with its
exact citation strings (one per product and vintage), the Census Bureau
Data API notice where the adapter calls the API, and its conditions (no
agency logo or seal, nothing implying endorsement; a figure the site
computes is "an estimate by Dating Stats Atlas", never "Census data";
GHCN US stations only; crime never scored and its caveat kept); and Pew
(not shippable). `cube.build` holds every served feature, and the
geography every figure passes through, to "shippable and cited", and the
manifest carries the citations, notice and conditions; About us renders
them (§5).

**The station audit and m3.6.0** (`station_audit_before_3b.json`,
`station_audit.json`, `rank_shift_m3_5_0_to_m3_6_0.json`,
`validation_report_m3_6_0.json`). Of 387 metros, 386 read a US station
and one a Canadian one: Detroit, on Windsor, Ontario (CA006139520,
14.9 km). The GHCN adapter now keeps US stations only; Detroit is
rematched by the same rule to Detroit Metro Airport (USW00094847,
25.3 km), and its nice days a year move from 115.6 to 120.7. No other
metro's station or value changes. m3.6.0 shipped as build 6172181a114f:
ten of ten hard gates; the stability gate against m3.5.0 0.999925 (nothing
touched); on the default search ten cities move one place (Detroit 25 →
24), the top ten unchanged; latency p95 34.9 ms.

**The photo audit** (`photo_review.json`, `logo_audit.json`). All 365
city photographs, 6 stat-page photographs and the hero were read on
labelled contact sheets and every candidate again at full size. Sixteen
are removed — an identifiable person as the subject, a recent US
sculpture or mural as a subject, or a government emblem prominent (ADR
0012) — six of them borderline calls marked for your confirmation (C043
Boulder, C061 Charleston WV, C069 Clarksville, C285 Salinas, C343 Waco,
S06 the "places to go out" stat photo):

- C026 (city, `barnstable-town-massachusetts`, sculpture): the Mercy Otis Warren statue (dedicated 2001) stands large in the left foreground
- C033 (city, `bend-oregon`, sculpture): a modern cast sculpture of a seated man dominates the right foreground
- C053 (city, `canton-ohio`, sculpture): the Hall of Fame's sculpted relief of football players is the photograph's centrepiece
- C116 (city, `fort-collins-colorado`, person): two cyclists, faces visible, are the photograph's subject
- C136 (city, `gulfport-mississippi`, sculpture): the Fighting Seabee statue fills the frame: a recent sculpture of a military emblem at a Navy gate
- C146 (city, `hilton-head-island-south-carolina`, emblem): the America 250 emblem of the U.S. Semiquincentennial Commission is painted large on the lighthouse, the photograph's subject
- C154 (city, `huntsville-alabama`, sculpture): a contemporary sculpture stands at the centre of the museum steps, with banners reproducing artworks behind it
- C185 (city, `lakeland-florida`, emblem): the City of Lakeland's logo sign is prominent and legible in the foreground
- C309 (city, `spartanburg-south-carolina`, mural): the photograph is the "Love Where You Live" wall mural
- C318 (city, `st-louis-missouri`, sculpture): The Runner (William Zorach, 1965) stands at the centre of the foreground
- C043 (city, `boulder-colorado`, person, borderline): a street performer with two young women is the focal point; faces small but visible
- C061 (city, `charleston-west-virginia`, sculpture, borderline): the Lincoln bronze (1974) stands on the photograph's central axis before the Capitol
- C069 (city, `clarksville-tennessee`, mural, borderline): a painted wall mural fills about a tenth of the frame beside the street scene
- C285 (city, `salinas-california`, sculpture, borderline): a carved column with figure reliefs dominates the foreground (the courthouse's 1930s art programme, possibly still in copyright)
- C343 (city, `waco-texas`, sculpture, borderline): one of the collage's ten panels is entirely a bronze horseman statue that looks modern
- S06 (stat, `venues_per_100k`, person, borderline): a man and a child, faces clear, stand large in the right foreground of the square

Twenty are kept with a note. One finding is left for you: **Savannah,
Georgia ships a photograph of Tarangire National Park, Tanzania** (the
pipeline resolved the article "Savanna"), a wrong image rather than a
licence problem. A stray file with no manifest row went to the Trash. The
logo audit finds no agency logo, emblem or seal in `web/public` or on any
of 29 page shapes.

**Photographs under a Creative Commons licence before 4.0**
(`photo_credits.json`, `cc_before_4_0`): 141 of the 356 photographs the
site shows — listed for your confirmation, the 1.0 and 2.5 ones with the
2.0 and 3.0 ones since they raise the same question:

- **CC BY 2.0** (38): `ames-iowa`, `brunswick-georgia`, `cape-coral-florida`, `chicago-illinois`, `des-moines-iowa`, `dubuque-iowa`, `flagstaff-arizona`, `hammond-louisiana`, `hanford-california`, `harrisburg-pennsylvania`, `helena-montana`, `houston-texas`, `las-vegas-nevada`, `longview-texas`, `louisville-kentucky`, `madison-wisconsin`, `muskegon-michigan`, `new-orleans-louisiana`, `omaha-nebraska`, `portland-maine`, `redding-california`, `reno-nevada`, `rochester-minnesota`, `rochester-new-york`, `rocky-mount-north-carolina`, `salisbury-maryland`, `san-francisco-california`, `san-jose-california`, `san-luis-obispo-california`, `santa-cruz-california`, `santa-fe-new-mexico`, `scranton-pennsylvania`, `slidell-louisiana`, `springfield-ohio`, `waterloo-iowa`, `wenatchee-washington`, `wilmington-north-carolina`, `yuba-city-california`
- **CC BY 2.5** (1): `boston-massachusetts`
- **CC BY 3.0** (15): `bakersfield-california`, `deltona-florida`, `eugene-oregon`, `jackson-michigan`, `knoxville-tennessee`, `la-crosse-wisconsin`, `lansing-michigan`, `mankato-minnesota`, `miami-florida`, `modesto-california`, `naples-florida`, `santa-rosa-california`, `wausau-wisconsin`, `wildwood-florida`, `stat page: resident_walkability_index`
- **CC BY 3.0 us** (1): `corvallis-oregon`
- **CC BY-SA 1.0** (1): `elmira-new-york`
- **CC BY-SA 2.0** (16): `duluth-minnesota`, `fargo-north-dakota`, `gadsden-alabama`, `grants-pass-oregon`, `idaho-falls-idaho`, `jackson-mississippi`, `kahului-hawaii`, `kennewick-washington`, `kenosha-wisconsin`, `los-angeles-california`, `macon-georgia`, `morgantown-west-virginia`, `sioux-city-iowa`, `springfield-illinois`, `st-george-utah`, `york-pennsylvania`
- **CC BY-SA 2.5** (4): `dover-delaware`, `oshkosh-wisconsin`, `st-joseph-missouri`, `valdosta-georgia`
- **CC BY-SA 3.0** (65): `albany-georgia`, `alexandria-louisiana`, `amarillo-texas`, `anniston-alabama`, `auburn-alabama`, `bloomington-indiana`, `bowling-green-kentucky`, `bozeman-montana`, `brownsville-texas`, `cedar-rapids-iowa`, `charleston-south-carolina`, `chico-california`, `college-station-texas`, `columbia-south-carolina`, `davenport-iowa`, `eagle-pass-texas`, `elkhart-indiana`, `fayetteville-arkansas`, `florence-alabama`, `fond-du-lac-wisconsin`, `gettysburg-pennsylvania`, `grand-junction-colorado`, `great-falls-montana`, `greeley-colorado`, `harrisonburg-virginia`, `homosassa-springs-florida`, `hot-springs-arkansas`, `houma-louisiana`, `jefferson-city-missouri`, `jonesboro-arkansas`, `joplin-missouri`, `kansas-city-missouri`, `killeen-texas`, `kiryas-joel-new-york`, `lancaster-pennsylvania`, `laredo-texas`, `las-cruces-new-mexico`, `lawton-oklahoma`, `manhattan-kansas`, `mansfield-ohio`, `merced-california`, `michigan-city-indiana`, `midland-michigan`, `myrtle-beach-south-carolina`, `oklahoma-city-oklahoma`, `oxnard-california`, `phoenix-arizona`, `pinehurst-north-carolina`, `provo-utah`, `punta-gorda-florida`, `roanoke-virginia`, `rockford-illinois`, `salem-oregon`, `san-diego-california`, `seattle-washington`, `sebastian-florida`, `sherman-texas`, `shreveport-louisiana`, `toledo-ohio`, `vallejo-california`, `victoria-texas`, `visalia-california`, `walla-walla-washington`, `washington-district-of-columbia`, `yuma-arizona`

## 3. The intermarriage check from Census PUMS (ADR 0016)

(`intermarriage_pums.json`, `intermarriage_check.json`,
`intermarriage_pew_agreement.json`.) For each metro, the share of people
married in the past 12 months whose spouse is of a different race or
ethnicity, in Pew's category scheme, from the ACS 2020–2024 PUMS: the
newlyweds' record keys came from the Census PUMS API (MARHM = 1; 199,869
records, 180,551 in the build's areas, every checked field matching the
extract), joined to the extract, weighted as every pool figure, with the
80-replicate margins. 80.0% of newlyweds have a spouse PUMS links (3.9% of
them same-sex). The rate over the build's metros is 23.8% (± 0.4); 124
metros have at least 200 newlyweds in sample.

On the served form's leave-one-metro-out predictions, corrected by one
national ratio: median absolute error **1.92 points** (shrunk dials), 1.91
raw dials, 3.75 national only, 35.66 random pairing; the shrunk kernel
beats national-only in 95 of 124 metros (p < 0.001) and ties raw dials
(69–55, p = 0.24). What the check loses is on the record: it comes from
the same survey as the fit, and the newlyweds are 8.1% of the fitting
weight (6.1–10.2% across metros), so the dial predictions are only partly
out of sample. Against Pew's table, read once from the private copy:
correlation 0.722, median absolute difference 6.65 points over the 124
metros both cover (0.729 on the 107 that also meet the floor). Pew then
plays no part in any check.

## 4. Compatibility (m4.0.0, ADR 0018)

**The race-free form's held-out cost** (`race_free_heldout.json`; the
store under `kernel/`). The race-off default is D0 — the cohort age term
and the education matrix, refitted with no race component and no
interaction, with its own per-metro dials (age τ 0.064, education τ
0.088). On the usual held-out measure (leave one metro out, split-half,
shrunk dials), per 1,000 weighted couple-sides, with ADR 0014's margin of
0.25:

| D0 against | shrunk | national only | metros where D0 is better | reading |
| --- | --- | --- | --- | --- |
| C1 (what leaving race out costs) | −407.1 | −402.3 | 0 of 387 | C1 beats D0 |
| C1 with its race terms zeroed (why it is refitted) | +2.2 | +3.6 | 266 of 387 | D0 beats it |

The intermarriage check reads D0 at a median error of 34.9 points (C1
1.9; random pairing 35.7): a form without race does not predict who
marries across groups, and is not asked to. The same-sex form without race
(`kernel/samesex_fit.json`) passes the same-sex face checks, sits 151.4
per 1,000 same-sex couple-sides below the composition m3.5.0 served
(race borrowed, the interaction riding), and ties the joint same-sex fit
with its race term dropped (−0.25, within the margin; the refit ships).
Race on is C1 exactly as m3.5.0 serves it: its arrays are copied byte for
byte from the artifact m3.5.0 and m3.6.0 both serve.

**The variant design.** `/v1/rank` takes the own age and an explicit
sought sex; `self.sex`, `self.education` and `self.race_ethnicity` are a
422. The response carries 50 variants — the opposite-sex own sex's 45
(education not given or one of four, times race off or one of eight) and
the same-sex own sex's 5 (race never used) — with everything no variant
changes sent once: the rows in the default variant's order, and per
variant, field by field in its own rank order, the rank, the score and
its display, the figure, its display and band and standing, the V2
normalised value, its contribution and the explanation (movers and
summary line, from a shared table), plus the balance for both own sexes.
The browser selects and copies; it computes no ranking number
(`web/src/lib/variants.ts`, tested against the Python model's own
selections). Every variant equals the single-seeker ranking exactly: all
90 combinations of two searches through HTTP in the tests, and a spread of
every persona's in `build.validate`'s new hard gate (1,620 selections,
185,850 rows, 108 exact comparisons, no problem).

| | before (m3.6.0) | after (m4.0.0) | budget |
| --- | --- | --- | --- |
| default search, gzipped response | 100,050 bytes | 229,408 bytes (2.29×) | 300,150 (3×) |
| same-sex reference search, gzipped | 77,064 bytes | 161,428 bytes (2.09×) | — |
| latency p95, 400-request mix | 34.9 ms | 54.3 ms (load 1.92) | 100 ms |
| the default search alone, p95 | — | 61.1 ms (load 1.57) | — |

(`payload_before.json`, `payload_after.json`, `latency_m3_6_0.json`,
`latency_m4_0_0.json`, `latency_m4_0_0_heaviest.json`.) The raw response
grows from 1.03 MB to 1.53 MB.

**The rank shift** (`rank_shift_m3_5_0_to_m4_0_0.json`; from m3.6.0
beside it, the same but for Detroit's weather):

- **The default search** (a woman of 30 seeking men 28–40, race off): 185
  of 193 cities change place, Kendall's τ 0.81, median move 9 places,
  90th percentile 30, largest 83; the compatibility figure moves by a
  median 1.9 points (largest 17.4). Top ten before: New York, Boston,
  Philadelphia, Chicago, San Francisco, Los Angeles, New Orleans,
  Atlanta, Seattle, Washington. After: San Francisco, Boston, New York,
  Los Angeles, San Jose, Seattle, Chicago, San Diego, Austin,
  Philadelphia.
- **The same-sex reference search** (a man of 31 seeking men 27–38, never
  married, a degree): 115 of 120 change place, τ 0.76, median 7, largest
  47. Top ten after: San Jose, New York, Boston, Los Angeles, San
  Francisco, Seattle, New Orleans, Washington, Philadelphia, San Diego.
- **The race-on persona searches** — the graduate Asian woman of 30, the
  Black woman of 30, the Pacific Islander man and woman of 35, the
  graduate Asian man of 34, each giving the seeker's race: identical to
  m3.6.0 (every rank and figure); against m3.5.0 only Detroit's weather
  moves any of them, at most five places.

**The stability check** (`gate_m4_0_0_vs_m3_5_0.json`,
`gate_controls_m4_0_0.json`). Read against the m3.5.0 reference, recorded
and not blocking: **1.308** over the 115 searches the change touches
(total wobble 69.05 against 52.81) — above the 1.10 line — and 1.066 over
all 516. The touched searches are the ones without race: the undisclosed
and education-only grid searches, the same-sex grid and the personas
without race; the 400 race-on grid searches are untouched. 68 touched
searches rose more than 25%; the largest risers are the persona with every
importance control moved (1.42 → 3.61 places), women of 25–40 seeking
women with high school or less (to 1.0–1.7), and the man of 41 seeking
women earning 50,000 or more (0.55 → 1.88); the largest falls are the two
personas at the slider's compatibility end (3.37 → 1.41) and the
undisclosed women of 25 and 30. The reference then moved to m4.0.0
(`stability_reference_m4_0_0.json`, total 261.18): read against itself it
reads exactly 1.0 and passes; with every replicate's deviation scaled by
1.5 it reads 1.490 and fails, as it must; the record reproduces the
ship's reading and the validation report search for search. For the
record, m3.5.0 and m3.6.0 read 0.765 and 0.766 against it.

**Phase 3d's V2 open items** (named, not investigated in this phase):

- the shakier searches with runs of cities beyond the fences (Asian,
  Pacific Islander and Hispanic seekers, 49 of V2's 95 risers): unchanged
  for visitors who switch race on — those searches read identical to
  m3.5.0's; with race off the figure no longer depends on the seeker's
  race at all;
- V2's narrow pass of the outlier condition: unchanged — the narrowest
  spread is still 41.8 points, a race-on search (a man of 40, high school
  or less, two or more races);
- the two match-end searches at 3.37 places: both are race-off personas,
  and now read 1.41.

## 5. Pages

- **The nav** is Browse cities, Compare cities, About us.
  `/how-it-works` redirects permanently to `/about`; What we measure keeps
  its page, linked prominently near the top of About us beside About crime
  data and Privacy.
- **About us** is the plain-language account (`docs/methodology.md`, the
  figure's sections rewritten for the rename and race off) and the one
  **Sources and credits** section: the data citations and the Census
  Bureau Data API notice from the licence registry, and every photograph
  the site shows — the hero's credit, then the city and stat-page
  photographs in a collapsible list — with title, author, a link to the
  source file, the licence linked to its deed, and "cropped" where the
  site crops it (the hero). The credit lines under the hero, the city
  photographs and the stat-page photographs are gone; the crime figures
  keep their caveat.
- **Privacy** (`/privacy`, from `docs/privacy.md`, linked from About us,
  not in the nav): a draft for your approval (§6).
- **Every response** of the site and the API says `Referrer-Policy:
  no-referrer`; no page makes a request to another origin (ADR 0017's
  test); the `dsa_prefs` cookie lives 30 days and holds no "about you"
  detail; a whole browser session — the home page, setting the details, a
  city page, the compare page and a shared link opened by someone else —
  is watched by a test, and no request, cookie, link or permalink carries a
  detail, while the recipient of the shared link sees their own figures.
  A returning visitor's stored details never show the list in another
  order first (a test watches every frame).

## 6. Copy for Nathan's approval

Every new or changed sentence, old → new (`copy_changes.json`). The
registry strings and `docs/` are where each one lives.

- **docs/methodology.md, "In a minute" (About us page)** (Stage 3) — presented our counts as coming from the Census Bureau; they are our estimates from its survey (ADR 0012)
  - old: **In a minute:** Every count on this site comes from the Census Bureau's American Community Survey from 2020 through 2024.
  - new: **In a minute:** Every count on this site is our estimate from the Census Bureau's American Community Survey from 2020 through 2024.
- **registry features.pool_size.definition (What we measure, info tips)** (Stage 3) — "counted from" presented a weighted, allocated estimate as a count from the Census survey (ADR 0012)
  - old: The number of people in each city who match your whole search, counted from the Census Bureau's household survey.
  - new: The number of people in each city who match your whole search, estimated from the Census Bureau's household survey.
- **web/src/app/layout.tsx, the site's meta description** (Stage 3) — "Counted from" presented our estimates as counts from the Census survey (ADR 0012)
  - old: "Which city has the best dating scene for you? Counted from the Census Bureau's own survey, city by city."
  - new: "Which city has the best dating scene for you? Estimated from the Census Bureau's own survey, city by city."
- **registry pillars.match.display_name (panel, What we measure)** (Stage 5) — the rename to Compatibility (ADR 0018 §1, Nathan's decision 1)
  - old: "Chances of matching"
  - new: "Compatibility"
- **registry size_vs_odds.label_high (the slider's pole)** (Stage 5) — the rename to Compatibility (ADR 0018 §1, Nathan's decision 1)
  - old: "Chances of matching"
  - new: "Compatibility"
- **registry features.match_propensity.display_name (rows, city page, compare table)** (Stage 5) — the rename to Compatibility (ADR 0018 §1, Nathan's decision 1)
  - old: "Chances of matching"
  - new: "Compatibility"
- **registry features.match_propensity.mover_phrase (the rows' movers line)** (Stage 5) — the rename to Compatibility (ADR 0018 §1, Nathan's decision 1); the bare word could read as ordinary English here, so "the compatibility figure"
  - old: "your chances of matching"
  - new: "the compatibility figure"
- **registry pillars.match.definition and features.match_propensity.definition (What we measure card, info tips)** (Stage 5) — race is off by default and used only if the visitor switches it on (ADR 0018 §2)
  - old: How closely the people who match your search resemble the people who actually pair with someone like you, on age, education and background, where 100 is the US average
  - new: How closely the people who match your search resemble the people who actually pair with someone like you, on age and education (and on background, if you include yours), where 100 is the US average
- **registry strings.slider_info (the slider's information box)** (Stage 5) — the rename to Compatibility (ADR 0018 §1, Nathan's decision 1); race is off by default and used only if the visitor switches it on (ADR 0018 §2)
  - old: Leaning towards size favors larger cities with the most possible matches. Leaning towards chances of matching favors cities where the people who match your search line up more closely with you on age, education, and background, based on historical Census marriage data.
  - new: Leaning towards size favors larger cities with the most possible matches. Leaning towards compatibility favors cities where the people who match your search line up more closely with you on age and education, and on background if you include yours, based on historical Census marriage data.
- **registry strings.match_info (the figure's information box)** (Stage 5) — race is off by default and used only if the visitor switches it on (ADR 0018 §2)
  - old: This compares the people who match your search against the pattern of who actually forms couples in Census data: the age gaps, the education pairings and the racial and ethnic pairings that occur. A higher number means the people here are more like the people who typically pair with someone in your situation.
  - new: This compares the people who match your search against the pattern of who actually forms couples in Census data: the age gaps and the education pairings that occur, and the racial and ethnic pairings too if you include your race or ethnicity. A higher number means the people here are more like the people who typically pair with someone in your situation.
- **registry strings.match_how and docs/methodology.md, the figure's section (About us)** (Stage 5) — the rename to Compatibility (ADR 0018 §1, Nathan's decision 1); race is off by default and used only if the visitor switches it on (ADR 0018 §2)
  - old: The chances-of-matching figure is built from real couples in the Census Bureau's household survey, using each partner's age, education and race or ethnicity. Across the whole country we measure how often each age gap, each education pairing and each racial or ethnic pairing actually occurs, compared with how often it would occur if single people paired at random. That pattern, adjusted a little for each city's own couples, is then applied to the single people who match your search in each city, so the figure says how closely they resemble the people who typically pair with someone of your sex, age, education and background. It is an aggregate pattern from recent unions, not a prediction about any one person, and 100 is the US average for your search.
  - new: The compatibility figure is built from real couples in the Census Bureau's household survey, using each partner's age and education, and their race or ethnicity only if you include yours. Across the whole country we measure how often each age gap and each education pairing actually occurs, compared with how often it would occur if single people paired at random; if you include your race or ethnicity, the racial and ethnic pairings are measured the same way. That pattern, adjusted a little for each city's own couples, is then applied to the single people who match your search in each city, so the figure says how closely they resemble the people who typically pair with someone of your sex, age and education, and background if you include it. It is an aggregate pattern from recent unions, not a prediction about any one person, and 100 is the US average for your search.
- **registry strings.match_same_sex_note (a same-sex figure's information box) and docs/methodology.md** (Stage 5) — same-sex searches use no race pairing (ADR 0018 §3)
  - old: For a same-sex search the age gaps and the education pairings come from same-sex couples in the same survey; the racial and ethnic pairings are borrowed from opposite-sex couples, because the same-sex couples in the survey are too few to measure them dependably on their own.
  - new: For a same-sex search the age gaps and the education pairings come from same-sex couples in the same survey; the racial and ethnic pairings are not used, even if you include your race or ethnicity.
- **registry strings.about_you_note (the panel's "about you" note)** (Stage 5) — the rename to Compatibility (ADR 0018 §1, Nathan's decision 1); the "about you" details stay in the browser (ADR 0018 §4); race is off by default and used only if the visitor switches it on (ADR 0018 §2)
  - old: Optional: your education and your race or ethnicity feed only the chances-of-matching figure. Leave either unset and the average for people of your age and sex is used instead.
  - new: Your sex, education and race or ethnicity stay in this browser and are never sent to us. Education is optional and feeds only the compatibility figure; leave it unset and the average for people of your age and sex is used instead.
- **registry strings.self_race_switch_label (the panel's race switch; new)** (Stage 5) — the "about you" details stay in the browser (ADR 0018 §4); race is off by default and used only if the visitor switches it on (ADR 0018 §2)
  - old: (new)
  - new: Include my race or ethnicity
- **registry strings.self_race_switch_note (the panel's race switch; new)** (Stage 5) — the "about you" details stay in the browser (ADR 0018 §4); race is off by default and used only if the visitor switches it on (ADR 0018 §2)
  - old: (new)
  - new: Off unless you turn it on. Your answer stays in this browser and is never sent to us.
- **registry strings.self_race_same_sex_note (the panel's race switch; new)** (Stage 5) — the "about you" details stay in the browser (ADR 0018 §4); race is off by default and used only if the visitor switches it on (ADR 0018 §2); same-sex searches use no race pairing (ADR 0018 §3)
  - old: (new)
  - new: Not used in a same-sex search.
- **docs/methodology.md, the figure's heading and definition (About us)** (Stage 5) — the rename to Compatibility (ADR 0018 §1, Nathan's decision 1); race is off by default and used only if the visitor switches it on (ADR 0018 §2)
  - old: What are the chances of matching? / **Chances of matching** is how closely the people who match your search resemble the people who actually pair with someone like you, on age, education and background, where 100 is the US average.
  - new: Compatibility / **Compatibility** is how closely the people who match your search resemble the people who actually pair with someone like you, on age and education (and on background, if you include yours), where 100 is the US average.
- **docs/methodology.md, the "about you" paragraph (About us)** (Stage 5) — the "about you" details stay in the browser (ADR 0018 §4); race is off by default and used only if the visitor switches it on (ADR 0018 §2)
  - old: Your own education and your race or ethnicity are optional inputs. They feed only this figure; leave either unset and the average for people of your age and sex is used instead.
  - new: Your own sex, education and race or ethnicity stay in your browser and are never sent to us: the site works out the figure for every possible answer, and your browser shows the one that fits you. Your education is optional; leave it unset and the average for people of your age and sex is used instead. Your race or ethnicity is used only if you switch it on, and then only for this figure; with it off, the figure uses no racial or ethnic pairing at all.
- **docs/methodology.md, the race and ethnicity boxes section (About us; new paragraph)** (Stage 5) — the "about you" details stay in the browser (ADR 0018 §4); race is off by default and used only if the visitor switches it on (ADR 0018 §2)
  - old: (none)
  - new: These boxes are about the people you're looking for. Your own race or ethnicity is a separate setting: it is off unless you switch it on, stays in your browser, and affects only the compatibility figure.
- **docs/methodology.md, how the score works (About us)** (Stage 5) — the rename to Compatibility (ADR 0018 §1, Nathan's decision 1)
  - old: The slider divides the people-side weight between pool size and chances of matching; ...
  - new: The slider divides the people-side weight between pool size and compatibility; ...
- **registry strings.self_race_choose (the race select's empty option; new)** (Stage 5) — the race switch (ADR 0018 §2): switched on, the select starts with no group chosen
  - old: (new)
  - new: Choose one
- **registry strings.about_title (About us; new)** (Stage 5) — the page "How it works" becomes About us (decision 7)
  - old: (new)
  - new: About us
- **registry strings.about_measure_link (About us; new)** (Stage 5) — What we measure leaves the nav and is linked prominently from About us (decision 7)
  - old: (new)
  - new: What we measure
- **registry strings.about_crime_link (About us; new)** (Stage 5) — About crime data stays reachable from About us
  - old: (new)
  - new: About crime data
- **registry strings.about_privacy_link (About us; new)** (Stage 5) — the privacy page is linked from About us, not the nav (decision 9)
  - old: (new)
  - new: Privacy
- **registry strings.credits_heading (About us; new)** (Stage 5) — one section for every source and photograph credit (decision 8)
  - old: (new)
  - new: Sources and credits
- **registry strings.credits_data_heading (About us; new)** (Stage 5) — Sources and credits: the data citations (decision 8)
  - old: (new)
  - new: Data
- **registry strings.credits_photos_heading (About us; new)** (Stage 5) — Sources and credits: the photograph credits (decision 8)
  - old: (new)
  - new: Photographs
- **registry strings.credits_photos_more (About us; new)** (Stage 5) — the collapsible list of city and stat page photographs (decision 8)
  - old: (new)
  - new: Photographs on the city and stat pages ({n})
- **registry strings.credits_source (About us; new)** (Stage 5) — a photograph credit's link to its source file (the word the removed credit lines used)
  - old: (new)
  - new: source
- **registry strings.credits_cropped (About us; new)** (Stage 5) — marks a photograph shown cropped (decision 8)
  - old: (new)
  - new: cropped
- **web/src/lib/nav.ts, the nav** (Stage 5) — Nathan's decision 7: What we measure leaves the nav (its page stays); How it works becomes About us
  - old: Browse cities · Compare cities · What we measure · How it works
  - new: Browse cities · Compare cities · About us

**Reviewed and kept** — sentences that name Census data as a figure's
source, not as the figure (Stage 3):

- registry strings.home_subtitle: "Find out how many people match your search in each city based on Census data." — names the source data; the figure is not called Census data
- registry strings.slider_info: "... based on historical Census marriage data." — names the source data; rewritten in Stage 5 for the rename
- registry strings.match_info: "... the pattern of who actually forms couples in Census data ..." — names the source data; rewritten in Stage 5
- registry strings.match_how / docs/methodology.md: "The chances-of-matching figure is built from real couples in the Census Bureau's household survey ..." — says what the figure is built from; rewritten in Stage 5 for the rename
- docs/methodology.md, where the data comes from: "... weighted the way the Census Bureau weighs them." — describes the weighting, not a figure
- docs/methodology.md, the source table: "Places to go out | Census Bureau business data" — names the source of the stat

**The privacy page** (`docs/privacy.md`), new, in full:

> # Privacy
>
> **In short:** you don't sign up, we don't track you, and what you tell us
> about yourself stays in your browser.
>
> ## Your search
>
> The people you're looking for — their sex, ages, marital status,
> education, income and race or ethnicity — and your own age travel to our
> server so it can build the page you asked for. We use them for that and
> nothing else, and we don't save them on our servers.
>
> ## About you
>
> Your own sex, your education and your race or ethnicity stay in your
> browser. They are never sent to us: not in a web address, a request, a
> cookie or any other way. Our server works out the figures for every
> possible answer, and your browser shows the ones that fit you. Your race
> or ethnicity is used only if you switch it on.
>
> Your browser keeps these details so the site remembers them next time.
> You can remove them at any time by clearing this site's data in your
> browser's settings.
>
> ## The cookie
>
> One cookie, called dsa_prefs, remembers the rest of your search — the
> people you're looking for and your age, never your own sex, education or
> race — for up to 30 days, so the site can show your search again when you
> come back. You can delete it at any time in your browser's settings.
>
> ## Our host
>
> The site runs on Fly.io. Like any web host, Fly.io handles the requests
> your browser sends and keeps standard technical logs, such as IP
> addresses and the addresses of the pages requested, under its own
> privacy policy.
>
> ## No tracking
>
> There are no analytics, no advertising and no third-party trackers on
> this site, and no page loads anything from another company's servers. We
> don't sell or share personal data.
>
> ## Race and sex
>
> The race and sex details on this site are used only to work out the
> figures on the page you asked for. They never feed advertising, listings,
> referrals, or any housing, credit or job use.

## 7. Before launch

`docs/deploy.md`'s list — what stays with Nathan:

Phase 4 did everything in the repository; these are Nathan's own.

- [ ] **Approve the copy**: the privacy policy text and every new or
      changed sentence, listed old → new in `PHASE4.md` ("Copy for
      Nathan's approval").
- [ ] **Terms of use** for the site.
- [ ] **Fly.io's data processing agreement**, and confirming that Fly's
      edge does not log query strings (search settings travel in the
      query).
- [ ] **Look inside both images before the first deploy**: `fly deploy`
      uploads the build context (the repository root) to a remote builder.
      Since Phase 4 a deny-by-default `.dockerignore` keeps the data, the
      results, private folders and key files out of it, and the API image
      copies only `atlas/api` and `atlas/model`; build both images locally
      once and list their files to confirm.
- [ ] **A trademark clearance search** on the name.
- [ ] **HUD's terms**: save the dated snapshot of HUD's terms page to
      `docs/decisions/counsel_packet/attachments/`, as the other sources'
      are.
- [ ] **Optional: an email to ASARB** (the 2020 US Religion Census)
      confirming commercial use, before that source is ever started.
- [ ] **Foursquare's Places Portal terms**, when venues are un-deferred
      (ADR 0012).
- [ ] **The force-push and the GitHub purge from Phase 4 Stage 1**: re-add
      `origin`, force-push every branch and tag, ask GitHub Support to purge
      cached views of the old commits, and check for forks — the exact
      commands are in `PHASE4.md` §1.

## After the phase: Nathan's calls (2026-09-29)

These are **Nathan's decisions**, made after Phases 4b and 4c; ADR 0012 is
amended for the photographs.

**The copy (§6).** Nathan approved all the copy, for now: every change in
§6, the privacy text, and PHASE4B.md §2. Three sentences still name the race
switch Phase 4b removed — Privacy's "Your race or ethnicity is used only if
you switch it on." and two on About us (under Compatibility, and under the
race and ethnicity boxes) — and are flagged for rewording before launch.

**The three switch sentences, reworded (2026-09-30).** At Nathan's request
they now describe the select as it works: a race or ethnicity is used only
when one is chosen instead of "Prefer not to say", the wording About us
already used ("only if you include yours").

- Privacy, "About you": "Your race or ethnicity is used only if you include
  it."
- About us, "Compatibility": "Your race or ethnicity is used only if you
  include it, and then only for this figure; without it, the figure uses no
  racial or ethnic pairing at all."
- About us, "What do the race and ethnicity boxes do?": "Your own race or
  ethnicity is a separate setting: it is used only if you include it, stays
  in your browser, and affects only the compatibility figure."

`e2e/phase4b.spec.ts` holds both pages to it: no switch in their text, and
the "used only if you include it" sentence on each.

**Nice days' caption (2026-09-30).** Nathan pointed out that the line under
every nice-days figure, "mild and dry enough to be outside", reads as a
description of the city (on the stat page: "Seattle, WA 170 mild and dry
enough to be outside") when it is the bar a day has to clear. The
registry's unit for `pleasant_days` now names the days: "days that are
mild and dry enough to be outside", so a city card reads "170 days that are
mild and dry enough to be outside". Build 5b780e4f2444's manifest is
refreshed in place (data identical), the fixture, the stat pages and the
variant cases are regenerated with only that line changed, and goldens.json
is byte-identical. For Nathan's approval.

**The pre-rewrite backup (§1).** Nathan has deleted it (recorded
2026-09-30): neither
`~/Downloads/Projects/Dating_Stats_Atlas_backup_2026-09-28_pre_phase4_rewrite.git`
nor a copy in the Trash exists. With the backup gone, Pew is only in
`atlas/data/private/pew/` (gitignored).

**The photo review (§2).** Nathan said to keep every photograph except
Waco's and Savannah's, and to find replacements for those two; asked
whether that meant all fifteen other removals, he answered: restore all 15.

- **Fifteen removals are restored as they were:** C026 Barnstable, C033
  Bend, C053 Canton, C116 Fort Collins, C136 Gulfport, C146 Hilton Head
  Island, C154 Huntsville, C185 Lakeland, C309 Spartanburg, C318 St. Louis,
  and the five other close calls, C043 Boulder, C061 Charleston WV, C069
  Clarksville, C285 Salinas and S06 (places to go out). For them he sets
  aside the subject rule — three show recognisable people, eight recent
  sculptures and two murals — and, for Hilton Head Island (the America 250
  emblem on its lighthouse) and Lakeland (the city's logo sign), the line
  that no agency logo, emblem or seal appears on any page. Each file came
  back from the Trash matching its recorded sha256, and each render entry
  is rebuilt from its manifest row as `city_images` composes one.
- **Waco's collage stays removed, and Waco gets a replacement:**
  `File:Obligatory_waco_suspension_bridge_photo.jpg`, the Waco Suspension
  Bridge's twin-arched tower head-on under a blue sky (CC BY-SA 2.0,
  Steve). Nathan chose it from the three candidates, over the bridge-deck
  view first put in (CC BY-SA 4.0). Its Commons description is the
  photographer's caption ("Obligatory waco suspension bridge photo"), so its
  alt text is the review's own, approved by Nathan: "The Waco Suspension
  Bridge in Waco, Texas."
- **Savannah's photograph (Tarangire National Park, Tanzania) is
  replaced:** `File:The_Fountain_at_Forsyth.jpg`, the Forsyth Park fountain
  of 1858 (CC BY-SA 4.0, Derrick Gaines). Its Commons description is only in
  Italian, so its alt text is the review's own, approved by Nathan: "The
  Forsyth Park fountain in Savannah, Georgia."
- Both replacements come from three candidates per city that meet every
  rule of ADR 0012 (licence, subject, no logo). The review names them (`photo_review.json`, `replaced`), and the
  pipeline sources exactly those files on any re-run while refusing the
  files they replace (`city_images.source_file`, `photo_review.pinned_files`).
  Wikimedia now serves standard thumbnail sizes, so the two new renditions
  are 1,920 px wide where the others are 1,600; they are still Wikimedia's
  own, unmodified.
- **The 141 photographs under Creative Commons licences before 4.0 stay,**
  credited in the one central list; with the restorations and Waco's
  photograph they are 150.

The site shows 372 photographs — 365 city photographs (every city that had
one before the review has one again), 6 stat-page photographs and the hero
— all credited in About us (`photo_credits.json`).
`pipeline/tests/test_photo_review.py` holds the render data to the review.

## Gate check

| The brief's gate | Reading | |
| --- | --- | --- |
| No blob reachable from any ref carries Pew's per-metro values | 1,407 reachable and 1 stored blob, 0 violations (`pew_history_scan_at_report.json`) | pass |
| Served numbers move only in Stages 3b and 5 | goldens changed at `de35236` (m3.6.0) and `f4dca83` (m4.0.0) only | pass |
| `/v1/rank` p95 < 100 ms | 54.3 ms at a one-minute load of 1.92 | pass |
| Default search's gzipped response ≤ 3× today's | 2.29× (229,408 against 100,050 bytes) | pass |
| No request, cookie, link or permalink carries an "about you" item | the e2e session test and the API's 422s | pass |
| Every hard gate but stability passes on the build shipped | eleven of eleven on 5b780e4f2444 | pass |
| The stability gate read against m3.5.0 and recorded | 1.308 over the touched searches, 1.066 over all; not blocking (ADR 0018 §5) | recorded |
| The reference moves, both controls as ADR 0015 | identity 1.0 and passes; ×1.5 noise 1.490 and fails | pass |
| Explanation invariants, the exact attribution sum for every variant | asserted on every variant of every request (`score_from`); the variant gate in `build.validate` | pass |
| Banned vocabulary | zero in the registry, every served line and every page shape | pass |
| Axe | clean on all eleven page shapes | pass |
| `Referrer-Policy: no-referrer` on every response; cookie ≤ 30 days; no third-party request | the e2e and API tests | pass |
| Tests | pytest 122, vitest 84, e2e 94 | pass |
| Nothing deployed, pushed or sent | `origin` absent; no push | pass |

## Deviations

One line each; `results/phase4/deviations.md` is identical.

- Stage 0: the phase 2g manifest (`results/phase2g/hero_image.csv`) is read by nothing — `hero_image.py` wrote it beside `web/src/data/hero.json` from the same record, and the site reads only hero.json — so it is deleted like the phase 2f file rather than kept with its stray change discarded; `hero_image.py` no longer writes it, and hero.json stays the hero's committed record. Both files' stray change was line endings only (CRLF), which git's `core.autocrlf=input` already hid from `git status`.
- Stage 1: PHASE3D.md's A1 heading cited `efd93d7`, an amended draft of the Phase 3d A1 commit that was never on main (it survived only as an unreachable object), so filter-repo's commit map has no entry for it; the citation now names A1 as it is on main (`98725a2` before the rewrite), in the same follow-up commit as the mapped hashes.
- Stage 1 (the scan): "ten or more of Pew's (metro, value) pairs" is read against chance — a count of ten or more fails only if it beats every one of 200 seeded shuffles of Pew's values across its metros — because the literal count trips on columns of small integers that can hold no Pew value: the Phase 1 income-bucket column, written before the table was downloaded, reads 28 against a shuffled median of 29, and PUMAs per metro 12 against 9. The table itself reads 126 and every `pew_total` column 124 against a shuffled maximum of 19; the positive control (the scan run on the history before the rewrite) flags every known carrier.
- Stage 1 (what stays): Pew's national figure (the one constant the level offset used) and the summary comparisons (median and p90 errors, paired win counts, R²) stay in the history and the reports; they are not per-metro values. The per-metro figures quoted in PHASE3.md, PHASE3B.md and ADR 0009 read `[redacted]`.
- Stage 1 (private copies): besides the table and the current versions of the affected files, the private folder keeps every historical version of each affected file (35 blob versions, indexed by blob id) and the rewrite's log, so the full original record survives outside the repository.
- Stage 1 (local copies): the five ignored Phase 3c seed copies of `pew_lomo_*.csv` (local only, never tracked) carried `pew_total`; they were copied to the private folder and stripped in place with the rewrite's own column transform.
- Stage 1 (the header guard): the tracked-file test recognises the table's column-header line by its SHA-256 (`pew_guard.PEW_HEADER_SHA256`), so no tracked file — the test included — carries the header it looks for.
- Stage 1 (the tool): `git filter-repo` 2.47.0 ran from a throwaway virtualenv (it is not a project dependency); the rewrite was rehearsed on a scratch clone of the backup, verified and scanned there, and the real run produced the same new HEAD (9574d7c).
- Stage 2 (ADR 0012): the FBI citation names 2025, the year the site shows (registry `crime.year`), not the 2021–2025 span the build pulls to choose it from.
- Stage 2 (ADR 0012): the deferred credit lines are taken from each source's own attribution page in the dated 24 September snapshots; Overture's Places section is collapsed in its snapshot, so the ADR records the foundation-level line and the OpenStreetMap line and says the Places section is read again when venues are un-deferred.
- Stage 2: three older lines tied a wording or a deploy to counsel ("if neither is acceptable to counsel", "until the counsel review returns" in both fly.toml files, and the deploy checklist's "if counsel changed wording"); they are reworded so nothing ties a decision to counsel, and the deploy checklist's "counsel review returned and archived" item becomes "every item under Before launch done". `sources.md`'s and `cube.py`'s counsel mentions are reworded in Stage 3, where those files change.
- Stage 3 (the registry): `LicenseTerms.citations` is a tuple, one exact string per product and vintage, because two Census source ids each carry two products (the PUMS and the detailed tables; the relationship files and TIGERweb/cartographic files); OMB's delineation, read through the `census_geo` adapter, gets its own entry (`omb_delineation`) so it is credited as OMB's; `attribution` stays until Stage 5 moves the page to the citations.
- Stage 3 (the build check): `cube.build` held only `active` features to the shippable bar; it now holds every served feature (`active` and `context_only` — crime, balance, who lives here, everyday prices) to "shippable and cited", and the geography sources every figure passes through (`GEOGRAPHY_SOURCES`) to the same bar; the manifest's licences block gains the citations, notice and conditions and lists the geography sources.
- Stage 3 ("Census data"): three sentences presented our estimates as the Census Bureau's (the methodology's "Every count on this site comes from…", the pool definition's "counted from…", the meta description's "Counted from…") and are reworded to "is our estimate from" / "estimated from" (listed in `copy_changes.json`); six that name Census data as the source of a figure, not as the figure, are listed as reviewed and kept, four of them rewritten anyway in Stage 5. The meta description lives in `layout.tsx`, where Phase 3c's call put it.
- Stage 3 (the photo rules): beside the brief's two removal rules (an identifiable person as subject; a recent US sculpture or mural), photographs in which a government or agency logo, emblem or seal is prominent are removed under ADR 0012's no-emblem rule (three: Lakeland's city logo, the America 250 emblem, the Seabee insignia statue, which is also a sculpture).
- Stage 3 (borderline photographs): six of the sixteen removals are borderline calls (C043, C061, C069, C285, C343, S06) and are marked so in `photo_review.json` and on the local contact sheet; all sixteen are removed pending Nathan's confirmation, and restoring one is deleting its entry from the review and re-running `photo_review` (the files are in the Trash).
- Stage 3 (findings, not acted on): Savannah, Georgia ships a photograph of Tarangire National Park, Tanzania — the pipeline resolved the article "Savanna" — which is a wrong image rather than a licence problem, so it stays for Nathan to decide; a stray file (`winston-north-carolina.jpg`, no manifest row, never rendered, no recorded licence) was moved to the Trash with the removals.
- Stage 3 (the CC list): the photographs listed for Nathan's confirmation are every one under a Creative Commons licence before 4.0 — 1.0, 2.0, 2.5, 3.0 and 3.0 US (141) — not only the 2.0 and 3.0 ones the brief names, since 1.0 and 2.5 raise the same question.
- Stage 3 (the hero credit): the live hero is not the Carol M. Highsmith image (it is "Adult couple holding hands", CC0, Alice Donovan Rouse), so the Highsmith credit is recorded in ADR 0012 for the day it is, and not used.
- Stage 3 (logos): `web/public` also holds five unreferenced create-next-app scaffold SVGs, two of them the Next.js wordmark and the Vercel logo; neither is an agency's, no page uses them, and they are left as found (`logo_audit.json`).
- Stage 3b (the version): the rematch moves a served number, so it ships as m3.6.0 (the minor bump `versions.py` gives every served-number change; patches are display-only), with its own build (6172181a114f); Stage 5 then ships m4.0.0 on top of it, and its gate is still read against m3.5.0, the reference, as the brief says.
- Stage 3b (the Phase 2d report): `build.pleasant_days` rewrites `results/phase2d/pleasant_days_report.json`, whose "vs Normals" fields compare against `static_features.csv` — which has held the GHCN values since Phase 2d — so a re-run reads 0 change and 0 metros at 365; the Phase 2d record is restored as committed, and 3b's own before/after is `station_audit_before_3b.json` / `station_audit.json` and the rank shift.
- Stage 3b (the stability gate): read against m3.5.0 and recorded as the brief says, not blocking: 0.999925 (245.054 against 245.073, nothing touched); the reference stays m3.5.0 until m4.0.0.
- Stage 4 (MARHM): "married in the past 12 months" (MARHM) is not in the Phase 1 extract and the raw person files were evicted after extraction, so the newlyweds' record keys come from the Census PUMS API (`2024/acs/acs5/pums`, MARHM = 1 as the predicate, with age, relationship, race and Hispanic origin to check the join) rather than a re-download of every state's person file; every joined record matches the extract on all four fields.
- Stage 4 (the fetch): the first responses for Arkansas and Oklahoma arrived corrupted in transit (digits injected into fields, 31 rows unparseable and hundreds silently wrong); both were fetched again, and a second complete fetch of all 51 states then agreed with the cache record for record.
- Stage 4 (the universe): the rate counts every newlywed with a linked spouse — same-sex couples included (3.9% of linked newlyweds) and every age the item covers — as the brief defines it, while the kernel's predictions are opposite-sex and 18–70, the same kind of mismatch the Pew reading carried; each metro's opposite-sex-only rate is recorded beside it.
- Stage 4 (the floor): Pew's floor of 200 newlyweds in sample is applied to each metro's allocated sample (records times their metro allocation), giving 124 metros — the same count Pew's table matched, by coincidence; the agreement with Pew is reported on all 124 metros both cover and on the 107 of them that also meet the floor.
- Stage 4 (what the check loses, measured): beyond the brief's "same survey, different subset", the check's record measures the overlap — newlyweds are 8.1% of the kernel's decay-weighted fitting weight (6.1–10.2% across metros), and a metro's dials are fitted on its own couples, so the dial-based predictions are only partly out of sample; ADR 0016 says so.
- Stage 4 (Pew in the code): `kernel.pew_table`/`pew_national` are replaced by readers of the PUMS reference, `pew_comparison` becomes `outgroup_comparison` (neutral keys: `reference_national`, `level_offset_ratio_ours_over_reference`, `outgroup_pred`; stores written before Phase 4 are read under either name), `kernel_refine`'s record key becomes `intermarriage`, the sample-choice rule reads the new check, and `kernel.pew_rerun` — Phase 3b's one-off Pew re-run — is retired with Pew (its record stays as history); `build.validate`'s soft `pew_reproduction` becomes `intermarriage_pums`.
- Stage 5a (the same-sex form): "the same-sex age and education terms" are refitted with no race component, like the race-off form (`samesex --race-free`), rather than the joint same-sex fit with its race term dropped; the two tie on held-out same-sex couples (−0.25 per 1,000 couple-sides, within ADR 0014's margin), and the refit ships to match decision 2's "refitted, not zeroed".
- Stage 5a (normalisers): the race-off and same-sex normalisers are computed on the served kernel's national availability (the array the artifact carries and the engine reads); the refinement store recomputes it with a different summation order (relative differences of 1e-16).
- Stage 5b (one figure, one value): the compatibility figure's technical stats entry carries the figure at its match block's precision (two decimals; it carried four), so the single-seeker path and the variants agree field for field and the response sends it once.
- Stage 5b (the margin): the variant columns leave out the compatibility figure's margin (moe) — computed by the single-seeker `rank()` and never rendered (ADR 0004) — which the brief's list of what each variant carries does not name; leaving it out also keeps the payload in budget.
- Stage 5b (the arithmetic): to compute 50 variants within the latency budget, the seeker's interaction tensor is contracted level by level (the same code on both paths), average ranks are computed in numpy rather than pandas, and each metro's cards and crime block are kept per build; on the m3.6.0 build, over 181 searches, every served number is unchanged but the stats-entry precision above, and every race-on search in the rank shift and the gate reads identical to m3.6.0.
- Stage 5b (the layout): the variant columns are field-major and in each variant's own rank order (`order` names each row's position in `ranked`), which compresses best (2.29× today's gzipped default against 2.61× row-aligned); `rank` is still sent although it is 1…n, so the browser never takes a ranking number from a position.
- Stage 5b (the default variant): a visitor who has not given their own sex is taken as the opposite of the sought sex (the old default, a woman seeking men, is that case), with education not given and race off; the server renders that variant first.
- Stage 5c (the two sex fields): changing "I'm a" keeps an opposite-sex search opposite-sex (the sought sex follows, as it did when it defaulted to the opposite of the visitor's), and changing "I'm looking for" first stores the own sex the panel was showing, so a woman who switches to seeking women gets a same-sex search.
- Stage 5c (old links and cookies): an old link's `self_sex`/`self_edu`/`self_race` move into storage only where storage holds nothing (a shared old link would otherwise overwrite the recipient's own details), an old `dsa_prefs` cookie is rewritten without them the same way, and an old link or cookie with no sought sex keeps the search it meant (the opposite of its `self_sex`), decided in the browser; an old permalink token's own sex is never read, so one without a sought sex reruns with the default one.
- Stage 5c (the race switch): switching race off removes the race from the browser's storage too; switched on with no group chosen, the figure stays race-free until one is chosen.
- Stage 5c (no reordering flash): the chosen approach is a script in the page head that, before the first paint, hides what a variant changes (visibility, so nothing shifts) whenever the browser holds details, until the page has selected the stored variant, with a four-second fallback; a returning visitor with details sees a moment of blank rather than a list that reorders, and a test watches every frame.
- Stage 5d (About us): methodology.md's title "How the numbers are made" becomes a second-level heading under the page's "About us", wording unchanged; the link under the home list keeps its words ("How it works") and now goes to About us.
- Stage 5d (the credits): the data credits are the licences' citations and the Census Bureau Data API notice, each once; only photographs the site shows (their file on disk) are credited; the city and stat-page photographs sit in a collapsible list. One city photograph's title, "Four-market-square-tn1" (Knoxville's Market Square), holds a word on the banned-vocabulary list; it is the work's title, which its licence asks to be reproduced, and the rendered-text sweep does not read the collapsed list.
- Stage 5d (tsconfig): the web tsconfig included a September build directory's generated types (`.next-prod/types`, an old local build, gitignored), which named the renamed page and failed the e2e build's type check; the include is removed.
- Stage 5 (the deploy context): both images build from the repository root and `fly deploy` uploads that context to a remote builder; with no .dockerignore, and the API image copying all of `atlas/`, a deploy from a working machine would have carried the data, the private Pew copy, key files and the decision records' private packet into the build context and the image. A deny-by-default `.dockerignore` and narrower COPY lines keep them out; building both images locally to check is added to "Before launch".
- Stage 5e (the gate): read against m3.5.0 and recorded, not blocking (ADR 0018 §5): 1.308 over the 115 searches the change touches (the searches without race, education alone included, the same-sex grid and the personas without race), 1.066 over all 516; the 400 race-on grid searches are untouched. The reference then moved to m4.0.0: identity reads 1.0, the ×1.5 noise control 1.49 and fails.
- Stage 5e (the rank shift): reported from m3.5.0, as the brief says, and from m3.6.0 beside it; the two differ only by Detroit's weather (m3.6.0).
