# ADR 0018 — Compatibility; race off by default; same-sex searches without race; "about you" in the browser

Date: 2026-09-28 (Phase 4, Stage 5)
Status: accepted; amended 2026-09-29 (Phase 4b, below) and again
2026-09-29 (Phase 4c, below). Every decision below is **Nathan's
decision** (decisions 1–5 of the Phase 4 brief; the Phase 4b and Phase 4c
changes after his reviews). The measured parts —
the race-free form's held-out cost, the payload and latency of the variant
design, the rank shift, the stability gate's reading and the reference
move — are recorded in the "At the ship" section when m4.0.0 ships.

## 1. The figure is renamed "Compatibility"

- As a label, a heading or the slider's pole it is **"Compatibility"**
  (today "Chances of matching").
- In running text it is "compatibility" only where the sentence plainly
  means the figure; where the bare word could be read as ordinary
  English, the text says "the compatibility figure".
- It is never called a "score": "score" already means a city's overall
  score.
- Internal names do not change: the `match` pillar, `match_propensity`,
  `pool_vs_match` and the URL parameter `s`.

## 2. Race is off by default

A visitor who has not switched race on gets no race component at all:
no race pairing, no race × education interaction, and no
population-average mixture over races. The figure comes from a
**race-free form**: the cohort age term and the education matrix, with no
race component and no interaction, refitted by the same machinery (not C1
with its race terms zeroed), with its own per-metro dials. A visitor's
own race is used only if they switch it on; then the figure is C1's, as
m3.5.0 serves it.

## 3. Same-sex searches use no race pairing at all

Even with race switched on, a same-sex search uses the same-sex age and
education terms and nothing else: no race term, no interaction. This
**supersedes the Phase 3c/3d call** (ADR 0010 as amended in m3.3.0, kept
by Nathan after Phase 3d) that the race × education interaction rides on
same-sex searches (+2.90 per 1,000 sides, 1.66 SE), and the m3.2.0 rule
that a same-sex search borrows the opposite-sex race term.

## 4. The "about you" details live in the browser

- The visitor's own sex, education and race are never sent to the
  server: not in the query string, the request body, the cookie or any
  header. `/v1/rank` rejects them with a 422, and the sought sex is always
  explicit.
- The server computes every variant — own sex (2) × own education (not
  given, or one of 4) × own race (not used, or one of 8), de-duplicated
  where a variant cannot differ (own race never matters on a same-sex
  search) — and the browser only selects the one that applies. It never
  computes a ranking number.
- Share links and permalinks leave the details out, so a shared link
  shows its recipient their own compatibility figure.
- Own age stays on the server as today: it is not a sensitive attribute,
  and the age term needs it.

## 5. The stability check reads this phase's changes; it does not block them

At the ship, the ADR 0011 gate is read against the m3.5.0 reference and
recorded as a finding; it does not block the ship. The reference then
moves to the new build (m4.0.0), with both controls re-run as ADR 0015
did (identity reads 1.0; the ×1.5 noise control fails).

## At the ship

m4.0.0 ships as build **5b780e4f2444** (kernel artifact `kernel_v3`). Every
number below is read from the file named beside it, under `results/phase4/`.

### The race-free form (`race_free_heldout.json`)

The race-off default is the form D0: the cohort age term and the education
matrix, refitted with no race component and no interaction by the same
machinery, with its own per-metro dials (age and education earn them: τ
0.064 and 0.088). On the usual held-out measure (leave one metro out,
split-half, shrunk dials; ADR 0014's margin of 0.25 per 1,000 weighted
couple-sides):

- **What leaving race out costs:** D0 is 407.1 per 1,000 couple-sides below
  C1 (402.3 on the national-only reading), below it in all 387 metros.
- **Why it is refitted:** D0 beats C1 with its race terms set to zero by
  2.2 per 1,000 couple-sides (better in 266 metros), a win under ADR 0014.
- The intermarriage check (ADR 0016) reads the race-free form at a median
  error of 34.9 points against C1's 1.9 — random pairing reads 35.7: a
  form without race cannot predict who marries across groups, and does
  not claim to.

A same-sex search takes the same-sex age and education terms, refitted
with no race (`kernel/samesex_fit.json`): it passes the same-sex face
checks, sits 151.4 per 1,000 same-sex couple-sides below the composition
m3.5.0 served (race borrowed, the interaction riding), and ties the joint
same-sex fit with its race term dropped (0.25 per 1,000, within the
margin). A seeker who switches race on gets C1 exactly as served: its
arrays are copied byte for byte from the kernel artifact m3.5.0 and m3.6.0
both serve (the same file), and every race-on search reads identical to
m3.6.0 (below).

