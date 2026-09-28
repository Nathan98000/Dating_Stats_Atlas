# ADR 0016 — The intermarriage check from Census PUMS

Date: 2026-09-28 (Phase 4, Stage 4)
Status: accepted (Nathan's decision). It replaces Pew's metro table in
every check and report. Every number here is read from
`results/phase4/intermarriage_pums.json`,
`results/phase4/intermarriage_check.json` or
`results/phase4/intermarriage_pew_agreement.json`, written by
`pipeline/build/intermarriage_pums.py`.

## Context

Since Phase 3 (ADR 0009 §4) the kernel's out-of-sample check has been
Pew Research Center's table of newlywed intermarriage rates by metro,
2011–2015: leave each metro out, predict its intermarriage rate from the
national pairing pattern and the metro's own singles, and compare with
Pew's. ADR 0012 records Nathan's decision that Pew's table is build-time
only — never published and never compared in public — and Phase 4 took
it out of the repository and its history. A check that cannot be shown
is not a check the record can carry, so the reference changes.

## Nathan's decision

The check's reference is computed from the Census Bureau's own survey.
The reason is **independence from a third-party licence**: the reference
is a public-domain federal source the build already reads.

## The rate

For each metro, the share of people married in the past 12 months whose
spouse is of a different race or ethnicity:

- **From the ACS 2020–2024 5-year PUMS.** "Married in the past 12
  months" is the survey's own item (MARHM = 1). It is not in the Phase 1
  extract and the raw person files were not kept, so the newlyweds' record
  keys are read from the Census Bureau's PUMS API with MARHM = 1 as the
  predicate and joined to the extract: 199,869 newlywed records, 180,551
  in the areas the build covers, every checked field (age, relationship,
  race, Hispanic origin) identical in both.
- **In Pew's category scheme**, as its table's note states it: a Hispanic
  married to a non-Hispanic, or non-Hispanic spouses from different groups
  among white, black, Asian (Pacific Islanders included), American
  Indian, multiracial and some other race. That is the kernel's eight
  groups with Asian and Pacific Islander merged, asserted against the raw
  race and Hispanic-origin codes.
- **The spouse PUMS links**: the household's reference person and their
  spouse, the linkage the kernel is fitted on. 80.0% of newlyweds' weight
  has a linked spouse; the rest are couples living in someone else's
  household, which PUMS cannot pair (the standing limitation).
- **Weighted as every pool figure** (person weight × the record's metro
  allocation), **with the survey's 80-replicate margins** (90%).
- **Metros with at least 200 newlyweds in sample**, Pew's own floor: 124
  metros. The rate over all the build's metros is 23.8% (± 0.4).

## The comparison

The same comparison the Pew reading made, on the same held-out
predictions: the served opposite-sex form's leave-one-metro-out record
(C1 on the five-year-decay sample, Phase 3d's finished fit), corrected by
one national ratio, with the error distributions of the national-only,
raw-dial and shrunk-dial predictions and their paired win counts. It is
the soft intermarriage reading in `build.validate`, and the kernel's own
comparison code (`kernel.outgroup_comparison`) reads it wherever it used
to read Pew's table.

On the record: corrected median absolute error 1.92 points for the
shrunk kernel, 1.91 raw per-metro, 3.75 national-only; the shrunk kernel
beats national-only in 95 of 124 metros (p < 0.001) and ties raw
per-metro (69–55, p = 0.24).

## What the check loses

- **It comes from the same survey as the fit**, though from a different
  subset. The kernel is fitted on every linked union in the 2020–2024
  PUMS, weighted by recency; the reference counts only the newlyweds
  among them. Pew's table came from different years (2011–2015) and a
  different processing (IPUMS), so it was independent of the fit in a way
  this one is not.
- **The dial predictions overlap the reference.** A metro's dials are
  fitted on all of its own couples, and the newlyweds the reference counts
  are among them: 8.1% of the fitting weight nationally (6.1–10.2% across
  metros, p10–p90). The national-only prediction — the kernel refitted
  without the metro, applied to the metro's own singles — is out of
  sample; the raw- and shrunk-dial predictions are only partly so, and
  their lead over national-only is partly by construction.
- **It is not a test of the period.** Pew's newlyweds were older unions
  than the fitting sample's; these are the most recent ones in it.

## Pew, once, then dropped

The agreement between these rates and Pew's was computed once, from the
private copy, and only as two numbers: across the 124 metros both cover,
correlation 0.722 and median absolute difference 6.65 points (the rates
here are higher, as intermarriage has risen since 2011–2015). No value of
Pew's is recorded. After this reading Pew's table plays no part in any
check: the kernel's comparison code no longer reads it, and the retired
Phase 3b re-run command that did is gone.
