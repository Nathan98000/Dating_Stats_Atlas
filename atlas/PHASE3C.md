# Phase 3c — the counsel packet catches up with the site; the stability gate reads the whole picture; same-sex searches get their measured education pattern (m3.3.0)

Every number here is read from a file under `results/phase3c/` (or a
committed record it names); nothing was recomputed for the report.

**In plain words, for Nathan.** Three things happened. First, the
lawyer's packet now describes the site as it is: the chances-of-matching
figure and how race enters it, what a visitor may tell the site, that
the search sits in the page address and in a cookie for about six months,
and the Pew table the build reads as a check — with two questions added
and one made honest, so it is ready for you to attach the licence pages
and send. Second, the stability test that decides whether a change to
the matching figure is allowed no longer turns on whether two near-tied
cities swapped places in one search; it now asks whether rankings got
shakier overall, against a fixed yardstick (the build you have now), and
it passed both of its own sanity checks — reading a build against itself
as exactly equal, and correctly failing a build whose survey noise was
artificially inflated by half. Third, same-sex searches now use the
education pairing pattern measured on same-sex couples, which predicts
those couples better, and the sentence on the page says exactly what is
measured and what is borrowed; a test now holds the sentence to the
model so they cannot drift apart. The held-back refinements were then
re-tested under the new rule; the outcome is in section 3.

## 1. The new gate (B1, ADR 0011)

**The rule.** For each of the 80 replicate versions of the survey, take
every city in the top 10 of either the published ranking or that
version's ranking, measure how many places each moved between the two
rankings, and average those moves; a search's wobble is that average over
the 80 versions (a 10th–11th swap counts one place for each city; a city
jumping from 40th into the top 10 counts thirty). The test searches are
the eighteen personas, the Phase 3b effects grid and a new same-sex grid
(men seeking men and women seeking women at 25, 30, 35, 40 and 50, the
grid's window and marital selection, education undisclosed or each
level): 518 requests, none identical, 516 scored (two personas rank fewer
than 12 metros and are skipped as before), over 26 distinct sought
pools. A change fails if its total wobble over the searches it touches
(any whose point or replicate index differs) is more than 10% above the
reference's total over the same searches; when nothing is touched the
totals run over every search. The reference is m3.2.0 (`f20cb02c3af8`),
fixed in `stability_reference.json` and moved only by an ADR. The rule,
the controls and the ADR were committed (374f8d6) before any held-back
refinement was run through the gate.

**The two controls** (`gate_controls.json`):

| Control | Reads | Verdict | Control passes |
|---|---|---|---|
| The reference against itself | **1.000000** — nothing touched, every hash equal, 316.209 places on both sides | pass | yes |
| The reference with every replicate deviation scaled by 1.5 | **1.509778** — 477.406 against 316.209, all 516 searches touched | fail | yes |

The reference's wobble runs from 0.0025 to 2.494 places per search
(median 0.4705); the two searches at the slider's match end wobble most.
Under the old rule the reference's worst persona sits at exactly 0.800
(the man of 41 seeking women earning 50k+), and the old rule read over
all 516 searches would give a minimum share of 0.775.

**How the gate reads the past three builds** (`past_readings.json`;
m3.1.0's kernel from its complete build, m3.0.0's rebuilt from its
retired record — see deviations — each loaded into the reference build's
cubes, which are byte-identical across the three):

| Change | Searches touched | Wobble before → after | Ratio | Verdict | Searches whose wobble rose > 25% |
|---|---|---|---|---|---|
| m3.0.0 → m3.1.0 (the five-year sample) | 516 of 516 | 319.631 → 309.511 | **0.968** | pass | 73 |
| m3.1.0 → m3.2.0 (race × education; the same-sex age term) | 516 of 516 | 309.511 → 316.209 | **1.022** | pass | 123 |

Both changes the old rule read as a cliff — m3.0.0 failing at 0.70 and
m3.1.0 passing at 0.95, then m3.2.0 passing at exactly 0.800 — read as
small overall moves here: the five-year sample made rankings 3.2% steadier
in total, race × education 2.2% shakier. Reported; nothing changed
because of them.

**The old and new readings side by side on the shipped build:** section 5.

## 2. Same-sex education (B2, ADR 0010 amended)

