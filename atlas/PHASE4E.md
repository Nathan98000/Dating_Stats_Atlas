# Phase 4e — walkability explained, two stat-page photos, "Home", a new nice day

## 1. In plain words

Five changes, in three commits. The first two change only words and
pictures, and no number on the site moved (checked over all 518 test
searches and all 387 city profiles). The third changes how "nice days a
year" is counted. The new rule is stricter, so every city has fewer nice
days — the typical city goes from 115 to 79 a year. Nice days are a small
part of the overall score, so the rankings barely move: the top ten of the
default search is the same, and the typical city moves one place. Every
check passed. One stop condition fired on the way — the site seemed to
have become slow — and the cause turned out to be the Mac's Low Power Mode,
not the code; with it switched off, everything runs as fast as in Phase 4.

Commits on branch `claude/phase4e` (not pushed): A `57facd9`, B `f6fee4b`,
C `ba6adab`.

## 2. The five changes

1. **Walkability, explained** (A). A registry key new to every feature,
   `stat_page_note`, shown after the definition on
   `/stats/resident_walkability_index` only; the definition used elsewhere
   is unchanged. **The draft is accurate and is kept as written.** Checked
   against what the build uses: the EPA's `NatWalkInd` ranks each
   neighbourhood (2010 block group) on intersection density (D3B), distance
   to the nearest transit stop (D4A), the jobs-and-households mix
   (D2A_EPHHM) and the mix of eight job types (D2B_E8MIXA); the city's
   figure is the `TotPop`-weighted mean over its block groups. Two details
   the sentence does not need to say: streets and transit count double the
   two mix measures in EPA's formula, and a block group with no index takes
   its metro's median.
2. **A new nice day** (C) — section 4.
3. **Who lives here, a photo** (B) — section 3.
4. **Political lean, a photo** (B) — section 3.
5. **Nav** (A). "Browse cities" reads **Home**: Home · Compare cities · About
   us (`web/src/lib/nav.ts`, its comment, the phase2f e2e test).

## 3. For Nathan's approval

**a. The walkability sentence** (on its stat page only):

> The EPA's index scores each neighborhood on how connected its streets
> are, how close it is to public transit, and how mixed its homes, shops
> and workplaces are. A city's figure averages those scores over where its
> residents live.

**b. The nice-day definition** (`pleasant_days.definition`, also the stat
page subheading):

> Days a year that average between 55 and 75°F, stay below 85°F and above
> 45°F, and have no more than a light shower and no snow

**c. Two readings.** "Between 55°F and 75°F" is read as the day's
**average**, (high + low) / 2 — GHCN's own average is often missing, and
separate high and low limits would otherwise be redundant. "No deep snow
cover" is read as **snow on the ground under 1 inch**. Both are in the
registry and easy to change. (In practice the snow terms almost never
bite: with the low above 45°F they removed 27 days in all, across every
station and thirty years.)

**d. The photos.** Each page shows its pick; the alternates are saved
locally (gitignored) for you to compare.

- **Who lives here** — pick: the Place des Vosges, Paris (public domain,
  Gryffindor; the article "Row house", the first subject on your list
  whose photo passes). Alt text: its Commons description, "Place des
  Vosges in Paris, eastern side." Local file:
  [web/public/stats/who_lives_here.jpg](web/public/stats/who_lives_here.jpg).
  Alternates:
  [brownstone stoops in Chelsea, New York](results/phase4e/_photos/who_lives_here_alt1_chelsea.jpg)
  (CC BY-SA 3.0, the article "Neighbourhood"; 1,024 px wide) and
  [a row of Harlem brownstones](results/phase4e/_photos/who_lives_here_alt2_harlem.jpg)
  (CC BY 4.0, Paul Lowry; the article "Brownstone", outside your list).
  The pick is Paris on a site about US cities — either alternate is a US
  street, if you prefer one.
- **Political lean** — none of your three subjects passed: "Ballot box"
  shows Ukraine's state coat of arms on every box (the emblem rule), and
  "Polling place" and "Voting booth" both lead to a UK photo whose author
  cannot be read (the licence rule). So the pick is a Commons file found by
  searching: **an empty polling place in Grand Rapids, Minnesota** — two
  booths marked VOTE with a US flag, no people, no party anything (CC BY
  2.0, Lorie Shaull). Local file:
  [web/public/stats/political_lean.jpg](web/public/stats/political_lean.jpg).
  Its Commons description is an attribution request, so it has a review
  alt text, a **draft**: "Two voting booths on a table in an empty polling
  place in Grand Rapids, Minnesota." Alternates:
  [three voting booths at Shamrock Town Hall, Minnesota](results/phase4e/_photos/political_lean_alt1_shamrock.jpg)
  (CC BY 4.0, Lorie Shaull; no sign or symbol at all) and
  [a "Vote Here" sign with a US flag](results/phase4e/_photos/political_lean_alt2_vote_here.jpg)
  (CC BY 2.0, Tony Webster).
- Both credits are in About us → Sources and credits only, not cropped.
  Every image seen and its verdict is in
  `results/phase4/photo_review.json` → `phase4e_stat_pages`. Left out on
  purpose: all-red "I Voted" stickers (red is the Republican colour on
  that page).

**e. Every other changed sentence, old → new**
(`results/phase4e/copy_changes.json`):

- Nav: "Browse cities · Compare cities · About us" → "Home · Compare cities · About us".
- Nice days' definition: "Days a year that reach between 55 and 85°F,
  don't dip below 40°F, and see no more than a light shower" → (b) above.
