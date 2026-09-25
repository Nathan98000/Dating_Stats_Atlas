# ADR 0014 — Held-out comparisons: a margin, and the simpler form on a tie

Date: 2026-09-25 (Phase 3d, R; Nathan's call after the A2 halt)
Status: accepted. **This rule was written after the flip was seen.** Phase
3d A2 re-ran the decisions that shaped m3.3.0 on the finished fit and one
verdict came out differently (C3 over C1 by 0.007 per 1,000 sides); the
brief made that a stop condition, nothing shipped, and this rule is the
decision. It is committed before m3.4.0 is built — the commit order is
the proof — and its protection against having been fitted to its result
is that no verdict on the record depends on the exact value of δ (the
interval below). Every number here is read from
`results/phase3d/tie_rule.json`, written by `results/phase3d/tie_rule.py`
from the stored records without a refit.

## Context

Every held-out comparison since Phase 3 has been read with a strict
inequality: a refinement improved held-out fit if its total held-out
log-likelihood exceeded the reference's at all, a yes/no choice took the
richer option if it was ahead at all, and among the candidates of Phase
3c B3 the largest gain shipped. Phase 3c read C1 (the cohort age term on
the shipped form) ahead of C3 (the same with the sex-specific education
matrix) by 0.0005 per 1,000 weighted couple-sides, and C2 (the matrix
alone) below the shipped form by 0.0033; the rule picked C1.

Phase 3d A2 let the fit reach the optimum it states (ADR 0010 amended,
the interaction projection). With the same forms, the same data and the
same held-out test, C3 now leads C1 by 0.0073 and C2 is above the shipped
form by 0.0070. The rule as written would ship C3, and C2 would qualify.
Both margins are smaller than what finishing the fit moved them by, and
smaller than their own sampling error. Nathan's decision: held-out
differences this small are ties, and a tie goes to the simpler form.

## Decision

**A held-out difference smaller than δ = 0.25 per 1,000 weighted
couple-sides is a tie, and a tie goes to the simpler form.**

1. **Beats.** Form A beats form B on held-out fit only if A's total
   held-out log-likelihood exceeds B's by at least δ per 1,000 weighted
   couple-sides of the set scored. The held-out measure is the usual
   one: leave one metro out, shrunk dials. Anything less, in either
   direction, is a tie.
2. **Improves.** Wherever a rule requires a candidate to improve
   held-out fit on a reference, it must beat the reference in the sense
   of 1. The gate requirement is unchanged.
3. **Choosing among candidates.** Take the largest gain among the
   qualifying candidates. Every qualifying candidate within δ of it is
   tied for first. Of those, the simplest ships:
   - if one form is nested in another (the other only adds terms), the
     nested one;
   - otherwise, the one with fewer free parameters in the kernel.

   If that does not settle it, apply these in order: the lower ADR 0011
   gate ratio, then the form already served, then the earlier form in
   the brief's table.
4. **Yes/no choices** (whether a term ships; whether the interaction
   rides). The richer option is taken only if it beats the simpler one
   in the sense of 1. A tie keeps the simpler one.
5. **Scope.**
   - δ applies to held-out likelihood comparisons of kernel forms, both
     opposite-sex and same-sex.
   - It does not touch the stability gate (ADR 0011).
   - It does not govern Part B's wobble-based selection. That selection
     has its own margin, set in ADR 0013.
   - δ is a named constant and is carried in the kernel record.
   - δ changes only by a new ADR, written before the comparison it would
     decide is measured.

## Why 0.25 — three anchors

- **Fitting-method shift.** Finishing the fit changed some margins with
  the same forms and the same data (Phase 3c records → A2 records): the
  race × education margin over the baseline moved **0.066** per 1,000
  sides (14.134 → 14.068); the C3 − C1 margin moved **0.008** (−0.0005 →
  +0.0073); the C2 − shipped margin moved **0.010** (−0.0033 →
  +0.0070). δ is **3.8 times** the largest of these. A margin smaller
  than what a change in the optimiser's stopping point can produce says
  nothing about the model.
- **Sampling noise.** The paired, metro-clustered standard error of the
  C3 − C1 difference on the finished fit is **0.014** per 1,000 sides
  (the per-metro differences of held-out log-likelihood, same metro left
  out, same household halves, treated as 387 independent draws; the
  standard error of their total is √(M·s²)), and C3 is better in **197
  of 387** metros. δ is **17 times** that standard error.
- **Smallest real decision.** The smallest margin that has decided a
  served term is **+2.90** per 1,000 sides: the interaction riding on
  same-sex searches, in the A2 records. δ is **11.6 times** smaller.

**One shift the anchors do not cover, stated so it is not read as
covered.** The same-sex margins moved far more than δ between the Phase
3c and A2 records: the interaction's margin from 8.92 to 2.90, the
education term's from 6.98 to 12.26 with the interaction off and 15.90 to
15.16 with it on. That is not the optimiser's stopping point: the
projection moves the education-pair and race-pair parts of the
opposite-sex interaction into the opposite-sex main effects, and a
same-sex search takes its education term from same-sex couples, so the
borrowed interaction carries less on same-sex searches after the
projection than before — a change in what the term contains. δ does not
claim to absorb a shift of that size; the same-sex verdicts hold under it
because their margins are above δ on both fits. It is recorded as a
finding in PHASE3D.md.

## The verdicts do not depend on the exact δ

`tie_rule.json` re-reads every decision on the record at every δ. **Every
outcome — what ships or is served — comes out the same for any δ above
0.0073 and up to 2.898** (`delta_interval.every_outcome_unchanged`,
(0.0073, 2.898]). Below the lower end C3 would beat C1 on the finished
fit and ship; above the upper end the interaction would tie with the
composition without it on same-sex searches and stop riding. Every
intermediate reading, too, holds for any δ up to 2.828
(`every_verdict_unchanged`, (0.0073, 2.828]): above that the Phase 3b
reading of the sex-specific education matrix (+2.83 over the baseline)
would turn into a tie, though its outcome — dropped for the combination's
gate failure — is the same either way. 0.25 sits in the middle of two
orders of magnitude within which nothing on the record changes.

## The record, re-run under the rule

Read from the stored records (`refine_heldout.json`, `samesex_fit.json`,
the gate records, `stability_check.json` for Phase 3b's gate) under the
old rule and under this one, side by side; margins per 1,000 weighted
couple-sides, the richer form minus the simpler; SE the paired,
metro-clustered standard error; "better in" the metros where the richer
form scores higher.

| Decision | Margin (SE; better in) | Old rule | ADR 0014 |
|---|---|---|---|
| 3b: the cohort age term improves on the baseline | +70.42 (7.33; 386/387) | improves; held back by the old gate (0.675) | same |
| 3b: race × education improves on the baseline | +14.13 (2.09; 350) | improves; gate 0.800; ships | same |
| 3b: the sex-specific education matrix improves on the baseline | +2.83 (0.28; 344) | improves; dropped, the combination fails the old gate (0.750) | same |
| 3b: same-sex age beats the fallback | +205.7 (24.1; 374) | served | same |
| 3b: same-sex education beats the fallback | +4.28 (1.80; 244) | improves; face check fails; not served | same |
| 3b: same-sex race beats the fallback | +42.6 (7.96; 272) | improves; unsupported; not served | same |
| 3c: the same-sex education term improves on what m3.2.0 serves | +6.98 off / +15.90 on (2.41; 301) | ships | same |
| 3c: the interaction rides on same-sex searches | +8.92 (2.47; 206) | rides | same |
| 3c: C1, C2, C3 against the shipped form | C1 +69.705 (7.27; 386), C2 −0.003 (0.015; 194), C3 +69.704 (7.27; 386) | C1 and C3 qualify; C1 ships by the larger gain (0.0005) | C1 and C3 qualify and are tied; **C1 ships, nested in C3** |
| A2: race × education improves on the baseline (re-run) | +14.07 (2.09; 348) | improves; gate 1.002; ships | same |
| A2: same-sex age / education / race beat the fallback (re-run) | +205.7 / +9.54 (1.90; 257) / +43.5 (8.02; 276) | age and education served; race unsupported | same |
| A2: the same-sex education term improves on what m3.2.0 serves (re-run) | +12.26 off / +15.16 on (2.33; 301) | ships | same |
| A2: the interaction rides on same-sex searches (re-run) | **+2.90 (1.75; 188)** | rides | same (+2.90 ≥ δ) |
| A2: C1, C2, C3 against the shipped form (re-run) | C1 +69.707 (7.27; 386; gate 0.970), C2 +0.007 (0.015; 209; gate 0.987), C3 +69.715 (7.27; 386; gate 0.976) | all three qualify; **C3 ships** by the larger gain (0.0073) | C2 does not qualify (0.007 < δ); C1 and C3 are tied, 0.007 apart; **C1 ships, nested in C3** |

Simplicity is read from the Form (`kernel_refine.nested_in`,
`free_parameters`): C1 is nested in C3 (C3 only adds the per-sex
matrix), so nesting settles the tie before any count is needed. The
counts are on the record: C1 5,520 free parameters, C2 2,192, C3 5,520,
the shipped form 2,192 — each main effect's cells less one gauge per
row, plus the interaction's 2,048 cells less the 188 (pooled matrix) or
200 (per-sex matrix) directions the fit projects out. With the
interaction present the per-sex matrix adds no free direction to the
kernel: it moves twelve directions out from under the ridge, which is
why C2 counts the same as the shipped form and C3 the same as C1, and why
the nesting check comes first.

## The same-sex interaction: seen, and kept

The interaction riding on same-sex searches rests on a margin of +2.90
per 1,000 sides with a standard error of 1.75 — **1.66 standard errors**
— and the composition with it is better in **188 of 387** metros. Nathan
has seen this and keeps the interaction as it is. The rule keeps it too
(+2.90 ≥ δ), so nothing changes; it is the smallest margin behind any
served term and the upper end of the interval above. The other decisions
on the record whose margin is under two standard errors are the ones
this rule now reads as ties: C3 against C1 (Phase 3c −0.0005, z −0.03;
A2 +0.0073, z 0.51) and C2 against the shipped form (Phase 3c −0.0033,
z −0.22; A2 +0.0070, z 0.47). Findings for Nathan, not gates
(`tie_rule.json`, `under_two_standard_errors`).

## Consequences

`kernel_refine.HELDOUT_TIE_MARGIN_PER_1000 = 0.25` beside the fit
constants, `beats` and `select_form` (with `nested_in` and
`free_parameters`, read from the Form) as the one implementation, and
every held-out decision routed through them: `summarise_lomo`'s `ships`
and `improves_on_shipped`, `cmd_combine`'s `improves_heldout`,
`samesex_decision` (whether a same-sex term ships, whether the education
term improves on what m3.2.0 serves, whether the interaction rides) and
`results/phase3d/speedup/a2_decisions.py`. Unit tests in
`pipeline/tests/test_heldout_tie_rule.py`. The kernel record the ship
chain writes carries `heldout_tie_margin_per_1000_sides` and
`heldout_tie_rule_adr` beside `shipped_form_name`. On the finished fit
**C1 ships as m3.4.0** (ADR 0010's Phase 3d section). Part B's selection
(ADR 0013) keeps its own rule and margin; δ does not apply to it.
