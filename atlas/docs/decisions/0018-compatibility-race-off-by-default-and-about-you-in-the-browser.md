# ADR 0018 — Compatibility; race off by default; same-sex searches without race; "about you" in the browser

Date: 2026-09-28 (Phase 4, Stage 5)
Status: accepted. Every decision below is **Nathan's decision** (decisions
1–5 of the Phase 4 brief). The measured parts — the race-free form's
held-out cost, the payload and latency of the variant design, the rank
shift, the stability gate's reading and the reference move — are recorded
in the "At the ship" section when m4.0.0 ships.

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