- Two photo alt texts and two credit lines, new (d above).
- No About us, Privacy, Terms or methodology sentence stated the old
  thresholds (About us names only "NOAA daily weather-station records,
  1991–2020"), so none changed. Outside the site: `docs/sources.md`
  (variables now include SNOW and SNWD) and ADR 0005 (amended).

## 4. Nice days, before and after (`results/phase4e/nice_days.json`)

| | min | p10 | median | p90 | max |
|---|---|---|---|---|---|
| all 387, before | 33.6 | 92.6 | 115.2 | 153.8 | 336.2 |
| all 387, after | 9.6 | 55.0 | 78.9 | 107.0 | 303.9 |
| ranked 193, before | 55.0 | 100.0 | 118.3 | 164.7 | 336.2 |
| ranked 193, after | 15.9 | 63.4 | 81.1 | 117.0 | 303.9 |

Every metro loses days (by 24 to 105; median 38); the cities' order by nice
days stays close (Spearman 0.92).

- **Biggest drops:** Honolulu 182 → 77, Charleston SC 216 → 135, Vallejo
  188 → 108, Santa Maria 269 → 191, Santa Rosa 153 → 76, San Luis Obispo
  266 → 192, Salinas 280 → 206, Kahului 172 → 102, Napa 208 → 140, San
  Jose 212 → 146. (Not separated by criterion here; the likely causes are
  Hawaii's warm days against the 75°F average and 85°F high, and coastal
  California's cool nights against the 45°F low.)
- **Smallest drops** (no city rises): Carson City 34 → 10, Utica 105 → 80,
  Los Angeles 320 → 292, Waterloo IA, Mankato, Ames, Burlington VT, Duluth,
  Grand Forks, Rochester MN (each about 27 fewer).
- **Top 10 under the new rule** (ranked cities): San Diego 304, Los Angeles
  292, Oxnard 275, San Francisco 240, Riverside 210, Salinas 206, San Luis
  Obispo 192, Santa Maria 191, San Jose 146, Charleston SC 135.
- **Bottom 10:** Bend 16, Ogden 34, Greeley 34, Reno 37, Provo 40, Yakima
  42, Anchorage 44, Denver 46, Boulder 52, Lubbock 53 — mostly high, dry
  places with cold nights.
- **Metros without a qualifying station:** none, before and after
  (unchanged). Every metro keeps the same station.
- **Snow data:** 712,139 of the 918,196 counted days (78%) had a snow
  reading; the snow terms excluded 27 days in total.
- **NOAA's data:** the old rule, run on the new download, reproduces every
  served value exactly — every change above is the rule's.

**The rank shift** (`rank_shift_m4_1_1_to_m4_2_0.json`):

- Default search (someone of 30 seeking men 28–40): 148 of 193 cities
  change place; Kendall's τ 0.968; median move 1, 90th percentile 5,
  largest 21 (Eugene 73 → 94); scores move a median 0.3 points (max 3.5).
  Top ten unchanged.
- Same-sex reference search (a man of 31 seeking men 27–38, never married,
  a degree): 71 of 120 change place; τ 0.968; median 1, largest 13
  (Honolulu 41 → 54). Top ten unchanged.

## 5. Checks and test counts

| Check | Result |
|---|---|
| A and B move no number | 518/518 rank responses, 1,036/1,036 rank(), 387/387 profiles identical (`served_numbers_commit_a/b.json`) |
| ADR 0011 gate, C's build vs the m4.0.0 reference | **0.999** (fail above 1.10), over all 516 searches (`gate_m4_2_0.json`) |
| Hard gates (`build.validate`) | 11/11, including pleasant-days sanity: no city at 365, rain only removes days (Spearman 0.755 with rainy days), coldest metro 357th of 387 |
| Latency p95 | **57.8 ms** (limit 100) — after the halt below |
| pytest / vitest / Playwright | 187 / 103 / 135 passed |
| Privacy network test | unchanged, passes |
| axe | zero serious or critical |
| Banned vocabulary | none (registry loader, validate gates, e2e sweeps) |
| Pew guard on every changed file | clean (86 files) |

**The halt.** C's build first read 99.1 and 102.1 ms p95, over the line —
a stop condition, so I halted and reported. You asked me to investigate:
every release, back to m4.0.0 (54 ms in Phase 4), read 91–105 ms on the
Mac that day, and the Mac was in Low Power Mode. You switched it off; the
same interleaved benchmark then read 53–56 ms for every release, m4.2.0
within 0.3 ms of the live site (`halt_latency.md`).

## 6. Deviations

- Political lean's photo comes from a Commons search, not from any of the
  three subjects in the brief (each failed a rule; recorded).
- Who-lives-here's second alternate (Harlem brownstones) comes from an
  article outside the brief's list.
- `city_images` gained `--stats <fid>` so the two pages could be re-sourced
  without re-keying the 387 city rows; stat pages now honour a review alt
  text, as city pages already did.
- Commit A records `n_source_files_fetched` as 2,587 (the committed fetch
  manifest's count): the background weather re-fetch was growing the
  manifest while A's build manifest was refreshed.
- NOAA's access API was throttled to about 2 files a minute; the 997
  station files were fetched with two parallel downloaders and recorded in
  the fetch manifest in one pass (each file checked against its URL key
  and as a CSV), instead of through `fetch()` one at a time.
- The ADR 0011 gate counts a search as "touched" only when its
  compatibility index moves, which weather never feeds; it therefore read
  all 516 searches — its strictest basis.
- Latency was halted, investigated and re-measured with Low Power Mode off
  at Nathan's word; the passing figure is that measurement.