**Held-out gain and the face check** (`samesex_fit.json`,
`lomo_samesex.json`; leave one metro out, 387 metros, 1,452,508 weighted
same-sex sides). Against what m3.2.0 serves — age from same-sex couples,
education and race from opposite-sex couples, the interaction riding —
the education term measured on same-sex couples gains **+6.98 per 1,000
weighted sides** with the interaction switched off (better in 266 of 387
metros) and **+15.90** with it on (301 of 387). Positive either way, so
the term ships and the stop condition did not fire. Support is unchanged
(smallest education cell 255 effective sides). The amended face check —
every own-level multiplier above 1, and each own level above every level
two or more away — passes for both sexes: own levels 1.19 / 1.42 / 2.05 /
4.55 (high school or less → graduate). The old diagonal-dominance reading
still fails the bachelor's row (2.44 with graduate partners against 2.05
at the same level) and is kept as a soft reading. Race stays borrowed.

**The interaction decision.** With education now same-sex, the reason
for letting the opposite-sex race × education interaction ride on a
same-sex search no longer held, so both compositions were scored on
held-out same-sex couples: **the interaction rides**, by +8.92 per 1,000
sides over the composition without it. The artifact records it
(`same_sex.interaction_applies: true`), the loader reads it and
`seeker_weights` applies it; an m3.2.0 artifact without the field keeps
that release's rule.

**The gate's reading of the term alone** (`gate_B2_samesex_edu.json`,
the shipped opposite-sex form plus the same-sex decision, against the
reference): 51 searches touched (the same-sex grid and the same-sex
persona), total wobble 23.793 → 20.729, ratio **0.871**, pass. Twelve of
the 51 rose by more than 25% (named in section 4).

**The sentence as served** (`strings.match_same_sex_note`, every row of
a same-sex search, and the methodology page):

> For a same-sex search the age gaps and the education pairings come from
> same-sex couples in the same survey; the racial and ethnic pairings are
> borrowed from opposite-sex couples, because the same-sex couples in the
> survey are too few to measure them dependably on their own.

`loader.same_sex_note_names` parses the sentence — the clause before the
semicolon names what is measured on same-sex couples, the clause after
it what is borrowed — and `load_build` refuses a build whose sentence
names components other than the kernel's `same_sex_components`;
`test_same_sex_note_names_reads_the_sentence` and
`test_same_sex_search_says_whose_patterns_it_uses` hold it.

## 3. C1, C2, C3 (B3)

Each candidate is a held-back refinement added to the shipped form
(baseline + race × education), fitted on the shipped five-year sample,
tested by leave-one-metro-out on split halves (`refine_heldout.json`,
`lomo_forms.json`; the same 387 metros and halves as Phase 3b), written
as an artifact with the same-sex decision of section 2 — as it would
ship — and read by the new gate against the m3.2.0 reference
(`gate_C*.json`). A candidate qualifies if it improves total held-out
likelihood over the shipped form and passes the gate; of those that
qualify, the largest gain ships.

| Candidate | Held-out gain over the shipped form (per 1,000 weighted sides; metros better) | Gate (touched; total wobble; ratio) | Old rule's reading (soft) | Outcome |
|---|---|---|---|---|
| **C1** — the cohort age term (seventeen cohorts as chosen in 3b) | **+69.705** (386 of 387) | 516 of 516; 316.209 → 307.128; **0.971**, pass | min share 0.7875 (would have failed at 0.80) | **ships** |
| **C2** — the sex-specific education matrix | **−0.003** (194 of 387) | 516 of 516; 316.209 → 312.510; 0.988, pass | 0.75 | dropped as measured: no held-out improvement |
| **C3** — both | **+69.704** (386 of 387) | 516 of 516; 316.209 → 306.747; 0.970, pass | 0.8125 | qualifies; C1's gain is larger by 0.001 |

C1 and C3 tie to the third decimal, which is what C2 says on its own:
the sex-specific matrix adds nothing to a form that already carries the
interaction. The rule is mechanical and picks C1. Under the old rule C1
would have failed on one persona at 0.7875 — the same term that failed
at 0.675 in Phase 3b — while making rankings 2.9% steadier in total over
all 516 searches; 98 searches' wobble rose by more than 25% under it
(section 4). For the record, against the baseline form the gains read
+83.8 / +14.1 / +83.8 for C1 / C2 / C3 (`refine_heldout.json`), and the
Pew corrected median absolute error stays at 2.50–2.52 for all three.

