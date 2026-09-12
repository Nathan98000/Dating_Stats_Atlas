# Phase 2b — the site: public-beta ready, running locally

Paste everything below into Claude Code at the repo root.

---

You are continuing the Dating Stats Atlas build. Phases 0, 1 and 2a are complete and
committed. Read these first, in order: `atlas/PHASE2A.md`, `atlas/PHASE1.md`,
`atlas/docs/methodology.md`, `atlas/docs/decisions/0001-acs-race-ethnicity-standard.md`, the
proposal (`Dating Stats Atlas.html` at the repo root — §5.2, §5.3, §8.2, §8.3, §9, §10, §11,
§12.3, §13.1 are what this phase implements), then `atlas/api/app.py`,
`atlas/model/{preferences,scoring,suppression,intervals,explain}.py` and
`atlas/pipeline/registry/features.yaml`.

**Phase 2b is the site.** Out of scope, deliberately: the POI union (registry entry stays
`status: deferred`), the build-time metro narratives (their §9 metric-record contract is
pinned — do not consume it yet), the religion layer, and deployment. Commit Vercel and
Fly/Render configuration and a deploy runbook, but **do not deploy** — the licensing review
in `docs/decisions/counsel_packet` has not returned, and no public URL exists until it does.

One backend carve-out is in scope and is item 5.

Ground rules, unchanged and still the point: nothing is tuned to make a check pass, a failing
check is a finding to report rather than a bug to hide, every deviation from the spec is
documented with its reason, and no number is displayed that the API did not compute.

## Acceptance gates — the phase is not done until all six hold

1. Every population figure rendered anywhere carries its margin **in the row**, in the exact
   words the policy strings use: "at least this wide," never "±" alone. No margin behind a
   tooltip, on hover, or rounded away.
2. Every number on every screen reaches its provenance record in one click.
3. Suppressed and shown-not-ranked metros are visible as counts with reasons, never silently
   absent.
4. WCAG 2.1 AA: contrast, full keyboard operation, visible focus, and a screen-reader
   rendering of the margin that cannot be mistaken for a precise figure.
5. The permalink round-trips: the frontend's decode of `/r/<data_version>/<model_version>/<state>`
   equals `model.permalink`'s encode, asserted by a shared test, not by inspection.
6. Playwright e2e green in CI alongside the existing suite.

## 1. Three spec corrections to make on the way in

The proposal's §5.3 mock row is now wrong in three ways, and the frontend is where that gets
fixed rather than inherited:

- **`84,200 ± 6,100`** becomes `84,200 · margin at least ±6,100`. The served interval is a
  one-sided calibrated upper bound (PHASE2A §Gate 0); "±" asserts symmetry the mechanism does
  not have.
- **`CV 4%`** leaves the row. The served CV is also an upper bound; it belongs in an
  expandable detail, labelled as one.
- **"38% of the pool in walkable tracts"** becomes the residents wording — the feature is
  `resident_walkability_index`, the walkability of where the metro's residents live, because
  the pool exists only at metro level. Never write "of the pool."

Also: the CV tiers are being removed in this phase (item 11), so `shown_unranked` returns to
being a permanently empty array. Handle it defensively — render the section only if it is
non-empty — but do not design a UI section for a tier that cannot fire, and never render a
"0 metros shown but not ranked" line.

## 2. Architecture and URL state

Next.js + TypeScript + Tailwind per §8.3. **The browser never calls FastAPI directly.** The
API binds loopback with no CORS and there is no public API (D04), so a Next.js server route
proxies `POST /v1/rank`. A frontend that fetches the ranking endpoint from the client breaks
the decision that the whole licensing posture rests on.

The URL is the state (§10.1): every preference in the query string, the first ranking
server-rendered from a sensible default profile, results on arrival rather than a form
(§10.2). Permalink routes carry both version pins. Handle the API's **409 on pin mismatch**
as a real page that says the link was made under a different build and offers to re-run under
the current one — never silently serve today's numbers under yesterday's permalink.

Nothing is recomputed in the browser. Score, margins, tiers, contributions and explanation
strings all arrive from the API. A frontend that re-derives any of them can disagree with its
own permalink.

