# ADR 0011 — The rank-stability gate reads the whole picture: total wobble against a fixed reference

Date: 2026-09-24 (Phase 3c, B1; committed before any held-back refinement
was run through it — the commit order is the proof that the rule was not
fitted to its results)
Status: accepted

## The old rule and what it selected between

Since m3.0.0 the battery's hard rank-stability gate resampled every
persona's pool and chances-of-matching figure across the 80 replicate
weights and failed a build if any single persona's top 10 kept fewer than
8 of its 10 cities in 80% of the replicates. Phase 3b showed the verdict
turning on where near-ties happened to fall at 10th place, for a
percentile-ranked, per-request index whose top-10 boundary sits within a
few index points of survey noise:

- m3.0.0 failed at 0.70 and m3.1.0 passed at 0.95, though the replicate
  noise in the index barely changed (4.05 against 4.1 index points for the
  worst persona: it is survey noise in the metro's own pool under a fixed
  kernel, and no fitting sample reduces it);
- the cohort age term — the best-fitting refinement by far, +70.4 held-out
  log-likelihood per 1,000 weighted couple-sides — failed at 0.675 while
  making four personas more stable;
- race × education passed at exactly 0.800 alone, and failed at 0.750
  combined with the sex-specific education matrix, which passed alone at
  0.825.

The gate was doing what it was written to do; what it selected between
was not fit (ADR 0010, "the finding under the decision").

## Nathan's decision

Fail a change only if it makes rankings shakier overall, not because two
near-tied cities swapped places in one search.

## The new rule

**A search's wobble.** For each of the 80 replicate versions of the
survey: take every city in the top 10 of either the published ranking or
that version's ranking; measure how many places each moved between the
two rankings; average those moves. The search's wobble is that average
over the 80 versions. A swap between 10th and 11th counts one place for
each city (2 / 11 of a place over the eleven cities involved); a city
jumping from 40th into the top 10 counts thirty.

**The test searches** (`pipeline/build/stability_gate.py`,
`test_searches`): the eighteen golden personas; the Phase 3b effects grid
(both sexes at 25, 30, 35, 40 and 50 — education undisclosed, each of the
four levels, each of the eight race groups, and each education × race
pair — with the grid's window of age − 2 to age + 10 and both marital
statuses); and a same-sex grid (men seeking men and women seeking women
at the same five ages, education undisclosed or each level). Identical
requests count once; a search that ranks fewer than 12 metros is skipped
(two personas: the Black woman of 29 with the stress filters, and the
Pacific Islander search below the suppression bar). 518 searches, 516
scored, over 26 distinct sought pools. These searches serve the gate
only; the golden fixture does not change.

**The verdict.** A change fails if its total wobble is more than **10%**
above the reference's total. Both totals are summed over the same test
searches: those the change touches, meaning any whose index — the point
figure or any of its 80 replicate figures — differs from the reference's.
When a change touches nothing, the totals run over every search, so the
reference against itself reads exactly 1.0.

**The reference is m3.2.0** (`f20cb02c3af8`), not whichever build is
current, so small rises cannot pile up release after release. Its
per-search record is `results/phase3c/stability_reference.json`. It moves
only by Nathan's decision recorded in an ADR — for instance when the
survey data are refreshed — and the build stays complete on disk while it
is the reference.

**Implementation.** The replicate machinery is the validation suite's:
the same pool, the same 80 replicate weights, the same score function.
The kernel-weighted numerator is composed in numpy from the masked pool's
per-cell replicate sums (metro × partner age × education × race), which
do not depend on the kernel and are cached under `data/phase3c_cache/`
so every kernel is read against bit-identical sums; the numpy path
reproduces the suite's SQL join to 1e-8 relative. `build.validate`'s hard
rank-stability gate is now this rule; the old overlap share is reported
beside it as a soft reading, per persona.

## Controls, before anything else went through the gate

`results/phase3c/gate_controls.json`:

- **The reference against itself** reads exactly **1.0** and passes: no
  search is touched, every hash matches, the totals are identical
  (316.209 places over 516 searches).
- **The reference with enlarged noise** — every replicate's deviation from
  the published estimate scaled by 1.5, which makes the survey noise half
  as large again — reads **1.510** and fails (477.406 against 316.209;
  all 516 searches touched, since every replicate figure changed).

For the record, the reference's wobble runs from 0.02 to 2.49 places per
search (median 0.47); the two searches at the slider's match end wobble
most (2.49), and under the old rule the reference's worst persona sits at
exactly 0.800, the knife edge the decision removes. The old rule's
reading over all 516 searches would be a minimum share of 0.775, i.e. a
grid search that would have failed a gate written for personas.

## What the gate does not do

It does not read fit. A candidate still has to improve total held-out
likelihood to ship (ADR 0010's rule stands); the gate only says whether
it made rankings shakier overall. It does not veto churn in one search:
searches whose wobble rises by more than 25% are named in the report as
findings for Nathan, not gates.

## Consequences

`pipeline/build/stability_gate.py` (the rule, the reference, the
controls, a CLI), `pipeline/tests/test_stability_gate.py` (the
arithmetic and the verdict on synthetic rankings), `build.validate` reads
the reference from `results/`. The readings of the past builds through
the new gate (m3.1.0 → m3.2.0, m3.0.0 → m3.1.0) are reported in
PHASE3C.md and change nothing.