**The shipped build is m3.3.0**: C1 plus the same-sex education term
with the interaction riding; every component keeps its dial (τ 0.064 /
0.078 / 0.122 for age / education / race).

## 4. What changed for the visitor

**The rank shift from m3.2.0** (`rank_shift_m3_2_0_to_m3_3_0.json` /
`.csv`, snapshots taken on each build):

| Search | Metros | Ranks changed | Kendall τ | Median move | p90 move | Largest move | Top 10 |
|---|---|---|---|---|---|---|---|
| The stated default (a woman of 30 seeking men 28–40) | 193 | 170 | 0.94 | 2 | 11 | 26 (Provo, 153 → 179) | the same ten cities; Philadelphia and Chicago swap 3rd and 4th, San Jose falls from 8th to 10th behind Seattle and Atlanta |
| The same-sex reference (a man of 31 seeking men 27–38, never married, with a degree) | 120 | 100 | 0.862 | 4 | 15 | 32 (New Haven, 69 → 37) | Denver enters at 10th, Madison leaves; Boston rises to 3rd |

The default search's index moves a median 0.8 points (p90 2.2, largest
4.9; range 84.0–114.9 → 85.2–111.5); the same-sex reference's a median
1.0 (largest 4.4), with San Jose still top by index at 116 (was 117).
The disclosed reference searches keep their top city and their count of
metros above the 250 cap (San Jose 250+ for the graduate Asian woman of
30 and the graduate Asian man of 34; Montgomery for the Black woman of
30; Fayetteville for the Pacific Islander seekers; the graduate woman of
30 reads San Jose 190, was 192).

**Every test search whose wobble rose more than 25%** (98 of 516 —
findings for Nathan, not gates; `validation_report_m3_3_0.json` →
`hard.rank_stability.searches_wobble_rose_more_than_25pct`, with the
reference and shipped wobble beside each). Over all 516 searches the
shipped build is steadier in 291, shakier in 224 and unchanged in one
(the total falls 2.9%). Of the 98 risers, 79 are effects-grid searches,
16 same-sex grid searches and 3 personas; 4 rise from a base under 0.05
of a place. The eighteen with an absolute rise of a quarter of a place
or more:

| Search | Wobble, m3.2.0 → m3.3.0 |
|---|---|
| man of 25, some college | 0.72 → 1.31 |
| persona: man of 33 seeking Hispanic women | 0.81 → 1.37 |
| woman of 25, two or more races | 0.75 → 1.24 |
| man of 50, some college, white | 1.06 → 1.51 |
| man of 50, high school or less | 0.85 → 1.23 |
| man of 25, high school or less | 0.28 → 0.65 |
| man of 30, some college | 0.42 → 0.78 |
| same-sex: woman of 50 seeking women, bachelor's | 0.26 → 0.60 |
| persona: woman of 31 seeking men of two or more or another race | 0.95 → 1.27 |
| woman of 25, undisclosed | 0.68 → 1.00 |
| man of 50, some college | 0.92 → 1.23 |
| woman of 25, some college, white | 0.91 → 1.21 |
| man of 50, two or more races | 0.56 → 0.86 |
| same-sex: woman of 35 seeking women, some college | 0.75 → 1.05 |
| woman of 25, some college | 0.90 → 1.20 |
| (and three more between 0.25 and 0.30 of a place; the full list of 98 is in the report file) | |

The third persona among the risers is the widest legal search (a man of
35 seeking women 18–70), 0.24 → 0.39. The searches at the slider's match
end remain the wobbliest on the site, 2.49 → 2.88 places. The pattern
behind the risers is the cohort age term: the youngest and oldest
seekers, whose gap curves moved most, sit at the top of the list.

**The same-sex education term's own risers** (section 2's twelve, from
`gate_B2_samesex_edu.json`): men of 25 and 40 seeking men with a
bachelor's (0.0025 → 0.07 and 0.015 → 0.11, from near-zero bases), men
of 30 with high school or less (0.17 → 0.37), women of 50 with a
bachelor's (0.26 → 0.52), men of 40 with a graduate degree (0.14 → 0.28),
men of 35 with a bachelor's (0.18 → 0.31), women of 25 with a bachelor's
(0.20 → 0.32), men of 50 with a bachelor's (0.20 → 0.29), women of 25
with a graduate degree (0.31 → 0.44), women of 40 undisclosed (0.50 →
0.70), women of 35 with high school or less (0.41 → 0.58) and women of
35 with a graduate degree (0.33 → 0.45). The other 39 same-sex searches
got steadier, and the 51 together by 12.9%.