## 3. The ranking page

Open on results, controls beside them, the list visibly reordering as a control moves. The
size-versus-odds slider is the hero (D05, §10.3) and sends `size_vs_odds`, not a weight
vector; per-pillar weights live in a "fine-tune" disclosure below.

Each row: rank, metro name **from the build's `metros.json`** (never hand-typed — the
delineation is pinned), pool with its margin, partners-per-rival, score, the API's rendered
`explanation` string, the comparator sentence, and any flags (`low_allocation_purity`,
`gq_flag`, missing-feature renormalization). Contributions render the exact linear
attribution (§7.5, §9) — that decomposition is exact, so the copy must never read as
inference.

Do **not** put `score_moe` in the row. It is a first-order approximation stacked on a
one-sided bound (PHASE2A item 5); it belongs in the detail with a plain sentence saying so.

Below the list, permanently: how many metros are shown-not-ranked and how many suppressed,
each with its reason and a link to the policy; and above the list, the "fewer than 40 metros
ranked" notice when it fires (§5.2, D11). No rank bands.

Controls must only offer what the cube can answer: `income_min` has to be a band edge or the
API 422s, so the income control is a select over the band edges, never free text.

## 4. Identity controls (§10.4, D02)

Off by default, in a secondary group, never a step in the primary funnel. Race and ethnicity
multi-select maps to `seeking.race_ethnicity` using the spec names. Whenever a race filter is
active, the cross-group pairing rate renders **beside the pool at the same visual weight** —
not a footnote. `cross_group_pairing_rate: null` must never render as "0%". Disabled states
explain themselves. No superlative anywhere across groups: metro pages describe composition,
rankings stay personal. Religion controls are absent, not greyed teasers — that layer is
Phase 4.

## 5. The one backend carve-out: an interim cross-group pairing rate

§10.4 and D02 require the counterweight whenever a race filter is on, and the full assortative
kernel is Phase 3. Build the minimum that satisfies the product rule honestly:

Pair spouses and unmarried partners within PUMS households from the housing and person files
already extracted (`RELSHIPP` links, asserted rather than assumed — verify the codes against
the pinned dictionary the way `pums verify` does). For each metro × sex × race group, compute
the share of partnered people whose partner is outside their own group. Gate it with the same
min(allocated, Kish) ≥ 100 rule, and carry an interval by the same one-sided mechanism if it
extends to a ratio — if it does not, say so and suppress rather than display a bare number.
Ship it in `features.parquet`, fill `cross_group_pairing_rate`, and register it in
`features.yaml` with full provenance and `default_weight: 0`: it is a counterweight, not a
scored feature, and it must never enter a pillar.

Two things to carry with it. The §7.3 limitation copy, verbatim in spirit: observed couples
describe who matched, not who was available, so the copy says "how couples here actually pair,"
never "what people here want." And a directional comparison against Pew's 2015 metro
intermarriage table as a **warning, not a gate** — reproducing that table is Phase 3's gate,
and this interim estimate is explicitly replaced then.

## 6. Metro pages (§10.5)

All 387 metros get a page, not just the 193 ranked. The objective profile stands alone for a
visitor arriving from search with no preferences; the personalised layer appears above it once
preferences exist. Unranked metros get the explicit "not enough sample to rank" state — an
honest empty state is better content than a bad number (D03). Crime renders at CBSA level with
the FBI's own comparability caveat attached and is never part of any score (D01). No star
ratings: the number and its interval.

## 7. Methodology page and provenance drill-down

Render `docs/methodology.md` for the interval, suppression and provenance language — it is
versioned with `model_version`, so the page must render it rather than paraphrase it. The
provenance drill-down renders the provenance record from the build manifest, not prose
somebody typed. Attribution strings come from the registry's typed license fields, and the
exact required wording must stay pluggable in one place: the counsel memo may change it.

Add to that page what Phase 2a measured and the spec had not anticipated: the B12007
state-median fallback, the walkability naming correction, and the interval mechanism's two
published numbers.

## 8. Search (§8.3)