### The variants (`payload_before.json`, `payload_after.json`, `latency_m4_0_0*.json`)

The server computes 50 variants per search (45 for the opposite-sex own
sex — education not given or one of four, times race off or one of eight —
and 5 for the same-sex one, whose race variants are one). The default
search's gzipped response is 229,408 bytes, 2.29 times the 100,050 before
(budget 3 times); the same-sex reference search 161,428, 2.09 times. The
API's latency over the standard 400-request mix is p95 54.3 ms (34.9 before;
budget 100 ms) at a one-minute load average of 1.92; the default search
alone p95 61 ms. Every variant equals the single-seeker ranking exactly
(checked for all 90 combinations of two searches through HTTP in the tests,
and for a spread of variants of every persona in `build.validate`'s new
hard gate).

### The rank shift (`rank_shift_m3_5_0_to_m4_0_0.json`)

- **The default search** (a woman of 30 seeking men 28–40, race off): 185
  of 193 cities change place, Kendall's τ 0.81, median move 9 places,
  largest 83; the compatibility figure moves by a median 1.9 points
  (largest 17.4). The top ten becomes San Francisco, Boston, New York, Los
  Angeles, San Jose, Seattle, Chicago, San Diego, Austin, Philadelphia.
- **The same-sex reference search** (a man of 31 seeking men): 115 of 120
  change place, τ 0.76, median 7, largest 47.