## 5. The battery on the shipped build (m3.3.0, build ee4f08cf33e1)

`build.validate` on ee4f08cf33e1 (`validation_report_m3_3_0.json`,
`validate_m3_3_0_run.log`): **ten of ten hard gates pass**.

| Hard gate | m3.2.0 | m3.3.0 |
|---|---|---|
| Interval calibration | pass | pass |
| Suppression reasons and intervals | pass | pass |
| Cube-vs-SQL differential | pass, 1.98e-7 | pass — 40 shapes, both paths, the kernel-weighted sum with seventeen cohorts and the interaction |
| **Rank stability (ADR 0011)** | reference | **pass — 0.971**: all 516 searches touched, total wobble 316.209 → 307.128 (median 0.4705 → 0.4597, largest 2.494 → 2.878) |
| Explanation invariants | pass | pass — 2,065 explanations, zero banned terms |
| Kernel face validity | pass | pass — the 30-year-old's multiplier peaks at 30 for both sexes; both per-sex education matrices diagonal-dominant; every own-group race multiplier above its off-diagonals; the served same-sex age term peaks at 30 and the served same-sex education matrix passes the amended rule for both sexes (own level above 1, above every level two or more away; the soft diagonal-dominance reading fails the bachelor's row, as expected) |
| Pew never shipped (Phase 3c A3) | — | pass — the licence is registered non-shippable, no feature traces to the table, nothing in manifest.json or kernel.json names it |
| Adversarial artifacts | pass | pass |
| Pleasant-days sanity | pass | pass |
| Crime consistency | pass | pass |

**The old and the new reading side by side on the shipped build.** The
old rule, reported as a soft reading beside the new one: minimum share
of replicates keeping 8 of 10 across the sixteen scored personas
**0.7875** (the two searches at the slider's match end; the next lowest
0.9875), which would have failed at the 0.80 bar. The new rule reads
0.971 and passes. That is the decision in ADR 0011 doing its work on the
first build after it: the same cohort age term that the old rule refused
in Phase 3b, at 0.675 then and 0.7875 now, makes rankings 2.9% steadier
across the 516 test searches while moving the top-10 boundary of the two
match-end searches.

Soft gates: weight sensitivity τ 0.92–0.99 for every ±20% (pool ±20%
0.920 / 0.937, match 0.937 / 0.924, reach 0.955 / 0.932, cost 0.963 /
0.961, weather 0.983 / 0.981, students 0.992 / 0.987); the Pew
reproduction reads the shipped form's record from Phase 3b as before
(2.51 / 2.49 / 3.39 shrunk / raw / national-only, the accepted tie
noted); the served-region true CV unchanged.