A ~40 KB JSON index shipped to the client — CBSA names, principal cities, state
abbreviations, and hand-written colloquials ("NYC", "the Bay Area", "DFW", "Twin Cities",
"the Triangle") — fuzzy-matched in the browser. No server round-trip, no search
infrastructure.

## 9. Design register

Editorial data-journalism: type-led, restrained palette, generous whitespace, the numbers
carrying the visual interest. The register of a statistical publication, not a dashboard and
not a listicle. Keep tokens in one place (Tailwind config plus a small token set) so it can be
re-skinned without touching components. No chart junk, no gauges, no stars.

First ranking visible within two seconds of arrival (§10.2) — measured, not asserted. No
layout shift while the slider moves.

## 10. Tests, and one differential check worth adding

Playwright e2e, wired into `.github/workflows/ci.yml`: URL round-trip; permalink decode equals
`model.permalink`; the slider reorders the list; a race filter renders the counterweight; a
query that suppresses metros shows the footer counts and reasons; a suppressed metro's page
renders its explicit state; and a keyboard-only path through the hero control.

While the harness is open, add a **randomized cube-versus-SQL differential** over filtered
query shapes as a build gate. Phase 2a's mask-axis bug is the reason: a cell-by-cell mask test
pins one mechanism, but a randomized differential over the whole query path is what would have
caught it on the day it was written, and will catch the next one.

## 11. Drop the CV tiers: gate on n alone (decided — implement it)

Phase 1 measured that the 20–30% CV tier never fires: above the 100-respondent gate, true CV
never exceeded 12.9% over 23,262 points, and the n-gate agreed with the full specified policy
on 100.00% of them. Phase 2a then wired the tiers to the **served** CV — an upper bound padded
by a median 23.4% and a p90 51.5% — so a metro could be demoted from the ranking by the
conservatism of our interval rather than by anything about its data. That was a side effect of
a display decision, not a decision anyone took. **Nathan has now taken it: drop the CV rules
and gate on n alone.** See `docs/decisions/0002-suppression-gate-n-only.md`.

Implement exactly that:

- `min(n_alloc, kish) < 100` (or an empty pool or rival set) suppresses; everything else in the
  ranked set ranks. No CV rule suppresses and no CV rule demotes.
- `shown_unranked` stays in the response contract as a permanently empty array, so removing
  the tier is a no-op for clients. Retire the `cv_above_20` and `cv_above_30` reason strings
  from the code — they can no longer be produced — and say so in the contract docs.
- **The served interval is unaffected.** Every population figure still carries its margin in
  the row in the required words. This changes only which metros get a rank, never what is
  displayed beside a number. The served CV may still appear in the expandable detail, labelled
  an upper bound; it just decides nothing.
- Bump `model_version` to `m1.2.0` — §5.4 versions the suppression policy, and D08's thresholds
  are covered by golden tests — and regenerate the goldens with a commit note saying what moved
  and why.
- Update `docs/methodology.md`: the policy table loses the two CV rows and gains a short,
  plain statement of why a rule that never fires was removed rather than carried. The
  "fewer than 40 metros ranked" notice is unaffected and stays.

One measurement to take while you are in there, because the ADR should rest on this build's own
numbers rather than Phase 1's smaller battery: **the p99 and maximum true CV in the served
region of the 480-shape battery** (n_gate ≥ 100, where intervals display). If that maximum sits
below 20%, then the removed rule provably could not have fired on the data at all, and that one
number is the whole justification. Report it, and add it to the ADR and the methodology page.
If it does exceed 20% — which would contradict Phase 1 — stop and report before removing
anything, because the decision was taken on the assumption that it does not.

## Exit

`atlas/PHASE2B.md` in PHASE2A.md's style: every acceptance item with its measured result,
every deviation with its reason, the accessibility audit result, the measured time-to-first-
ranking, e2e timings, and what Phase 3 inherits. Screenshots of the three states — ranked,
shown-not-ranked, suppressed — plus one with a race filter active showing the counterweight.
Commit in logical units in the existing message style.

State plainly in the first paragraph whether all six acceptance gates hold, and if any does
not, which and why.
