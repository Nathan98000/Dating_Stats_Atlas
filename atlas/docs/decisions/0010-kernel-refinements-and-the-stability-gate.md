# ADR 0010 — Three refinements of the kernel: the race × education term ships, the cohort age term and the sex-specific education matrix are held back by the stability gate; same-sex terms per component

Date: 2026-09-24 (Phase 3b Part B, model m3.2.0, build f20cb02c3af8)
Status: accepted

## Context

Phase 3 measured three failures of the separable kernel (ADR 0009 §2):
the shift-invariant age-gap curve under-fits how tightly the young pair
in age and over-fits the old; race and education pairings interact (7.2%
of couples misallocated on the recent sample, 16% of couples in
well-measured cells off by more than a quarter); and the education
matrix pooled over sex hides a real asymmetry. Same-sex couples
(117,522 sides) were counted and excluded, and same-sex searches were
served the opposite-sex terms. The Phase 3b brief asked for each to be
fitted and tested on the shipped five-year sample under the framework
Phase 3 built — leave one metro out, split its couples in half by
household, score the held-out half — with each refinement shipping only
if it improves total held-out likelihood and breaks neither rank
stability nor latency, one failing not holding up the others.

## Decision

The kernel's form becomes

    w = exp( θ_age f_age(gap; sex_s, cohort(age_s)) + θ_edu f_edu(edu_s, edu_c; sex_s)
           + θ_race f_race(race_s, race_c; sex_s) + g(race_s, race_c, edu_s, edu_c; sex_s)
           + log_norm(metro, seeker) )

as a **capability** (artifact `kernel_v2`, loader reads v1 and v2;
`pipeline/build/kernel_refine.py`, reproducing kernel.py to 1e-9 on the
baseline form), and the shipped kernel uses **one cohort, one education
matrix stored per sex with equal rows, and the interaction** —

1. **B2a ships.** g is the race × education two-way term per seeker
   sex (2,048 cells), estimated by penalised coordinate ascent: exact
   IPF steps for the main effects, a Newton step per cell on the
   ridge-penalised Poisson objective for g, with a Gaussian prior
   centred at zero (no interaction) whose variance τ² = 0.0324 (τ =
   0.18) is estimated by the method of moments at the separable fit —
   a cell keeps n / (n + 31) of its raw log ratio for n observed sides.
   Undialled (a national correction). Held-out gain **+14.1 per 1,000
   weighted couple-sides**, better in 350 of 387 metros; separability of
   the race × education table G² 1,157,677 → 35,311, couples misallocated
   6.6% → 0.25%; rank stability passes at the bar, 0.800; latency in
   PHASE3B.md.
2. **B1 is dropped by the stability gate, not by fit.** A gap curve per
   (sex, cohort) — seventeen cohorts chosen by split-half held-out
   likelihood among seven stated partitions, bandwidth cross-validated
   per cohort — is the best-fitting refinement by far (**+70.4 per
   1,000**, better in 386 of 387 metros; the raw own-age shares at 25
   and 50 reproduced to a point) and **fails the standing rank-stability
   gate** on the m3.1.0 build (0.675 on the man of 33 seeking Hispanic
   women, 0.7875 at the slider's match end). Nothing was retried to make
   it pass; the gate is untouched; the term stays in the code and the
   record.
3. **B2b is dropped because the combination fails the gate.** The
   sex-specific education matrix improves held-out likelihood (+2.8 per
   1,000, 344 of 387 metros) and passes rank stability alone (0.825), but
   B2a + B2b together fail it (0.750 on the man of 41 seeking women
   earning 50k+ — the persona that failed in m3.0.0). The refinement with
   the larger held-out gain ships alone; the other is recorded as
   shippable on its own and dropped for the combination's failure.
4. **B3 — same-sex terms per component.** Same-sex couples get a
   kernel of their own — 65,011 allocated couple-sides (Kish 39,989)
   under the same five-year decay, fitted against the same sex's single
   population — and a same-sex search takes from it each component
   that (a) the sample supports (every education cell, every own-group
   race cell and every gap within ten years at or above 100 effective
   sides, both sexes), (b) predicts held-out same-sex couples better
   than the opposite-sex fallback in the leave-one-metro-out test, and
   (c) passes the standing face-validity check; the rest keep the
   opposite-sex term with the metro's dial. **The age term ships** (all
   three hold: +205.7 held-out log-likelihood per 1,000 weighted sides
   over the fallback, better in 374 of 387 metros — same-sex age gaps
   are symmetric where the opposite-sex curve is not). **Education does
   not**: supported (smallest cell 255 effective sides) and better held
   out (+4.3, 244 of 387), but its matrix is not diagonal-dominant in
   the bachelor's row (2.44× with graduate partners against 2.05× at
   the same level), which the battery's hard gate would fail; the gate
   was not loosened. **Race does not**: unsupported (the three small
   groups' own-group cells hold 5–44 effective sides) although the
   held-out test favours it (+42.6). The page says so: every row of a
   same-sex search carries one registry sentence in its information box
   naming the age gaps as measured on same-sex couples and the
   education and race pairings as borrowed from opposite-sex couples,
   and the methodology page carries the same sentence.

**The finding under the decision.** A percentile-ranked, per-request
index whose top-10 boundary lies within a few index points of survey
noise crosses the rank-stability gate with almost every change to the
kernel, in either direction: m3.0.0 failed it (0.70), m3.1.0 passed it
(0.95), the best-fitting age term fails it (0.675), the interaction
passes at exactly 0.800, and two individually-passing terms fail it
together (0.750). The gate is doing what it was written to do; what it
now selects between is not fit. Whether the gate should read differently
for a per-request feature (the m3.0.0 alternatives: accept the churn,
change the intensive normalisation, or a wider top-k) is Nathan's call;
nothing here moved it.

## Consequences

MODEL_VERSION m3.2.0; goldens regenerated; every number in PHASE3B.md;
`match_inputs.same_sex` and the row's `match.note` on same-sex searches;
two registry strings (`match_same_sex_note`,
`match_same_sex_note_all_fallback`) and the same sentence on the
methodology page; kernel_v1 artifacts still load (one cohort, the pooled
matrix twice, no interaction, no same-sex block).