**Latency** (`measure_latency.py`, 400 queries through the ASGI stack
after a warm-up): p95 **59.19 ms** on the idle re-measure (`latency_m3_3_0_idle.json`; p50 42.11, p99 73.3, max 80.51; load averages 2.05 / 3.47 / 8.41 over 1 / 5 / 15 minutes, the one-minute figure at Nathan's usual baseline, the longer ones still cooling from the chain) and 58.27 ms in the ship chain (`latency_m3_3_0.json`; p50 41.72, load 2.35 / 4.24 / 11.08). Both under the 60 ms budget, by 0.8 and 1.7 ms. **A finding for Nathan:** m3.2.0 measured p95 41.11 ms (p50 30.71) at a load of 2.48, so the p95 has risen by about 18 ms while the median is unchanged (about 42 ms). Nothing in the weighted path should cost more per request — the cohort term selects one curve of seventeen instead of one of one — and the 15-minute load was still 8–11 on both runs, so whether this is the engine or the machine is not settled here; the fair test is an engine-level A/B of the two kernels under equal load on a quiet machine, which the version-pinned loader did not allow in this session (the API refuses an m3.2.0 build under an m3.3.0 engine). The budget is nearly spent either way.

**Tests.** `pytest atlas`: 61 passed on the m3.3.0 fixture (the one
failure in the ship chain was a test that double-rounded the served
value; deviations). Playwright, hermetic on the fixture: **78 passed**,
the axe suite clean on home, results, city, narrow search, compare,
compare landing, stat page and What we measure.

**Retired and pointed.** ae1efbef9f0e (m3.1.0) is retired to its
manifest, metros and kernel record; f20cb02c3af8 (m3.2.0) stays complete
as the gate's reference; `.claude/launch.json` points at ee4f08cf33e1.
Nothing is deployed.

## Gate check

1. **The counsel packet** describes the matching score and its two uses
   of race, what visitors may disclose, the URL and the cookie, and lists
   the Pew table; its PDF and DOCX are regenerated, the checklist is
   updated, nothing is sent, and Part A is its own commit (3057615). ✓
2. **The new stability gate, ADR 0011 and both controls were committed
   (374f8d6) before any held-back refinement went through the gate**;
   the identity control reads 1.0 and the enlarged-noise control fails
   (§1). ✓
3. **Same-sex searches serve the measured education term**: the amended
   face check passes, the re-measured held-out gain is positive (+6.98
   without the interaction, +15.90 with it), the interaction is decided
   by held-out fit (it rides), the page sentence names exactly what is
   served, and the loader assertion plus two tests hold it (§2). ✓
4. **C1, C2 and C3** each report a held-out gain and the gate's verdict;
   C2 does not qualify (no held-out improvement); of C1 and C3 the
   larger gain, C1, ships (§3). ✓
5. **All hard gates pass** on ee4f08cf33e1, with the old overlap share
   reported beside the new reading (§5). ✓
6. **Latency**: p95 59.19 ms idle (load 2.05) and 58.27 ms in the chain (load 2.35), both under 60 ms; the rise from m3.2.0's 41.11 ms is a finding (§5). ✓
7. **Strings and copy.** No new registry key: the one changed string is
   `match_same_sex_note`, whose text the brief fixed, and the loader
   asserts it against the kernel; axe reports zero serious or critical
   issues on eight page shapes; the banned-vocabulary sweep returns zero
   across 2,065 explanations; Nathan's approved copy is byte-identical
   (`match_info`, `match_how`, `slider_info`, `about_you_note`, the home
   strings, the crime caution — the diff touches none of them). **No
   sentence of his was made inaccurate by this phase.** One standing
   item, not caused here and left as it is: the methodology page's race
   boxes paragraph (m2.0.0, commit c8a2960) says the boxes "say nothing
   about who dates or marries whom, and this site makes no claim about
   that"; since m3.0.0 the chances-of-matching figure is built from
   observed pairing patterns by race, so the second clause reads wider
   than the site now is. Listed for Nathan; not re-worded. ✓

## Deviations

- A4: pandoc and LibreOffice, which made the 12 September DOCX and PDF (pandoc's reference styles in the DOCX; "LibreOffice 26.2.5.2 Writer" in the PDF's producer field), are not on this machine and Docker Desktop is paused; the DOCX was regenerated with pandoc 3.9 installed into the session scratchpad (not the project venv), and the PDF by Google Chrome headless from pandoc's HTML (the third route in `docs/decisions/counsel_packet/render.sh`; the Word route was not tried because it would raise a macOS automation prompt no one was present to answer).
- A4: the memo filing instruction now says `0012-data-licensing-review.md`: 0001–0010 exist and 0011 is reserved by Part B of this brief for the stability gate.
- A4: the checklist's example attachment filenames were re-dated from `_2026-09-12` to `_2026-09-24` to match the packet's new date (none had been saved; `attachments/` is empty).
- A1: question 8's "we do not store visitors' search preferences" carried the same inaccuracy as the privacy paragraph, so it was revised too, although the brief names only the paragraph.
- A1: the "What it is" sentence said the site ranks by how many people are competing; balance has been context-only since m3.0.0 (ADR 0009 §7), so the sentence now names chances of matching as the ranked quantity and balance as information only.
- A3: the provenance assertion (`assert_all_shippable`) traces published fields to adapter sources and cannot see a file read outside an adapter; the Pew table is read directly by `build.kernel`, `build.kernel_refine` and `build.validate`, so a specific hard check (`pew_never_shipped`) was added to `build.validate`, and the packet says so.
- A3: TIGERweb (Census Bureau internal points for counties and places) was in `docs/sources.md` and the geography build but not in the packet's source table; added.
- A3: `docs/sources.md`'s "last checked" line was moved to 24 September 2026 (m3.2.0) after the fetch-manifest comparison; its opening sentence now admits the Pew check as a second non-federal source.
- B1: "any whose index changes" is read as the point index OR any replicate figure differing from the reference's (both are hashed per search); when nothing is touched the totals run over every search, which is what lets the identity control read exactly 1.0 rather than 0/0.
- B1: two personas rank fewer than 12 metros and are skipped as before (E_black_woman29_stress, below_bar_nhpi_250k); 516 of 518 searches are scored.
- B1: the pool's per-cell replicate sums are cached under `data/phase3c_cache/` (never committed) rather than `results/`, because they are 210 MB per sought pool; the reference record commits only per-search figures and hashes.
- B1: the wobble path composes the kernel-weighted numerator in numpy from cached float32 cell sums instead of the suite's SQL join; checked on three personas to agree to 1e-8 relative.
- B1 (readings): the m3.0.0 kernel could not be loaded from its retired build (59fd352c5c2f keeps no kernel.npz), so it was rebuilt from the retired kernel.json — which carries the kernel_v1 terms and every metro's dials in full — with the normalisers recomputed by `kernel.log_norm_for` from the same national singles array the fits used (`phase3c_past_readings.py`); the reading is of that rebuilt kernel loaded into the reference build's cubes, which are byte-identical across the three builds.
- B2: the same-sex LOMO was re-run in full (1,880 s with 8 workers) rather than re-scored from Phase 3b's record, because the record held no composition with education from same-sex couples beside the served age term, and no interaction variant.
- B2: the same-sex candidate artifact was written by `kernel_refine ship --form shipped` into `results/phase3c/_candidates/` (the shipped opposite-sex form plus the same-sex decision), so the gate read it exactly as it would ship; `ship` gained `--form` for the B3 candidates the same way.
- B2: the fit store for Phase 3c is a seeded copy of the Phase 3b records (`results/phase3c/_seed.sh`); files that stayed byte-identical to their Phase 3b originals are not committed twice.
- B3: C1 and C3 tie on held-out gain to 0.001 per 1,000 sides (+69.705 against +69.704); the stated rule (the largest gain among qualifying candidates) picks C1, and the sex-specific matrix that C3 adds is the term C2 measured as adding nothing (−0.003) on the shipped form.
- B3: every C fit's interaction stage stopped at its 200-pass ceiling with a final change under 0.0009 in a log multiplier (Phase 3b deviation 3 repeated); C1's and C3's raw age stage also stopped at 200 iterations, as the cohort fit did in 3b. Recorded, not material.
- B3: C2's full-sample fit fails the opposite-sex face check — the men's bachelor's row loses diagonal dominance once the interaction is present (2.008 at own level against 2.030 with graduate partners; B2b alone passed) — moot, since C2 is dropped on held-out fit, but recorded.
- B3: the C forms' leave-one-metro-out pass took 6,772 s with 8 workers (three interaction forms at 28–30 iterations per metro).
- Ship: m3.3.0 is written by `kernel_refine ship --form C1_cohorts_plus_shipped` (the form by name; the "shipped" name in the Phase 3b store stays the m3.2.0 form), so the store records both.
- Ship: `test_match_display_cap_is_presentational` failed on the m3.3.0 fixture because it re-rounded the two-decimal served value (79.50 → 80) and compared it with the display formatted from the raw index (79.496 → "79"); the display path is unchanged since m3.1.0, so the test now checks the display is within half a unit of the served value. Nothing in the model was touched.
- Ship (latency): the p95 was measured twice — 58.27 ms right after the chain (load 2.35 / 4.24 / 11.08) and 59.19 ms after the one-minute load fell to 2.05 (5- and 15-minute loads 3.47 / 8.41) — because the first read 17 ms above m3.2.0's 41.1; both are under the 60 ms budget and both are reported; an engine-level A/B under equal load was not possible in this session (the version-pinned loader refuses the m3.2.0 build under the m3.3.0 engine) and is left for Nathan.
