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

Recorded when m4.0.0 ships (Phase 4 Stage 5e).