- **The race-on persona searches** (five, each giving the seeker's race):
  identical to m3.6.0; against m3.5.0 only Detroit's weather (m3.6.0)
  moves any of them, at most five places.

### The stability check (`gate_m4_0_0_vs_m3_5_0.json`, `gate_controls_m4_0_0.json`)

Read against the m3.5.0 reference, as decided, and recorded, not
blocking: **1.308** over the 115 searches the change touches (total wobble
69.05 against 52.81) — above the 1.10 line — and 1.066 over all 516; 68 of
the touched searches rose more than 25%, the largest the persona with
every importance control moved (wobble 1.42 to 3.61), women of 25–40
seeking women with high school or less, and the man of 41 seeking women
earning 50,000 or more; the largest falls are the two personas at the
slider's compatibility end (3.37 to 1.41) and the undisclosed women of 25
and 30. The 400 race-on grid searches are untouched.

The reference then moved to m4.0.0: `results/phase4/stability_reference_m4_0_0.json`
(total wobble 261.18), the record `stability_gate.REFERENCE` names; m3.5.0's
record stays under `results/phase3d` as history. The controls, re-run as
ADR 0015 ran them: the reference read against itself reads exactly **1.0**
and passes; with every replicate's deviation scaled by 1.5 it reads
**1.490** and fails, as it must. The record reproduces the ship's reading
and its validation report search for search. Every other hard gate passes
(`validation_report_m4_0_0.json`: eleven of eleven, the new variant gate
among them).

## Amended in Phase 4b (2026-09-29): the panel and the figure

Nathan reviewed the home page after m4.0.0 and changed how the panel asks
for the visitor's details and how the figure is presented. Nothing the
API computes changes: every served number, every variant and the goldens
are as m4.0.0 ships them (build 5b780e4f2444, its manifest refreshed in
place for the registry strings). These are **Nathan's decisions**.

- **The opt-in is the race select's default.** The race switch and the
  select it revealed become one select, "My race or ethnicity", whose
  first option, selected by default, is "Prefer not to say": race is not
  used. Choosing one of the eight groups turns race on — still an active
  choice by the visitor, as §2 requires — and there is no separate
  switch. The browser keeps a race only when one is chosen, so a stored
  race means race is on; a detail stored by m4.0.0 (`{raceOn, race}`)
  reads as the same choice, and is rewritten without the switch when it
  is read. On a same-sex search the select is disabled and keeps its
  value (§3: the figure uses no race there). *[Superseded in Phase 4c,
  below: the select stays operable there, muted and explained.]*
- **No inline notes about where the details go.** The panel carries no
  note beside the visitor's details — the "about you" note and the
  switch's notices leave the panel and the registry — because the Privacy
  page explains it. §4 is unchanged: the details never leave the browser.
- **The same-sex note sits in the side panel's information box.** The box
  beside "What matters more to you?" carries Nathan's text and, on a
  same-sex search only, the served same-sex sentence (the rows'
  `match.note`, `strings.match_same_sex_note`); the loader still holds
  that sentence to the kernel's same-sex components.
- **The compatibility figure shows no information box and no band
  words** — on the result rows, the city page and the compare table. The
  number against 100 says where a city stands, and the panel's box is the
  one explanation. The API still sends the band; every other figure keeps
  its band words.

Beside these, the panel is split into two labelled sections, "About you"
and "Who you're looking for", and the overall score carries the label
"Overall score" on every result row and in the compare table. The strings
added, changed and removed are listed in `PHASE4B.md`.

## Amended in Phase 4c (2026-09-29): same-sex searches

Nathan made two changes for same-sex searches. These are **Nathan's
decisions**. Every score and rank is unchanged; the served balance moves on
same-sex searches only (ADR 0004 amended), so the model is m4.1.0 on the same
build, 5b780e4f2444, its manifest refreshed.

- **Own race is selectable on a same-sex search, and explained on hover.**
  The race select stays operable there — neither disabled nor
  aria-disabled. A choice is stored as usual (in the browser only, §4),
  changes nothing on the same-sex search (§3: the figure uses no race
  there, so every race selects the same variant), and applies as soon as the
  search is opposite-sex again. The field is muted — grey text on the paper
  background, a dashed border, every colour at WCAG AA — and the registry's
  tip, `strings.self_race_same_sex_tip` (Nathan's wording: "This information
  is not used to calculate compatibility for same-sex couples because not
  enough data is available to make a reliable estimate."), shows while the
  pointer is over the field or the select has keyboard focus. It is always
  the select's description (`aria-describedby`), so a screen reader
  announces it. A touch screen has no hover: there an information button
  beside the label opens the same text (its name,
  `strings.self_race_same_sex_tip_label`, "Why race or ethnicity isn't used
  here", was drafted in Phase 4c and approved by Nathan after the report).
  An opposite-sex search shows the plain field, with no tip. This supersedes
  the Phase 4b line that the select is disabled on a same-sex search.
- **Balance no longer depends on own sex.** Balance is the single people of
  the sought sex per 100 single people of the other sex (ADR 0004 amended),
  so §4's variants carry one balance per search (`variants.balance`) instead
  of one per own sex (`variants.by_sex`), and `balance_applies` is gone. Own
  sex still selects the compatibility figure and the ranking it feeds; the
  details still never leave the browser, and the response is smaller than
  m4.0.0's for every test search.

## Amended in Phase 5 (8 October 2026): each variant carries its median score

Approved by Nathan on 10 October 2026 (Phase 5, commit I). The featured cards and the city page draw a tick
on the score track at the median overall score of the cities ranked for the search, so "77/100"
reads against the middle of the list. The median is a number, so the API computes it: each entry
of `variants.list` gains `score_median: {value, display}` — the median of that variant's
unrounded ranked scores, `value` to one decimal like a row's `score`, `display` a whole number
like its `score_display` (null when nothing is ranked). `rank()` returns the same field, and
`select_variant` and `lib/variants.ts` hand it on, so the parity tests cover it. It is additive:
no existing field changes, nothing ranks, scores or selects by it, and the visitor's own details
still never leave the browser — the median of every variant travels, as everything else does.
Over the 518 ADR 0011 test searches every other part of every /v1/rank response is unchanged
(`results/phase5/served_numbers_commit_i.json`). The goldens do not move, so the field ships
inside m4.2.1, the release Phase 5's commit C opened.

## Amended in Phase 6 (9 October 2026): an ⓘ beside "Optional"

Approved by Nathan on 9 October 2026 (Phase 6, commit F; his decision 4). Phase 4b dropped every inline
note beside the "about you" inputs because the Privacy page explains where they go. The round-3
review (F10) found the page asking for race and education under nothing but an "Optional" pill,
and the Privacy page never saying the details are not sent. This reverses Phase 4b's "no inline
notes" for one box only: an information button beside "Optional" in Sharpen compatibility (rail
and sheet), named `sharpen_info_label`, whose box holds `sharpen_info` ("…They stay on this
device: the site sends the figures for every combination, and your browser shows yours.") and a
link to Privacy (`sharpen_info_link`). It shows only on demand; the trust line and the "stays in
this browser" line stay deleted. Nothing about the mechanism changes: the details never leave the
browser, and the privacy network test passes unchanged. The Privacy page's "Your search" section
now says so too.

## Amended 10 October 2026: Sharpen compatibility is its heading alone

At Nathan's request (10 October 2026). The "Optional" pill (`optional_pill`, after the Phase 5
report) and the ⓘ beside it (Phase 6's `sharpen_info_label`, `sharpen_info` and
`sharpen_info_link`) are deleted: the group shows its heading and, opened, its two fields, in the
rail and in the sheet. This reverses the Phase 6 amendment above. Nothing about the mechanism
changes: the details never leave the browser, the privacy network test passes unchanged, and the
Privacy page's "Your search" section still says so.
